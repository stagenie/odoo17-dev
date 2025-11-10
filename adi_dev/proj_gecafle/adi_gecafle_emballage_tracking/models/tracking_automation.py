# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class VenteInherit(models.Model):
    _inherit = 'gecafle.vente'

    # Champ pour tracker les mouvements créés
    emballage_mouvement_ids = fields.One2many(
        'gecafle.emballage.mouvement',
        'vente_id',
        string="Mouvements d'emballage",
        readonly=True
    )

    def action_confirm(self):
        """Surcharge pour créer les mouvements d'emballage lors de la validation"""
        # D'abord exécuter la méthode parent
        res = super(VenteInherit, self).action_confirm()

        # Ensuite créer les mouvements si la vente est validée
        for vente in self:
            if vente.state == 'valide':
                _logger.info(f"Création des mouvements d'emballage pour la vente {vente.name}")
                vente._create_emballage_mouvements()

        return res

    def _create_emballage_mouvements(self):
        """Crée les mouvements d'emballage lors de la validation"""
        self.ensure_one()

        # Vérifier si la création automatique est activée
        auto_create = self.env['ir.config_parameter'].sudo().get_param(
            'gecafle.tracking_auto_create', 'True'
        )

        if auto_create != 'True':
            _logger.info("Création automatique des mouvements désactivée")
            return

        _logger.info(f"Création des mouvements pour {len(self.detail_emballage_vente_ids)} lignes d'emballage")

        # Créer les mouvements basés sur les lignes d'emballage
        for line in self.detail_emballage_vente_ids:
            if not line.emballage_id:
                continue

            # Obtenir ou créer le tracking
            tracking = self._get_or_create_tracking(line.emballage_id)

            # Sortie d'emballages
            if line.qte_sortantes > 0:
                mouvement = self.env['gecafle.emballage.mouvement'].create({
                    'tracking_id': tracking.id,
                    'date': self.date_vente,
                    'type_mouvement': 'sortie_vente',
                    'quantite': line.qte_sortantes,
                    'client_id': self.client_id.id,
                    'vente_id': self.id,
                    'notes': _("Sortie emballages - Vente %s") % self.name,
                })
                _logger.info(f"Mouvement sortie créé : {mouvement.name} - Qté: {line.qte_sortantes}")

            # Retour d'emballages
            if line.qte_entrantes > 0:
                mouvement = self.env['gecafle.emballage.mouvement'].create({
                    'tracking_id': tracking.id,
                    'date': self.date_vente,
                    'type_mouvement': 'retour_client',
                    'quantite': line.qte_entrantes,
                    'client_id': self.client_id.id,
                    'vente_id': self.id,
                    'notes': _("Retour emballages - Vente %s") % self.name,
                })
                _logger.info(f"Mouvement retour créé : {mouvement.name} - Qté: {line.qte_entrantes}")

    def _get_or_create_tracking(self, emballage):
        """Obtient ou crée le tracking pour un emballage"""
        tracking = self.env['gecafle.emballage.tracking'].search([
            ('emballage_id', '=', emballage.id)
        ], limit=1)

        if not tracking:
            _logger.info(f"Création du tracking pour l'emballage {emballage.name}")
            tracking = self.env['gecafle.emballage.tracking'].create({
                'emballage_id': emballage.id,
                'is_tracked': True,
                'stock_initial': 0
            })

        return tracking

    def action_cancel(self):
        """Annule la vente et crée des mouvements inverses"""
        for vente in self:
            if vente.state == 'valide' and vente.emballage_mouvement_ids:
                # Créer des mouvements inverses
                vente._reverse_emballage_mouvements()

        return super(VenteInherit, self).action_cancel()

    def _reverse_emballage_mouvements(self):
        """Crée des mouvements inverses pour annuler"""
        self.ensure_one()

        for mouvement in self.emballage_mouvement_ids.filtered(lambda m: not m.is_cancelled):
            # Créer le mouvement inverse
            inverse_type = 'retour_client' if mouvement.type_mouvement == 'sortie_vente' else 'sortie_vente'

            self.env['gecafle.emballage.mouvement'].create({
                'tracking_id': mouvement.tracking_id.id,
                'date': fields.Datetime.now(),
                'type_mouvement': inverse_type,
                'quantite': mouvement.quantite,
                'client_id': mouvement.client_id.id,
                'vente_id': self.id,
                'notes': _("Annulation vente %s - Mouvement inverse") % self.name,
                'is_cancelled': True,
            })


