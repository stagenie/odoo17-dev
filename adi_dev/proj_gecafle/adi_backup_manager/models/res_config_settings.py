# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Paramètres du module backup
    module_adi_backup_manager = fields.Boolean(
        string='Gestionnaire de Backups',
        help='Installer le module de gestion des sauvegardes'
    )

    backup_auto_scan = fields.Boolean(
        string='Scan automatique',
        config_parameter='adi_backup_manager.auto_scan',
        default=False
    )

    backup_scan_interval = fields.Integer(
        string='Intervalle de scan (heures)',
        config_parameter='adi_backup_manager.scan_interval',
        default=24
    )

    backup_retention_days = fields.Integer(
        string='Rétention (jours)',
        config_parameter='adi_backup_manager.retention_days',
        default=30,
        help='Nombre de jours de conservation des backups'
    )

    backup_notification_email = fields.Boolean(
        string='Notifications Email',
        config_parameter='adi_backup_manager.notification_email',
        default=False
    )

    backup_notification_recipients = fields.Many2many(
        'res.users',
        string='Destinataires',
        help='Utilisateurs qui recevront les notifications'
    )

    @api.model
    def get_values(self):
        """Récupérer les valeurs de configuration"""
        res = super(ResConfigSettings, self).get_values()

        # Récupérer les IDs des destinataires depuis les paramètres
        recipient_ids = self.env['ir.config_parameter'].sudo().get_param(
            'adi_backup_manager.notification_recipients',
            default='[]'
        )

        try:
            recipient_ids = eval(recipient_ids)
        except:
            recipient_ids = []

        res.update(
            backup_notification_recipients=[(6, 0, recipient_ids)]
        )

        return res

    def set_values(self):
        """Sauvegarder les valeurs de configuration"""
        super(ResConfigSettings, self).set_values()

        # Sauvegarder les IDs des destinataires
        self.env['ir.config_parameter'].sudo().set_param(
            'adi_backup_manager.notification_recipients',
            self.backup_notification_recipients.ids
        )
