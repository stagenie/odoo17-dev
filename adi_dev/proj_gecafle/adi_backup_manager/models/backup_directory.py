# -*- coding: utf-8 -*-
import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BackupDirectory(models.Model):
    """Configuration et gestion des répertoires de sauvegarde"""
    _name = 'backup.directory'
    _description = 'Répertoire de Sauvegarde'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Nom du répertoire',
        required=True,
        tracking=True
    )

    path = fields.Char(
        string='Chemin absolu',
        required=True,
        help='Chemin complet vers le répertoire de sauvegarde (ex: /home/backup/odoo)',
        tracking=True
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True
    )

    auto_scan = fields.Boolean(
        string='Scan automatique',
        default=False,
        help='Scanner automatiquement ce répertoire à intervalles réguliers'
    )

    scan_interval = fields.Integer(
        string='Intervalle de scan (heures)',
        default=24,
        help='Fréquence de scan en heures'
    )

    last_scan_date = fields.Datetime(
        string='Dernière analyse',
        readonly=True
    )

    retention_days = fields.Integer(
        string='Rétention (jours)',
        default=30,
        help='Nombre de jours de conservation des backups (0 = illimité)'
    )

    file_pattern = fields.Char(
        string='Pattern de fichier',
        default='*.zip,*.sql',
        help='Patterns de fichiers à rechercher, séparés par des virgules',
        required=True
    )

    naming_pattern = fields.Char(
        string='Pattern de nommage',
        default='(?P<db_name>[\w-]+)_(?P<date>\d{8})_(?P<time>\d{6})',
        help='Expression régulière pour extraire les informations du nom de fichier'
    )

    # Statistiques
    total_files = fields.Integer(
        string='Total fichiers',
        compute='_compute_statistics',
        store=True
    )

    total_size = fields.Float(
        string='Taille totale (GB)',
        compute='_compute_statistics',
        store=True
    )

    backup_file_ids = fields.One2many(
        'backup.file',
        'directory_id',
        string='Fichiers de sauvegarde'
    )

    # Chemins additionnels
    local_sync_path = fields.Char(
        string='Chemin de synchronisation local',
        help='Répertoire local pour la synchronisation automatique'
    )

    auto_sync = fields.Boolean(
        string='Synchronisation auto',
        default=False,
        help='Synchroniser automatiquement vers le répertoire local'
    )

    @api.depends('backup_file_ids', 'backup_file_ids.file_size')
    def _compute_statistics(self):
        """Calculer les statistiques du répertoire"""
        for record in self:
            record.total_files = len(record.backup_file_ids)
            record.total_size = sum(record.backup_file_ids.mapped('file_size')) / 1024  # En GB

    @api.constrains('path')
    def _check_path(self):
        """Vérifier que le chemin existe et est accessible"""
        for record in self:
            path = Path(record.path)
            if not path.exists():
                raise ValidationError(_("Le répertoire %s n'existe pas!") % record.path)
            if not path.is_dir():
                raise ValidationError(_("%s n'est pas un répertoire!") % record.path)
            if not os.access(record.path, os.R_OK):
                raise ValidationError(_("Pas d'accès en lecture sur %s!") % record.path)

    @api.constrains('naming_pattern')
    def _check_naming_pattern(self):
        """Vérifier la validité du pattern regex"""
        for record in self:
            if record.naming_pattern:
                try:
                    re.compile(record.naming_pattern)
                except re.error as e:
                    raise ValidationError(_("Pattern regex invalide: %s") % str(e))

    def action_scan_directory(self):
        """Scanner manuellement le répertoire"""
        self.ensure_one()
        return self._scan_directory()

    def action_view_files(self):
        """Ouvrir la vue des fichiers de ce répertoire"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Fichiers de %s') % self.name,
            'res_model': 'backup.file',
            'view_mode': 'tree,form',
            'domain': [('directory_id', '=', self.id)],
            'context': {
                'default_directory_id': self.id,
                'search_default_available': 1,
            }
        }

    def action_view_size(self):
        """Action pour visualiser les détails de taille"""
        self.ensure_one()

        message = _(
            "📊 Détails du répertoire %s:\n"
            "📁 Total fichiers: %d\n"
            "💾 Taille totale: %.2f GB\n"
            "📅 Dernier scan: %s"
        ) % (
                      self.name,
                      self.total_files,
                      self.total_size,
                      self.last_scan_date.strftime('%d/%m/%Y %H:%M') if self.last_scan_date else 'Jamais'
                  )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _('Détails de stockage'),
                'message': message,
                'sticky': True,
            }
        }

    def _scan_directory(self):
        """Scanner le répertoire et créer/mettre à jour les enregistrements de fichiers"""
        self.ensure_one()

        _logger.info(f"🔍 Scan du répertoire: {self.path}")

        try:
            path = Path(self.path)
            patterns = [p.strip() for p in self.file_pattern.split(',')]

            found_files = []
            new_files = 0
            updated_files = 0

            # Rechercher les fichiers selon les patterns
            for pattern in patterns:
                for file_path in path.glob(pattern):
                    if file_path.is_file():
                        file_info = self._extract_file_info(file_path)

                        # Rechercher si le fichier existe déjà
                        existing_file = self.env['backup.file'].search([
                            ('directory_id', '=', self.id),
                            ('file_path', '=', str(file_path))
                        ], limit=1)

                        if existing_file:
                            # Mettre à jour si nécessaire
                            if existing_file.file_size != file_info['file_size']:
                                existing_file.write(file_info)
                                updated_files += 1
                        else:
                            # Créer nouveau fichier
                            file_info['directory_id'] = self.id
                            self.env['backup.file'].create(file_info)
                            new_files += 1

                        found_files.append(str(file_path))

            # Marquer les fichiers non trouvés comme supprimés
            missing_files = self.env['backup.file'].search([
                ('directory_id', '=', self.id),
                ('file_path', 'not in', found_files),
                ('state', '!=', 'deleted')
            ])

            if missing_files:
                missing_files.write({'state': 'deleted'})
                _logger.info(f"📄 {len(missing_files)} fichiers marqués comme supprimés")

            # Mettre à jour la date de scan
            self.last_scan_date = fields.Datetime.now()

            # Nettoyer les vieux fichiers si rétention configurée
            if self.retention_days > 0:
                self._clean_old_files()

            message = _(
                "✅ Scan terminé!\n"
                "📁 Nouveaux fichiers: %d\n"
                "🔄 Fichiers mis à jour: %d\n"
                "📊 Total fichiers: %d"
            ) % (new_files, updated_files, len(found_files))

            _logger.info(message)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Scan terminé'),
                    'message': message,
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Erreur scan: {str(e)}", exc_info=True)
            raise UserError(_("Erreur lors du scan: %s") % str(e))

    def _extract_file_info(self, file_path):
        """Extraire les informations d'un fichier"""
        stat = file_path.stat()
        file_info = {
            'name': file_path.name,
            'file_path': str(file_path),
            'file_size': stat.st_size / (1024 * 1024),  # En MB
            'creation_date': datetime.fromtimestamp(stat.st_ctime),
            'modification_date': datetime.fromtimestamp(stat.st_mtime),
            'file_type': file_path.suffix[1:] if file_path.suffix else 'unknown',
            'state': 'available'
        }

        # Extraire le nom de base de données si possible
        if self.naming_pattern:
            try:
                match = re.match(self.naming_pattern, file_path.name)
                if match:
                    groups = match.groupdict()
                    if 'db_name' in groups:
                        file_info['database_name'] = groups['db_name']
                    if 'date' in groups:
                        # Essayer de parser la date
                        date_str = groups.get('date', '')
                        time_str = groups.get('time', '000000')
                        if len(date_str) == 8:  # Format YYYYMMDD
                            try:
                                backup_datetime = datetime.strptime(
                                    f"{date_str}{time_str}",
                                    '%Y%m%d%H%M%S'
                                )
                                file_info['backup_date'] = backup_datetime
                            except ValueError:
                                pass
            except Exception as e:
                _logger.debug(f"Impossible d'extraire les infos du nom: {e}")

        return file_info

    def _clean_old_files(self):
        """Nettoyer les fichiers plus vieux que la période de rétention"""
        self.ensure_one()

        if self.retention_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        old_files = self.env['backup.file'].search([
            ('directory_id', '=', self.id),
            ('creation_date', '<', cutoff_date),
            ('is_protected', '=', False)
        ])

        if old_files:
            _logger.info(f"🗑️ Suppression de {len(old_files)} anciens fichiers")
            for file in old_files:
                try:
                    # Supprimer physiquement le fichier
                    file_path = Path(file.file_path)
                    if file_path.exists():
                        file_path.unlink()
                    # Supprimer l'enregistrement
                    file.unlink()
                except Exception as e:
                    _logger.error(f"Erreur suppression {file.name}: {e}")

    @api.model
    def cron_scan_directories(self):
        """Tâche planifiée pour scanner automatiquement les répertoires"""
        directories = self.search([
            ('active', '=', True),
            ('auto_scan', '=', True)
        ])

        for directory in directories:
            # Vérifier si c'est le moment de scanner
            if directory.last_scan_date:
                hours_since_scan = (
                                           fields.Datetime.now() - directory.last_scan_date
                                   ).total_seconds() / 3600

                if hours_since_scan < directory.scan_interval:
                    continue

            try:
                _logger.info(f"🔄 Scan automatique de {directory.name}")
                directory._scan_directory()
            except Exception as e:
                _logger.error(f"Erreur scan auto {directory.name}: {e}")
