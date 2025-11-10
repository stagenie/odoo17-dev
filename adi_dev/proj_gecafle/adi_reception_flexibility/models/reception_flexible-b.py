# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleReceptionFlexible(models.Model):
    _inherit = 'gecafle.reception'

    # Override la méthode write pour permettre les modifications
    def write(self, vals):
        """Permet la modification même après confirmation"""
        # Juste vérifier si on a un récap
        for record in self:
            if record.state == 'confirmee' and 'details_reception_ids' in vals:
                # Vérifier s'il y a un récap
                recap = self.env['gecafle.reception.recap'].search([
                    ('reception_id', '=', record.id),
                    ('state', 'in', ['valide', 'facture'])
                ], limit=1)

                if recap:
                    raise UserError(_(
                        "Impossible de modifier la réception car elle a un récapitulatif validé.\n"
                        "Vous devez d'abord supprimer ou annuler le récapitulatif."
                    ))

        # Appeler la méthode parent
        result = super().write(vals)

        # Si on a modifié une réception confirmée, régénérer le stock
        for record in self:
            if record.state == 'confirmee':
                record._generate_stock_entries()

                # Message dans le chatter
                if 'details_reception_ids' in vals:
                    record.message_post(
                        body=_("✏️ Réception modifiée après confirmation")
                    )

        return result


class GecafleDetailsReceptionFlexible(models.Model):
    _inherit = 'gecafle.details_reception'

    def write(self, vals):
        """Permet la modification directe avec vérification simple"""
        for record in self:
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

        # Invalider le cache pour rafraîchir les ventes
        self.env['gecafle.details_reception']._invalidate_cache()

        return result

    @api.model
    def create(self, vals):
        """Permet l'ajout de nouvelles lignes"""
        result = super().create(vals)

        # Régénérer le stock si la réception est confirmée
        if result.reception_id.state == 'confirmee':
            result.reception_id._generate_stock_entries()

        return result

    def unlink(self):
        """Permet la suppression avec vérification"""
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

        # Régénérer le stock
        for reception in receptions:
            if reception.state == 'confirmee':
                reception._generate_stock_entries()

        return result