class ReceptionInherit(models.Model):
    _inherit = 'gecafle.reception'

    # Champ pour tracker les mouvements créés
    emballage_mouvement_ids = fields.One2many(
        'gecafle.emballage.mouvement',
        'reception_id',
        string="Mouvements d'emballage",
        readonly=True
    )

    def action_confirm(self):
        """Confirme la réception et crée les mouvements"""
        res = super(ReceptionInherit, self).action_confirm()

        for reception in self:
            if reception.state == 'confirmee':
                _logger.info(f"Création des mouvements d'emballage pour la réception {reception.name}")
                reception._create_emballage_mouvements()

        return res

    def _create_emballage_mouvements(self):
        """Crée les mouvements d'emballage pour les réceptions"""
        self.ensure_one()

        # Vérifier si la création automatique est activée
        auto_create = self.env['ir.config_parameter'].sudo().get_param(
            'gecafle.tracking_auto_create', 'True'
        )

        if auto_create != 'True':
            _logger.info("Création automatique des mouvements désactivée")
            return

        _logger.info(f"Création des mouvements pour {len(self.details_emballage_reception_ids)} lignes d'emballage")

        # Créer les mouvements basés sur les lignes d'emballage de réception
        for line in self.details_emballage_reception_ids:
            if not line.emballage_id:
                continue

            # Obtenir ou créer le tracking
            tracking = self.env['gecafle.vente']._get_or_create_tracking(line.emballage_id)

            # Entrée d'emballages
            if line.qte_entrantes > 0:
                mouvement = self.env['gecafle.emballage.mouvement'].create({
                    'tracking_id': tracking.id,
                    'date': self.reception_date,
                    'type_mouvement': 'entree_reception',
                    'quantite': line.qte_entrantes,
                    'producteur_id': self.producteur_id.id,
                    'reception_id': self.id,
                    'notes': _("Entrée emballages - Réception %s") % self.name,
                })
                _logger.info(f"Mouvement entrée créé : {mouvement.name} - Qté: {line.qte_entrantes}")

            # Sortie d'emballages
            if line.qte_sortantes > 0:
                mouvement = self.env['gecafle.emballage.mouvement'].create({
                    'tracking_id': tracking.id,
                    'date': self.reception_date,
                    'type_mouvement': 'sortie_producteur',
                    'quantite': line.qte_sortantes,
                    'producteur_id': self.producteur_id.id,
                    'reception_id': self.id,
                    'notes': _("Sortie emballages - Réception %s") % self.name,
                })
                _logger.info(f"Mouvement sortie créé : {mouvement.name} - Qté: {line.qte_sortantes}")


# Classes pour les opérations manuelles d'emballages
class EmballageClientInherit(models.Model):
    _inherit = 'gecafle.emballage.client'

    def create(self, vals):
        """Surcharge pour créer les mouvements lors de la création"""
        record = super(EmballageClientInherit, self).create(vals)
        record._create_emballage_mouvements()
        return record

    def _create_emballage_mouvements(self):
        """Crée les mouvements pour les opérations emballage client"""
        for operation in self:
            _logger.info(f"Création mouvements pour opération client {operation.name}")

            for line in operation.client_emb_operations_ids:
                if not line.emballage_id:
                    continue

                # Obtenir ou créer le tracking
                tracking = self.env['gecafle.vente']._get_or_create_tracking(line.emballage_id)

                # Créer les mouvements
                if line.quantite_entrante > 0:
                    self.env['gecafle.emballage.mouvement'].create({
                        'tracking_id': tracking.id,
                        'date': operation.date_heure_operation,
                        'type_mouvement': 'retour_client',
                        'quantite': line.quantite_entrante,
                        'client_id': operation.client_id.id,
                        'notes': line.remarque or _("Opération manuelle emballage client"),
                    })

                if line.quantite_sortante > 0:
                    self.env['gecafle.emballage.mouvement'].create({
                        'tracking_id': tracking.id,
                        'date': operation.date_heure_operation,
                        'type_mouvement': 'sortie_vente',
                        'quantite': line.quantite_sortante,
                        'client_id': operation.client_id.id,
                        'notes': line.remarque or _("Opération manuelle emballage client"),
                    })


class EmballageProducteurInherit(models.Model):
    _inherit = 'gecafle.emballage.producteur'

    def create(self, vals):
        """Surcharge pour créer les mouvements lors de la création"""
        record = super(EmballageProducteurInherit, self).create(vals)
        record._create_emballage_mouvements()
        return record

    def _create_emballage_mouvements(self):
        """Crée les mouvements pour les opérations emballage producteur"""
        for operation in self:
            _logger.info(f"Création mouvements pour opération producteur {operation.name}")

            for line in operation.prod_emb_operations_ids:
                if not line.emballage_id:
                    continue

                # Obtenir ou créer le tracking
                tracking = self.env['gecafle.vente']._get_or_create_tracking(line.emballage_id)

                # Créer les mouvements
                if line.quantite_entrante > 0:
                    self.env['gecafle.emballage.mouvement'].create({
                        'tracking_id': tracking.id,
                        'date': operation.date_heure_operation,
                        'type_mouvement': 'entree_reception',
                        'quantite': line.quantite_entrante,
                        'producteur_id': operation.producteur_id.id,
                        'notes': line.remarque or _("Opération manuelle emballage producteur"),
                    })

                if line.quantite_sortante > 0:
                    self.env['gecafle.emballage.mouvement'].create({
                        'tracking_id': tracking.id,
                        'date': operation.date_heure_operation,
                        'type_mouvement': 'sortie_producteur',
                        'quantite': line.quantite_sortante,
                        'producteur_id': operation.producteur_id.id,
                        'notes': line.remarque or _("Opération manuelle emballage producteur"),
                    })
