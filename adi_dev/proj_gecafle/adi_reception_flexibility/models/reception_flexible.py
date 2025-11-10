# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleReceptionFlexible(models.Model):
    _inherit = 'gecafle.reception'

    def write(self, vals):
        """Permet la modification même après confirmation avec synchronisation complète"""
        for record in self:
            # Vérifier s'il y a un récap validé
            if record.state == 'confirmee':
                recap = self.env['gecafle.reception.recap'].search([
                    ('reception_id', '=', record.id),
                    ('state', 'in', ['valide', 'facture'])
                ], limit=1)

                if recap:
                    raise UserError(_(
                        "Impossible de modifier la réception car elle a un récapitulatif validé.\n"
                        "Vous devez d'abord supprimer ou annuler le récapitulatif."
                    ))

        # IMPORTANT : Forcer la mise à jour du contexte pour permettre les modifications
        self = self.with_context(force_update_reception=True)

        # Appeler la méthode parent
        result = super().write(vals)

        # Traiter chaque réception après modification
        for record in self:
            if record.state == 'confirmee':
                # Régénérer le stock si nécessaire
                if 'details_reception_ids' in vals:
                    record._generate_stock_entries()

                # Synchroniser les emballages si des lignes ont été modifiées
                if 'details_reception_ids' in vals or 'details_emballage_reception_ids' in vals:
                    record.sync_emballages_with_reception()  # SANS underscore pour être public

                # Message dans le chatter
                record.message_post(
                    body=_("✏️ Réception modifiée après confirmation"),
                    subtype_xmlid='mail.mt_note'
                )

        return result

    def sync_emballages_with_reception(self):
        """Méthode PUBLIQUE pour synchroniser les lignes d'emballage avec les lignes de réception"""
        self.ensure_one()

        # Dictionnaire pour regrouper les emballages par type
        emballage_dict = {}

        # Parcourir les lignes de réception pour calculer les quantités
        for line in self.details_reception_ids:
            if line.type_colis_id:
                emballage_id = line.type_colis_id.id
                if emballage_id in emballage_dict:
                    emballage_dict[emballage_id] += line.qte_colis_recue
                else:
                    emballage_dict[emballage_id] = line.qte_colis_recue

        # Mettre à jour ou créer les lignes d'emballage
        for emballage_id, qte in emballage_dict.items():
            emb_line = self.details_emballage_reception_ids.filtered(
                lambda x: x.emballage_id.id == emballage_id
            )

            if emb_line:
                # Mettre à jour la quantité sortante
                emb_line[0].with_context(force_update_reception=True).write({
                    'qte_sortantes': qte
                })
            else:
                # Créer une nouvelle ligne d'emballage
                self.env['gecafle.details_emballage_reception'].with_context(
                    force_update_reception=True
                ).create({
                    'reception_id': self.id,
                    'emballage_id': emballage_id,
                    'qte_sortantes': qte,
                    'qte_entrantes': 0
                })

        # Supprimer les lignes d'emballage qui n'ont plus de correspondance
        emballages_to_remove = self.details_emballage_reception_ids.filtered(
            lambda x: x.emballage_id.id not in emballage_dict
        )
        if emballages_to_remove:
            emballages_to_remove.with_context(force_update_reception=True).unlink()

        _logger.info(f"Emballages synchronisés pour la réception {self.name}")

        return {'type': 'ir.actions.client', 'tag': 'reload'}


class GecafleDetailsReceptionFlexible(models.Model):
    _inherit = 'gecafle.details_reception'

    def write(self, vals):
        """Permet la modification directe avec synchronisation des emballages"""
        # Autoriser les modifications si on a le contexte approprié
        if self.env.context.get('force_update_reception'):
            result = super().write(vals)
            # Synchroniser après modification
            for record in self:
                if record.reception_id.state == 'confirmee':
                    record.reception_id.sync_emballages_with_reception()
            return result

        # Sinon, vérifier les contraintes normales
        for record in self:
            if record.reception_id.state == 'confirmee':
                # Vérifier la cohérence des quantités
                if 'qte_colis_recue' in vals:
                    new_qty = vals['qte_colis_recue']
                    min_qty = record.qte_colis_vendus + record.qte_colis_destockes

                    if new_qty < min_qty:
                        raise UserError(_(
                            "Impossible de réduire la quantité à %d.\n"
                            "Minimum requis : %d (Vendus: %d, Destockés: %d)"
                        ) % (new_qty, min_qty, record.qte_colis_vendus, record.qte_colis_destockes))

        result = super().write(vals)

        # Synchroniser les emballages si nécessaire
        if 'qte_colis_recue' in vals or 'type_colis_id' in vals:
            for record in self:
                if record.reception_id.state == 'confirmee':
                    record.reception_id.sync_emballages_with_reception()

        # Invalider le cache
        self.invalidate_cache()

        return result

    @api.model
    def create(self, vals):
        """Permet l'ajout de nouvelles lignes avec sync emballages"""
        result = super().create(vals)

        # Synchroniser les emballages si la réception est confirmée
        if result.reception_id.state == 'confirmee':
            result.reception_id._generate_stock_entries()
            result.reception_id.sync_emballages_with_reception()

        return result

    def unlink(self):
        """Permet la suppression avec synchronisation des emballages"""
        for record in self:
            if record.qte_colis_vendus > 0:
                raise UserError(_(
                    "Impossible de supprimer '%s' car il y a des ventes liées."
                ) % record.designation_id.name)

            if record.qte_colis_destockes > 0:
                raise UserError(_(
                    "Impossible de supprimer '%s' car il y a des destockages."
                ) % record.designation_id.name)

        receptions = self.mapped('reception_id')
        result = super().unlink()

        # Synchroniser les emballages après suppression
        for reception in receptions:
            if reception.state == 'confirmee':
                reception._generate_stock_entries()
                reception.sync_emballages_with_reception()

        return result


class GecafleDetailsEmballageReceptionFlexible(models.Model):
    _inherit = 'gecafle.details_emballage_reception'

    def write(self, vals):
        """Permet la modification de l'option acheté même après confirmation"""
        # Si on a le contexte de force, autoriser toute modification
        if self.env.context.get('force_update_reception'):
            return super().write(vals)

        # Sinon, vérifier les conditions
        for record in self:
            if record.reception_id.state == 'confirmee':
                # Pour une réception avec achat valorisé, permettre la modification
                if hasattr(record.reception_id, 'is_achat_valorise') and record.reception_id.is_achat_valorise:
                    # Autoriser toutes les modifications pour les réceptions valorisées
                    return super().write(vals)
                else:
                    # Pour les réceptions normales, appliquer certaines restrictions
                    # MAIS permettre quand même certaines modifications
                    restricted_fields = set(vals.keys()) & {
                        'emballage_id'}  # Seulement restreindre le changement de type
                    if restricted_fields:
                        raise UserError(_(
                            "Impossible de modifier le type d'emballage après confirmation."
                        ))

        return super().write(vals)

    def unlink(self):
        """Permet la suppression avec synchronisation"""
        receptions = self.mapped('reception_id')
        result = super().unlink()

        # Synchroniser après suppression
        for reception in receptions:
            if reception.exists() and reception.state == 'confirmee':
                reception.sync_emballages_with_reception()

        return result
