# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class GecafleConsigneRetourTracking(models.Model):
    _inherit = 'gecafle.consigne.retour'

    # Champ pour suivre les mouvements créés
    tracking_mouvement_ids = fields.One2many(
        'gecafle.emballage.mouvement',
        'consigne_retour_id',
        string="Mouvements de tracking",
        readonly=True
    )

    def action_validate(self):
        """Surcharge pour créer les mouvements de tracking"""
        res = super().action_validate()

        # Créer les mouvements de tracking si le module est installé
        if self.env['ir.module.module'].search([
            ('name', '=', 'adi_gecafle_emballage_tracking'),
            ('state', '=', 'installed')
        ]):
            self._create_tracking_mouvements()

        return res

    def _create_tracking_mouvements(self):
        """Crée les mouvements de tracking pour le retour de consigne"""
        self.ensure_one()

        _logger.info(f"Création des mouvements de tracking pour le retour de consigne {self.name}")

        for line in self.retour_line_ids:
            if line.qte_retournee > 0 and line.emballage_id:
                # Obtenir ou créer le tracking
                tracking = self._get_or_create_tracking(line.emballage_id)

                # Créer le mouvement de type 'consigne'
                mouvement = self.env['gecafle.emballage.mouvement'].create({
                    'tracking_id': tracking.id,
                    'date': fields.Datetime.now(),
                    'type_mouvement': 'consigne',
                    'quantite': line.qte_retournee,
                    'client_id': self.client_id.id,
                    'consigne_retour_id': self.id,  # Nouveau champ à ajouter
                    'notes': _("Retour consigne %s") % self.name,
                })

                _logger.info(f"Mouvement consigne créé : {mouvement.name} - Qté: {line.qte_retournee}")

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
        """Surcharge pour annuler les mouvements de tracking"""
        # Annuler les mouvements de tracking
        for mouvement in self.tracking_mouvement_ids:
            if not mouvement.is_cancelled:
                mouvement.action_cancel()

        return super().action_cancel()
