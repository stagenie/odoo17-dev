# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ========== CONFIGURATION DU TRACKING D'EMBALLAGES ==========

    # Emballages à tracker
    tracking_emballage_ids = fields.Many2many(
        'gecafle.emballage',
        'config_settings_emballage_tracking_rel',
        'config_id',
        'emballage_id',
        string="Emballages à suivre",
        help="Sélectionnez les emballages qui doivent être suivis automatiquement"
    )

    # Options de tracking
    tracking_include_non_returned = fields.Boolean(
        string="Inclure les emballages non rendus",
        default=False,
        config_parameter='gecafle.tracking_include_non_returned',
        help="Si activé, les emballages marqués comme 'non rendus' seront inclus dans le suivi"
    )

    tracking_auto_create = fields.Boolean(
        string="Créer automatiquement le tracking",
        default=True,
        config_parameter='gecafle.tracking_auto_create',
        help="Créer automatiquement le tracking lors des mouvements de vente/réception"
    )

    tracking_create_on_draft = fields.Boolean(
        string="Créer les mouvements sur les brouillons",
        default=False,
        config_parameter='gecafle.tracking_create_on_draft',
        help="Si activé, les mouvements seront créés même sur les documents en brouillon"
    )

    tracking_allow_manual_adjustment = fields.Boolean(
        string="Autoriser les ajustements manuels",
        default=True,
        config_parameter='gecafle.tracking_allow_manual_adjustment',
        help="Permet les régularisations manuelles via l'assistant"
    )

    tracking_show_zero_stock = fields.Boolean(
        string="Afficher les emballages sans stock",
        default=False,
        config_parameter='gecafle.tracking_show_zero_stock',
        help="Afficher les emballages avec stock à zéro dans les listes"
    )

    tracking_alert_negative_stock = fields.Boolean(
        string="Alerter sur stock négatif",
        default=True,
        config_parameter='gecafle.tracking_alert_negative_stock',
        help="Envoyer une alerte quand le stock d'un emballage devient négatif"
    )

    tracking_alert_threshold = fields.Integer(
        string="Seuil d'alerte stock bas",
        default=10,
        config_parameter='gecafle.tracking_alert_threshold',
        help="Nombre minimum d'emballages avant alerte de stock bas"
    )

    @api.model
    def get_values(self):
        res = super().get_values()

        # Récupérer les emballages trackés
        tracked = self.env['gecafle.emballage.tracking'].search([
            ('is_tracked', '=', True)
        ]).mapped('emballage_id')

        res.update({
            'tracking_emballage_ids': [(6, 0, tracked.ids)],
        })
        return res

    def set_values(self):
        super().set_values()

        # Mettre à jour les trackings pour les emballages sélectionnés
        for emballage in self.tracking_emballage_ids:
            tracking = self.env['gecafle.emballage.tracking'].search([
                ('emballage_id', '=', emballage.id)
            ], limit=1)

            if not tracking:
                # Créer le tracking SANS le champ include_non_returned qui n'existe pas
                self.env['gecafle.emballage.tracking'].sudo().create({
                    'emballage_id': emballage.id,
                    'is_tracked': True,
                    # SUPPRIMÉ : 'include_non_returned': emballage.non_returnable
                })
            else:
                # Activer le tracking existant
                tracking.is_tracked = True

        # Désactiver les trackings non sélectionnés
        non_tracked_emballages = self.env['gecafle.emballage'].search([
            ('id', 'not in', self.tracking_emballage_ids.ids)
        ])

        non_tracked = self.env['gecafle.emballage.tracking'].sudo().search([
            ('emballage_id', 'in', non_tracked_emballages.ids)
        ])
        non_tracked.sudo().write({'is_tracked': False})

    def action_configure_tracking(self):
        """Ouvre l'assistant de configuration avancée du tracking"""
        return {
            'name': _('Configuration avancée du suivi des emballages'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.config.settings',
            'target': 'new',
            'context': {'module': 'adi_gecafle_emballage_tracking'},
        }
