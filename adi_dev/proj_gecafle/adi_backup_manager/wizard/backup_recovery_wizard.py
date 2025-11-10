# -*- coding: utf-8 -*-
import logging
import shutil
from pathlib import Path
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BackupRecoveryWizard(models.TransientModel):
    """Assistant de récupération des sauvegardes"""
    _name = 'backup.recovery.wizard'
    _description = 'Assistant de Récupération'

    directory_id = fields.Many2one(
        'backup.directory',
        string='Répertoire',
        required=True,
        default=lambda self: self._get_default_directory()
    )

    backup_file_ids = fields.Many2many(
        'backup.file',
        string='Fichiers disponibles',
        compute='_compute_available_files',
        readonly=True
    )

    selected_file_ids = fields.Many2many(
        'backup.file',
        'recovery_wizard_file_rel',
        'wizard_id',
        'file_id',
        string='Fichiers sélectionnés'
    )

    action_type = fields.Selection([
        ('download', 'Télécharger'),
        ('download_batch', 'Télécharger en lot'),
        ('sync', 'Synchroniser localement'),
    ], string='Action', default='download', required=True)

    filter_database = fields.Char(
        string='Filtrer par base',
        help='Nom de la base de données à filtrer'
    )

    filter_date_from = fields.Date(
        string='Date début'
    )

    filter_date_to = fields.Date(
        string='Date fin'
    )

    total_size = fields.Float(
        string='Taille totale (MB)',
        compute='_compute_total_size',
        readonly=True
    )

    total_size_display = fields.Char(
        string='Taille totale',
        compute='_compute_size_display',
        readonly=True
    )

    @api.model
    def _get_default_directory(self):
        """Récupérer le premier répertoire actif"""
        return self.env['backup.directory'].search([
            ('active', '=', True)
        ], limit=1)

    @api.depends('directory_id', 'filter_database', 'filter_date_from', 'filter_date_to')
    def _compute_available_files(self):
        """Calculer les fichiers disponibles selon les filtres"""
        for wizard in self:
            domain = [
                ('directory_id', '=', wizard.directory_id.id),
                ('state', 'in', ['available', 'downloaded', 'synced'])
            ]

            if wizard.filter_database:
                domain.append(('database_name', 'ilike', wizard.filter_database))

            if wizard.filter_date_from:
                domain.append(('backup_date', '>=', wizard.filter_date_from))

            if wizard.filter_date_to:
                domain.append(('backup_date', '<=', wizard.filter_date_to))

            wizard.backup_file_ids = self.env['backup.file'].search(domain, order='backup_date desc')

    @api.depends('selected_file_ids')
    def _compute_total_size(self):
        """Calculer la taille totale des fichiers sélectionnés"""
        for wizard in self:
            wizard.total_size = sum(wizard.selected_file_ids.mapped('file_size'))

    @api.depends('total_size')
    def _compute_size_display(self):
        """Affichage intelligent de la taille"""
        for wizard in self:
            size_mb = wizard.total_size
            if size_mb < 1024:
                wizard.total_size_display = f"{size_mb:.2f} MB"
            else:
                wizard.total_size_display = f"{size_mb / 1024:.2f} GB"

    def action_scan_first(self):
        """Scanner le répertoire et recharger le wizard"""
        self.ensure_one()

        try:
            # Scanner le répertoire
            _logger.info(f"Scan du répertoire {self.directory_id.name}")
            self.directory_id.action_scan_directory()

            # Message de succès
            message = _("✅ Scan terminé! Les fichiers ont été mis à jour.")

            # Retourner l'action pour recharger le wizard avec les nouveaux fichiers
            return {
                'type': 'ir.actions.act_window',
                'name': _('💾 Récupération de Backups'),
                'res_model': 'backup.recovery.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_directory_id': self.directory_id.id,
                    'default_filter_database': self.filter_database,
                    'default_filter_date_from': self.filter_date_from,
                    'default_filter_date_to': self.filter_date_to,
                    'default_action_type': self.action_type,
                    'default_selected_file_ids': [(6, 0, self.selected_file_ids.ids)],
                    'show_notification': True,
                    'notification_message': message
                }
            }
        except Exception as e:
            _logger.error(f"Erreur lors du scan: {e}")
            raise UserError(_("Erreur lors du scan: %s") % str(e))

    def action_execute(self):
        """Exécuter l'action sélectionnée"""
        self.ensure_one()

        if not self.selected_file_ids:
            raise UserError(_("Veuillez sélectionner au moins un fichier"))

        if self.action_type == 'download':
            # Téléchargement simple du premier fichier
            if len(self.selected_file_ids) == 1:
                return self.selected_file_ids[0].action_download_file()
            else:
                # Si plusieurs fichiers, proposer le téléchargement en lot
                return self.env['backup.file'].action_download_multiple(
                    self.selected_file_ids.ids
                )

        elif self.action_type == 'download_batch':
            # Téléchargement en lot
            return self.env['backup.file'].action_download_multiple(
                self.selected_file_ids.ids
            )

        elif self.action_type == 'sync':
            # Synchronisation locale
            return self._sync_files_locally()

        return {'type': 'ir.actions.act_window_close'}

    def _sync_files_locally(self):
        """Synchroniser les fichiers vers un répertoire local"""
        if not self.directory_id.local_sync_path:
            raise UserError(_("Aucun chemin de synchronisation configuré dans le répertoire"))

        sync_path = Path(self.directory_id.local_sync_path)

        # Créer le répertoire s'il n'existe pas
        try:
            sync_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise UserError(_("Impossible de créer le répertoire de synchronisation: %s") % str(e))

        synced = 0
        errors = 0
        error_messages = []

        for file in self.selected_file_ids:
            try:
                source = Path(file.file_path)
                if source.exists():
                    dest = sync_path / file.name
                    shutil.copy2(str(source), str(dest))
                    file.write({'state': 'synced'})
                    synced += 1
                    _logger.info(f"✅ Synchronisé: {file.name}")
                else:
                    errors += 1
                    error_messages.append(f"{file.name}: Fichier source introuvable")
                    _logger.warning(f"Fichier introuvable: {file.file_path}")

            except Exception as e:
                errors += 1
                error_messages.append(f"{file.name}: {str(e)}")
                _logger.error(f"❌ Erreur sync {file.name}: {e}")

        # Construire le message de résultat
        message_parts = [_("Synchronisation terminée!")]
        if synced > 0:
            message_parts.append(_("✅ Fichiers copiés: %d") % synced)
        if errors > 0:
            message_parts.append(_("❌ Erreurs: %d") % errors)
            if error_messages:
                message_parts.append(_("\nDétails des erreurs:"))
                for err_msg in error_messages[:5]:  # Limiter à 5 messages
                    message_parts.append(f"  • {err_msg}")
                if len(error_messages) > 5:
                    message_parts.append(f"  ... et {len(error_messages) - 5} autres erreurs")

        message = "\n".join(message_parts)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if errors == 0 else 'warning',
                'title': _('Synchronisation'),
                'message': message,
                'sticky': True,
            }
        }

    @api.model
    def default_get(self, fields_list):
        """Initialiser avec notification si présente dans le contexte"""
        res = super().default_get(fields_list)

        # Afficher une notification si demandé
        if self.env.context.get('show_notification'):
            message = self.env.context.get('notification_message')
            if message:
                # Note: La notification sera affichée via JavaScript
                _logger.info(f"Notification: {message}")

        return res
