# -*- coding: utf-8 -*-
import subprocess
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServerControlWizard(models.TransientModel):
    """Wizard de confirmation et exécution des actions"""
    _name = 'server.control.wizard'
    _description = 'Wizard de contrôle serveur'

    action_type = fields.Selection([
        ('shutdown', 'Arrêt du serveur'),
        ('reboot', 'Redémarrage du serveur'),
        ('restart_odoo', 'Redémarrage du service Odoo'),
    ], string='Type d\'action', required=True)

    warning_message = fields.Text(
        string='Avertissement',
        readonly=True
    )

    confirmation_text = fields.Char(
        string='Tapez OK pour continuer'
    )

    def action_confirm(self):
        """Exécuter l'action après confirmation"""
        self.ensure_one()

        # Vérifier la confirmation
        if self.confirmation_text != 'OK':
            raise UserError(_('Vous devez taper exactement "OK" pour continuer.'))

        # Vérifier les droits
        if not self.env.user.has_group('adi_server_control.group_server_control'):
            raise UserError(_("Droits insuffisants!"))

        config = self.env['server.control.config'].get_config()

        # Exécuter l'action appropriée
        if self.action_type == 'shutdown':
            return self._execute_shutdown(config)
        elif self.action_type == 'reboot':
            return self._execute_reboot(config)
        elif self.action_type == 'restart_odoo':
            return self._execute_restart_odoo(config)

    def _execute_shutdown(self, config):
        """Exécuter l'arrêt du serveur"""
        try:
            command = [
                'sudo', 'shutdown', '-h',
                '+%d' % config.shutdown_delay,
                'Arrêt programmé par Odoo'
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                _logger.info(f"Arrêt du serveur programmé par {self.env.user.name}")

                if config.enable_logging:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _('✅ Arrêt programmé'),
                            'message': _('Le serveur s\'arrêtera dans %d minute(s).') % config.shutdown_delay,
                            'sticky': True,
                        }
                    }
            else:
                raise UserError(_("Erreur: %s") % (result.stderr or 'Commande échouée'))

        except Exception as e:
            _logger.error(f"Erreur arrêt serveur: {str(e)}")
            raise UserError(_("Impossible d'arrêter le serveur: %s") % str(e))

    def _execute_reboot(self, config):
        """Exécuter le redémarrage du serveur"""
        try:
            command = [
                'sudo', 'shutdown', '-r',
                '+%d' % config.reboot_delay,
                'Redémarrage programmé par Odoo'
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                _logger.info(f"Redémarrage serveur programmé par {self.env.user.name}")

                if config.enable_logging:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'warning',
                            'title': _('🔄 Redémarrage programmé'),
                            'message': _('Le serveur redémarrera dans %d minute(s).') % config.reboot_delay,
                            'sticky': True,
                        }
                    }
            else:
                raise UserError(_("Erreur: %s") % (result.stderr or 'Commande échouée'))

        except Exception as e:
            _logger.error(f"Erreur redémarrage serveur: {str(e)}")
            raise UserError(_("Impossible de redémarrer le serveur: %s") % str(e))

    def _execute_restart_odoo(self, config):
        """Exécuter le redémarrage du service Odoo"""
        try:
            command = ['sudo', 'systemctl', 'restart', config.service_name]

            result = subprocess.run(command, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                _logger.info(f"Service {config.service_name} redémarré par {self.env.user.name}")

                if config.enable_logging:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _('✅ Service redémarré'),
                            'message': _('Le service %s a été redémarré.') % config.service_name,
                            'sticky': False,
                        }
                    }
            else:
                raise UserError(_("Erreur: %s") % (result.stderr or 'Commande échouée'))

        except Exception as e:
            _logger.error(f"Erreur redémarrage Odoo: {str(e)}")
            raise UserError(_("Impossible de redémarrer le service: %s") % str(e))

    def action_cancel(self):
        """Annuler et fermer le wizard"""
        return {'type': 'ir.actions.act_window_close'}
