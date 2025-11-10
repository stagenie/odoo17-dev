# -*- coding: utf-8 -*-
import os
import base64
import zipfile
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BackupFile(models.Model):
    """Fichiers de sauvegarde détectés"""
    _name = 'backup.file'
    _description = 'Fichier de Sauvegarde'
    _order = 'backup_date desc, creation_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Nom du fichier',
        required=True,
        index=True
    )

    directory_id = fields.Many2one(
        'backup.directory',
        string='Répertoire',
        required=True,
        ondelete='cascade'
    )

    file_path = fields.Char(
        string='Chemin complet',
        required=True,
        index=True
    )

    file_size = fields.Float(
        string='Taille (MB)',
        readonly=True,
        help='Taille du fichier en mégaoctets'
    )

    file_size_display = fields.Char(
        string='Taille',
        compute='_compute_size_display',
        store=False
    )

    creation_date = fields.Datetime(
        string='Date de création',
        readonly=True,
        index=True
    )

    modification_date = fields.Datetime(
        string='Date de modification',
        readonly=True
    )

    backup_date = fields.Datetime(
        string='Date du backup',
        help='Date extraite du nom du fichier',
        index=True
    )

    database_name = fields.Char(
        string='Base de données',
        help='Nom de la base extrait du nom de fichier',
        index=True
    )

    file_type = fields.Selection([
        ('zip', 'Archive ZIP'),
        ('sql', 'Dump SQL'),
        ('dump', 'Dump PostgreSQL'),
        ('tar', 'Archive TAR'),
        ('gz', 'Archive GZ'),
        ('unknown', 'Inconnu')
    ], string='Type de fichier', default='unknown')

    state = fields.Selection([
        ('available', 'Disponible'),
        ('downloading', 'Téléchargement'),
        ('downloaded', 'Téléchargé'),
        ('synced', 'Synchronisé'),
        ('deleted', 'Supprimé'),
        ('error', 'Erreur')
    ], string='État', default='available', index=True)

    is_downloaded = fields.Boolean(
        string='Téléchargé',
        default=False
    )

    download_date = fields.Datetime(
        string='Date de téléchargement'
    )

    download_count = fields.Integer(
        string='Nombre de téléchargements',
        default=0
    )

    is_protected = fields.Boolean(
        string='Protégé',
        default=False,
        help='Les fichiers protégés ne sont pas supprimés automatiquement'
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.depends('file_size')
    def _compute_size_display(self):
        """Affichage formaté de la taille"""
        for record in self:
            size_mb = record.file_size
            if size_mb < 1:
                record.file_size_display = f"{size_mb * 1024:.2f} KB"
            elif size_mb < 1024:
                record.file_size_display = f"{size_mb:.2f} MB"
            else:
                record.file_size_display = f"{size_mb / 1024:.2f} GB"

    def action_download_file(self):
        """Télécharger le fichier"""
        self.ensure_one()

        # Vérifier les droits
        if not self.env.user.has_group('adi_backup_manager.group_backup_user'):
            raise UserError(_("Vous n'avez pas les droits pour télécharger des backups!"))

        # Vérifier que le fichier existe
        file_path = Path(self.file_path)
        if not file_path.exists():
            raise UserError(_("Le fichier %s n'existe plus!") % self.name)

        try:
            _logger.info(f"📥 Téléchargement de {self.name} par {self.env.user.name}")

            # Pour les gros fichiers, utiliser le streaming
            if self.file_size > 100:  # Plus de 100 MB
                return self._stream_download()
            else:
                return self._direct_download()

        except Exception as e:
            _logger.error(f"Erreur téléchargement {self.name}: {e}")
            raise UserError(_("Impossible de télécharger: %s") % str(e))

    def _direct_download(self):
        """Téléchargement direct pour petits fichiers"""
        with open(self.file_path, 'rb') as f:
            file_data = f.read()

        # Encoder en base64
        file_base64 = base64.b64encode(file_data).decode('utf-8')

        # Créer un attachment temporaire
        attachment = self.env['ir.attachment'].create({
            'name': self.name,
            'type': 'binary',
            'datas': file_base64,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': self._get_mimetype(),
            'description': f'Backup download: {self.name}'
        })

        # Mettre à jour les stats
        self.write({
            'download_count': self.download_count + 1,
            'download_date': fields.Datetime.now(),
            'is_downloaded': True,
            'state': 'downloaded' if self.state == 'available' else self.state
        })

        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _stream_download(self):
        """Téléchargement en streaming pour gros fichiers"""
        # Créer une URL de téléchargement temporaire
        download_token = self._create_download_token()

        # Mettre à jour les stats
        self.write({
            'download_count': self.download_count + 1,
            'download_date': fields.Datetime.now(),
            'is_downloaded': True,
            'state': 'downloading'
        })

        # Retourner l'URL de streaming
        return {
            'type': 'ir.actions.act_url',
            'url': f'/backup/download/{self.id}/{download_token}',
            'target': 'new',
        }

    def _create_download_token(self):
        """Créer un token de téléchargement sécurisé"""
        import secrets
        token = secrets.token_urlsafe(32)

        # Stocker le token temporairement (cache ou session)
        self.env.cr.execute("""
            INSERT INTO ir_config_parameter (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = %s
        """, (
            f'backup.download.token.{self.id}',
            token,
            token
        ))

        return token

    def _get_mimetype(self):
        """Déterminer le type MIME du fichier"""
        mime_types = {
            'zip': 'application/zip',
            'sql': 'application/sql',
            'dump': 'application/octet-stream',
            'tar': 'application/x-tar',
            'gz': 'application/gzip',
        }
        return mime_types.get(self.file_type, 'application/octet-stream')

    def action_toggle_protection(self):
        """Basculer la protection du fichier"""
        self.ensure_one()
        self.is_protected = not self.is_protected

        message = _("🔒 Fichier protégé") if self.is_protected else _("🔓 Protection retirée")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': message,
                'sticky': False,
            }
        }

    def action_view_content(self):
        """Aperçu du contenu (pour ZIP)"""
        self.ensure_one()

        if self.file_type != 'zip':
            raise UserError(_("L'aperçu n'est disponible que pour les fichiers ZIP"))

        try:
            content_list = []
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                for info in zf.filelist:
                    content_list.append({
                        'name': info.filename,
                        'size': info.file_size / (1024 * 1024),  # En MB
                        'date': datetime(*info.date_time)
                    })

            # Créer un wizard pour afficher le contenu
            wizard = self.env['backup.content.viewer'].create({
                'file_id': self.id,
                'content_text': self._format_content_list(content_list)
            })

            return {
                'type': 'ir.actions.act_window',
                'name': _('Contenu de %s') % self.name,
                'res_model': 'backup.content.viewer',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

        except Exception as e:
            raise UserError(_("Impossible de lire le contenu: %s") % str(e))

    def _format_content_list(self, content_list):
        """Formater la liste du contenu pour affichage"""
        lines = [f"📦 Contenu de l'archive ({len(content_list)} fichiers)\n" + "=" * 50]

        for item in sorted(content_list, key=lambda x: x['name']):
            size_str = f"{item['size']:.2f} MB" if item['size'] >= 1 else f"{item['size'] * 1024:.2f} KB"
            date_str = item['date'].strftime('%Y-%m-%d %H:%M')
            lines.append(f"📄 {item['name']:<40} {size_str:>10} {date_str:>20}")

        return "\n".join(lines)

    @api.model
    def action_download_multiple(self, file_ids):
        """Télécharger plusieurs fichiers dans une archive"""
        files = self.browse(file_ids)

        if not files:
            raise UserError(_("Aucun fichier sélectionné"))

        # Créer une archive ZIP temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in files:
                    if Path(file.file_path).exists():
                        zf.write(file.file_path, file.name)
                        _logger.info(f"Ajout de {file.name} à l'archive")

            tmp_path = tmp_file.name

        # Lire l'archive créée
        with open(tmp_path, 'rb') as f:
            archive_data = f.read()

        # Nettoyer
        try:
            os.unlink(tmp_path)
        except:
            pass

        # Créer l'attachment
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        attachment = self.env['ir.attachment'].create({
            'name': f'backups_batch_{timestamp}.zip',
            'type': 'binary',
            'datas': base64.b64encode(archive_data).decode('utf-8'),
            'res_model': 'backup.file',
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
