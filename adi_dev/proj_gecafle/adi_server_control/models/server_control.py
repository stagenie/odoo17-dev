# -*- coding: utf-8 -*-
import subprocess
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class ServerControlConfig(models.Model):
    """Configuration du contrôle serveur (Singleton)"""
    _name = 'server.control.config'
    _description = 'Configuration du contrôle serveur'
    _rec_name = 'service_name'

    service_name = fields.Char(
        string='Nom du service Odoo',
        default='odoo17',
        required=True,
        help='Nom du service systemd pour Odoo (ex: odoo17, odoo, odoo-server)'
    )

    shutdown_delay = fields.Integer(
        string='Délai avant arrêt (minutes)',
        default=1,
        required=True,
        help='Délai en minutes avant l\'arrêt du serveur'
    )

    active = fields.Boolean('Activ?', default=True)

    reboot_delay = fields.Integer(
        string='Délai avant redémarrage (minutes)',
        default=1,
        required=True,
        help='Délai en minutes avant le redémarrage du serveur'
    )

    enable_logging = fields.Boolean(
        string='Activer les notifications',
        default=True,
        help='Afficher les notifications après chaque action'
    )

    @api.model
    def create(self, vals):
        """S'assurer qu'il n'y a qu'une seule configuration"""
        if self.search_count([]) > 0:
            raise UserError(_(
                "Une configuration existe déjà. Veuillez la modifier au lieu d'en créer une nouvelle."
            ))
        return super().create(vals)

    @api.model
    def get_config(self):
        """Récupérer ou créer la configuration active"""
        config = self.search([], limit=1)
        if not config:
            config = self.sudo().create({
                'service_name': 'odoo17',
                'shutdown_delay': 1,
                'reboot_delay': 1,
                'enable_logging': True
            })
        return config


class ServerControlPanel(models.TransientModel):
    """Panneau de contrôle transitoire (pas de sauvegarde)"""
    _name = 'server.control.panel'
    _description = 'Panneau de contrôle du serveur'

    # Champ informatif uniquement
    info_message = fields.Html(
        string='Information',
        default=lambda self: self._get_info_message(),
        readonly=True
    )

    @api.model
    def _get_info_message(self):
        """Message d'information du panneau"""
        config = self.env['server.control.config'].get_config()
        return """
        <div class="alert alert-info">
            <h4>🖥️ Panneau de Contrôle du Serveur</h4>
            <p>Service configuré : <strong>%s</strong></p>
            <p>Utilisez les boutons ci-dessous pour contrôler le serveur et le service Odoo.</p>
        </div>
        """ % config.service_name

    @api.model
    def check_server_control_access(self):
        """Vérifier les droits d'accès"""
        if not self.env.user.has_group('adi_server_control.group_server_control'):
            raise AccessError(_("Vous n'avez pas les droits pour contrôler le serveur!"))
        return True

    def action_shutdown_server(self):
        """Ouvrir le wizard de confirmation pour arrêt"""
        self.check_server_control_access()
        config = self.env['server.control.config'].get_config()

        return {
            'type': 'ir.actions.act_window',
            'name': _('⚠️ Confirmation d\'arrêt du serveur'),
            'res_model': 'server.control.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'shutdown',
                'default_warning_message': _(
                    "Vous êtes sur le point d'ARRÊTER LE SERVEUR!\n\n"
                    "• Arrêt dans %d minute(s)\n"
                    "• Tous les services seront arrêtés\n"
                    "• Le serveur sera éteint physiquement\n\n"
                    "Confirmez-vous cette action?"
                ) % config.shutdown_delay,
            }
        }

    def action_reboot_server(self):
        """Ouvrir le wizard de confirmation pour redémarrage serveur"""
        self.check_server_control_access()
        config = self.env['server.control.config'].get_config()

        return {
            'type': 'ir.actions.act_window',
            'name': _('⚠️ Confirmation de redémarrage du serveur'),
            'res_model': 'server.control.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'reboot',
                'default_warning_message': _(
                    "Vous êtes sur le point de REDÉMARRER LE SERVEUR!\n\n"
                    "• Redémarrage dans %d minute(s)\n"
                    "• Interruption temporaire des services\n"
                    "• Le serveur sera de nouveau disponible après ~2-5 minutes\n\n"
                    "Confirmez-vous cette action?"
                ) % config.reboot_delay,
            }
        }

    def action_restart_odoo_service(self):
        """Ouvrir le wizard de confirmation pour redémarrage Odoo"""
        self.check_server_control_access()
        config = self.env['server.control.config'].get_config()

        return {
            'type': 'ir.actions.act_window',
            'name': _('⚠️ Confirmation de redémarrage du service'),
            'res_model': 'server.control.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'restart_odoo',
                'default_warning_message': _(
                    "Vous êtes sur le point de REDÉMARRER le service Odoo!\n\n"
                    "• Service : %s\n"
                    "• Interruption temporaire (~30 secondes)\n"
                    "• Tous les utilisateurs seront déconnectés\n\n"
                    "Confirmez-vous cette action?"
                ) % config.service_name,
            }
        }

    def action_cancel_shutdown(self):
        """Annuler un arrêt/redémarrage programmé"""
        self.check_server_control_access()

        try:
            command = ['sudo', 'shutdown', '-c']
            result = subprocess.run(command, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'info',
                        'title': _('Action annulée'),
                        'message': _('L\'arrêt/redémarrage programmé a été annulé.'),
                    }
                }
            else:
                raise UserError(_("Aucune action programmée à annuler."))
        except Exception as e:
            raise UserError(_("Erreur: %s") % str(e))
