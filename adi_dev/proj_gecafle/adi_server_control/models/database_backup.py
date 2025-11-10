# -*- coding: utf-8 -*-
import os
import base64
import subprocess
import logging
import tempfile
import zipfile
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import config
from odoo.service import db

_logger = logging.getLogger(__name__)


class DatabaseBackupWizard(models.TransientModel):
    """Wizard pour backup de base de données"""
    _name = 'database.backup.wizard'
    _description = 'Assistant de sauvegarde de base de données'

    backup_type = fields.Selection([
        ('download', 'Télécharger maintenant'),
       # ('server', 'Sauvegarder sur le serveur'),
    ], string='Type de sauvegarde', default='download', required=True)

    backup_path = fields.Char(
        string='Dossier de destination',
        default='/home/odoo/backups',
        required=False,
        help='Chemin sur le serveur pour sauvegarder le fichier'
    )

    include_filestore = fields.Boolean(
        string='Inclure les fichiers joints',
        default=True,
        help='Inclure le filestore (pièces jointes) dans la sauvegarde'
    )

    database_name = fields.Char(
        string='Base de données',
        default=lambda self: self._get_database_name(),
        readonly=True
    )

    @api.model
    def _get_database_name(self):
        """Récupérer le nom de la base actuelle"""
        return self.env.cr.dbname

    def _safe_str(self, value, default=''):
        """Convertir toute valeur en chaîne de manière sûre"""
        if value in [False, None]:
            return default
        return str(value)

    def _get_db_config(self):
        """Récupérer la configuration PostgreSQL de manière sûre"""
        # Récupérer l'utilisateur
        db_user = config.get('db_user', False)
        if not db_user or db_user == False:
            db_user = os.environ.get('USER', 'odoo')

        # Récupérer le mot de passe
        db_password = config.get('db_password', False)
        if db_password in [False, None, '']:
            db_password = None

        # Récupérer l'hôte
        db_host = config.get('db_host', False)
        if not db_host or db_host == False:
            db_host = 'localhost'

        # Récupérer le port
        db_port = config.get('db_port', False)
        if not db_port or db_port == False:
            db_port = '5432'

        return {
            'user': self._safe_str(db_user, 'odoo'),
            'password': db_password if db_password else None,
            'host': self._safe_str(db_host, 'localhost'),
            'port': self._safe_str(db_port, '5432')
        }

    def action_backup_database(self):
        """Exécuter la sauvegarde ZIP uniquement"""
        self.ensure_one()

        # Vérifier les droits
        if not self.env.user.has_group('adi_server_control.group_server_control'):
            raise AccessError(_("Vous n'avez pas les droits pour effectuer une sauvegarde!"))

        db_name = self.database_name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{db_name}_backup_{timestamp}.zip"

        try:
            if self.backup_type == 'server':
                return self._backup_to_server(db_name, filename)
            else:
                return self._backup_to_download(db_name, filename)
        except Exception as e:
            _logger.error(f"Erreur backup: {str(e)}", exc_info=True)
            raise UserError(_("Erreur lors de la sauvegarde: %s") % str(e))

    def _backup_to_server(self, db_name, filename):
        """Sauvegarde ZIP sur le serveur - VERSION FINALE CORRIGÉE"""
        try:
            # Gérer le chemin de sauvegarde de manière sûre
            backup_path = self.backup_path

            # S'assurer que backup_path est une chaîne valide
            if not backup_path or backup_path in [False, None, '']:
                backup_path = '/tmp'
            else:
                backup_path = str(backup_path).strip()

            # Expandre le chemin utilisateur (~)
            backup_path = os.path.expanduser(backup_path)

            # Créer le dossier si nécessaire
            try:
                os.makedirs(backup_path, exist_ok=True)
            except Exception as e:
                _logger.error(f"Impossible de créer le dossier {backup_path}: {e}")
                # Utiliser /tmp comme fallback
                backup_path = '/tmp'
                _logger.warning(f"Utilisation de /tmp comme dossier de sauvegarde")

            # Construire le chemin complet du fichier
            backup_file = os.path.join(backup_path, filename)

            # Récupérer la configuration DB
            db_config = self._get_db_config()

            _logger.info(f"=== DÉBUT BACKUP ===")
            _logger.info(f"Base de données: {db_name}")
            _logger.info(f"Fichier de destination: {backup_file}")
            _logger.info(f"Config DB - Host: {db_config['host']}, User: {db_config['user']}, Port: {db_config['port']}")
            _logger.info(f"Inclure filestore: {self.include_filestore}")

            # Utiliser un dossier temporaire pour la création
            with tempfile.TemporaryDirectory() as temp_dir:
                # Créer le dump SQL
                temp_sql = os.path.join(temp_dir, f"{db_name}.sql")

                # Configuration des variables d'environnement
                env_vars = os.environ.copy()
                if db_config['password']:
                    env_vars['PGPASSWORD'] = str(db_config['password'])

                # Construire la commande pg_dump
                dump_cmd = [
                    'pg_dump',
                    '-h', db_config['host'],
                    '-p', db_config['port'],
                    '-U', db_config['user'],
                    '-d', db_name,
                    '-f', temp_sql,
                    '--no-owner',
                    '--no-acl',
                    '--verbose'
                ]

                _logger.info(f"Exécution de: {' '.join(dump_cmd)}")

                # Exécuter pg_dump
                try:
                    result = subprocess.run(
                        dump_cmd,
                        env=env_vars,
                        capture_output=True,
                        text=True,
                        timeout=300  # Timeout de 5 minutes
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr or result.stdout or "Erreur inconnue lors du dump"
                        _logger.error(f"Erreur pg_dump (code {result.returncode}): {error_msg}")

                        # Vérifier si c'est un problème d'authentification
                        if "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                            raise UserError(_(
                                "Erreur d'authentification PostgreSQL.\n"
                                "Vérifiez la configuration dans odoo.conf:\n"
                                "- db_user\n"
                                "- db_password\n"
                                "- db_host\n"
                                "- db_port"
                            ))
                        else:
                            raise UserError(_("Erreur pg_dump: %s") % error_msg)

                    _logger.info("✓ pg_dump exécuté avec succès")

                except subprocess.TimeoutExpired:
                    raise UserError(_("La sauvegarde a pris trop de temps (>5 minutes)"))
                except FileNotFoundError:
                    raise UserError(_(
                        "pg_dump n'est pas installé ou accessible.\n"
                        "Installez postgresql-client:\n"
                        "sudo apt-get install postgresql-client"
                    ))

                # Vérifier que le dump a été créé
                if not os.path.exists(temp_sql):
                    raise UserError(_("Le fichier de dump SQL n'a pas été créé"))

                sql_size = os.path.getsize(temp_sql) / (1024 * 1024)  # En MB
                _logger.info(f"✓ Dump SQL créé: {sql_size:.2f} MB")

                # Créer l'archive ZIP
                _logger.info(f"Création de l'archive ZIP: {backup_file}")
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Ajouter le dump SQL
                    zf.write(temp_sql, f"{db_name}.sql")
                    _logger.info("✓ SQL ajouté au ZIP")

                    # Ajouter le filestore si demandé
                    if self.include_filestore:
                        filestore_path = config.filestore(db_name)

                        if filestore_path and os.path.exists(filestore_path):
                            _logger.info(f"Ajout du filestore depuis: {filestore_path}")

                            file_count = 0
                            total_size = 0

                            for root, dirs, files in os.walk(filestore_path):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        # Chemin relatif dans l'archive
                                        arc_path = os.path.join(
                                            'filestore',
                                            os.path.relpath(file_path, filestore_path)
                                        )
                                        zf.write(file_path, arc_path)
                                        file_count += 1
                                        total_size += os.path.getsize(file_path)

                                        # Log de progression
                                        if file_count % 100 == 0:
                                            _logger.info(f"Progression: {file_count} fichiers ajoutés...")
                                    except Exception as e:
                                        _logger.warning(f"Impossible d'ajouter {file}: {e}")

                            filestore_size_mb = total_size / (1024 * 1024)
                            _logger.info(f"✓ Filestore ajouté: {file_count} fichiers ({filestore_size_mb:.2f} MB)")
                        else:
                            _logger.warning(f"Filestore non trouvé ou vide: {filestore_path}")

                _logger.info("✓ Archive ZIP créée avec succès")

            # Vérifier la taille finale
            if os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file) / (1024 * 1024)  # En MB
                _logger.info(f"=== BACKUP TERMINÉ ===")
                _logger.info(f"Fichier: {backup_file}")
                _logger.info(f"Taille: {file_size:.2f} MB")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'title': _('✅ Sauvegarde réussie'),
                        'message': _(
                            '📦 Backup créé avec succès!\n'
                            '📁 Fichier: %s\n'
                            '💾 Taille: %.2f MB'
                        ) % (backup_file, file_size),
                        'sticky': True,
                    }
                }
            else:
                raise UserError(_("Le fichier de backup n'a pas été créé"))

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Erreur inattendue backup serveur: {str(e)}", exc_info=True)
            raise UserError(_("Erreur inattendue: %s") % str(e))

    def _backup_to_download(self, db_name, filename):
        """Créer un backup pour téléchargement direct"""
        try:
            _logger.info(f"Création du backup pour téléchargement: {filename}")

            # Utiliser un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                temp_path = tmp_file.name

                # Utiliser l'API native Odoo pour créer le backup
                db.dump_db(db_name, tmp_file, 'zip')

                # Lire le fichier créé
                with open(temp_path, 'rb') as f:
                    backup_data = f.read()

                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_path)
                except:
                    pass

            # Encoder en base64
            backup_base64 = base64.b64encode(backup_data).decode('utf-8')

            # Créer l'attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': backup_base64,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/zip',
                'description': f'Database backup of {db_name}',
            })

            _logger.info(f"✅ Téléchargement prêt: {attachment.name}")

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except Exception as e:
            _logger.error(f"Erreur création download: {str(e)}", exc_info=True)
            raise UserError(_("Impossible de créer le téléchargement: %s") % str(e))


# -*- coding: utf-8 -*-
import os
import base64
import subprocess
import logging
import tempfile
import zipfile
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import config
from odoo.service import db

_logger = logging.getLogger(__name__)


class DatabaseBackupWizard(models.TransientModel):
    """Wizard pour backup de base de données"""
    _name = 'database.backup.wizard'
    _description = 'Assistant de sauvegarde de base de données'

    backup_type = fields.Selection([
        ('download', 'Télécharger maintenant'),
       # ('server', 'Sauvegarder sur le serveur'),
    ], string='Type de sauvegarde', default='download', required=True)

    backup_path = fields.Char(
        string='Dossier de destination',
        default='/home/odoo/backups',
        required=False,
        help='Chemin sur le serveur pour sauvegarder le fichier'
    )

    include_filestore = fields.Boolean(
        string='Inclure les fichiers joints',
        default=True,
        help='Inclure le filestore (pièces jointes) dans la sauvegarde'
    )

    database_name = fields.Char(
        string='Base de données',
        default=lambda self: self._get_database_name(),
        readonly=True
    )

    @api.model
    def _get_database_name(self):
        """Récupérer le nom de la base actuelle"""
        return self.env.cr.dbname

    def _safe_str(self, value, default=''):
        """Convertir toute valeur en chaîne de manière sûre"""
        if value in [False, None]:
            return default
        return str(value)

    def _get_db_config(self):
        """Récupérer la configuration PostgreSQL de manière sûre"""
        # Récupérer l'utilisateur
        db_user = config.get('db_user', False)
        if not db_user or db_user == False:
            db_user = os.environ.get('USER', 'odoo')

        # Récupérer le mot de passe
        db_password = config.get('db_password', False)
        if db_password in [False, None, '']:
            db_password = None

        # Récupérer l'hôte
        db_host = config.get('db_host', False)
        if not db_host or db_host == False:
            db_host = 'localhost'

        # Récupérer le port
        db_port = config.get('db_port', False)
        if not db_port or db_port == False:
            db_port = '5432'

        return {
            'user': self._safe_str(db_user, 'odoo'),
            'password': db_password if db_password else None,
            'host': self._safe_str(db_host, 'localhost'),
            'port': self._safe_str(db_port, '5432')
        }

    def action_backup_database(self):
        """Exécuter la sauvegarde ZIP uniquement"""
        self.ensure_one()

        # Vérifier les droits
        if not self.env.user.has_group('adi_server_control.group_server_control'):
            raise AccessError(_("Vous n'avez pas les droits pour effectuer une sauvegarde!"))

        db_name = self.database_name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{db_name}_backup_{timestamp}.zip"

        try:
            if self.backup_type == 'server':
                return self._backup_to_server(db_name, filename)
            else:
                return self._backup_to_download(db_name, filename)
        except Exception as e:
            _logger.error(f"Erreur backup: {str(e)}", exc_info=True)
            raise UserError(_("Erreur lors de la sauvegarde: %s") % str(e))

    def _backup_to_server(self, db_name, filename):
        """Sauvegarde ZIP sur le serveur - VERSION FINALE CORRIGÉE"""
        try:
            # Gérer le chemin de sauvegarde de manière sûre
            backup_path = self.backup_path

            # S'assurer que backup_path est une chaîne valide
            if not backup_path or backup_path in [False, None, '']:
                backup_path = '/tmp'
            else:
                backup_path = str(backup_path).strip()

            # Expandre le chemin utilisateur (~)
            backup_path = os.path.expanduser(backup_path)

            # Créer le dossier si nécessaire
            try:
                os.makedirs(backup_path, exist_ok=True)
            except Exception as e:
                _logger.error(f"Impossible de créer le dossier {backup_path}: {e}")
                # Utiliser /tmp comme fallback
                backup_path = '/tmp'
                _logger.warning(f"Utilisation de /tmp comme dossier de sauvegarde")

            # Construire le chemin complet du fichier
            backup_file = os.path.join(backup_path, filename)

            # Récupérer la configuration DB
            db_config = self._get_db_config()

            _logger.info(f"=== DÉBUT BACKUP ===")
            _logger.info(f"Base de données: {db_name}")
            _logger.info(f"Fichier de destination: {backup_file}")
            _logger.info(f"Config DB - Host: {db_config['host']}, User: {db_config['user']}, Port: {db_config['port']}")
            _logger.info(f"Inclure filestore: {self.include_filestore}")

            # Utiliser un dossier temporaire pour la création
            with tempfile.TemporaryDirectory() as temp_dir:
                # Créer le dump SQL
                temp_sql = os.path.join(temp_dir, f"{db_name}.sql")

                # Configuration des variables d'environnement
                env_vars = os.environ.copy()
                if db_config['password']:
                    env_vars['PGPASSWORD'] = str(db_config['password'])

                # Construire la commande pg_dump
                dump_cmd = [
                    'pg_dump',
                    '-h', db_config['host'],
                    '-p', db_config['port'],
                    '-U', db_config['user'],
                    '-d', db_name,
                    '-f', temp_sql,
                    '--no-owner',
                    '--no-acl',
                    '--verbose'
                ]

                _logger.info(f"Exécution de: {' '.join(dump_cmd)}")

                # Exécuter pg_dump
                try:
                    result = subprocess.run(
                        dump_cmd,
                        env=env_vars,
                        capture_output=True,
                        text=True,
                        timeout=300  # Timeout de 5 minutes
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr or result.stdout or "Erreur inconnue lors du dump"
                        _logger.error(f"Erreur pg_dump (code {result.returncode}): {error_msg}")

                        # Vérifier si c'est un problème d'authentification
                        if "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                            raise UserError(_(
                                "Erreur d'authentification PostgreSQL.\n"
                                "Vérifiez la configuration dans odoo.conf:\n"
                                "- db_user\n"
                                "- db_password\n"
                                "- db_host\n"
                                "- db_port"
                            ))
                        else:
                            raise UserError(_("Erreur pg_dump: %s") % error_msg)

                    _logger.info("✓ pg_dump exécuté avec succès")

                except subprocess.TimeoutExpired:
                    raise UserError(_("La sauvegarde a pris trop de temps (>5 minutes)"))
                except FileNotFoundError:
                    raise UserError(_(
                        "pg_dump n'est pas installé ou accessible.\n"
                        "Installez postgresql-client:\n"
                        "sudo apt-get install postgresql-client"
                    ))

                # Vérifier que le dump a été créé
                if not os.path.exists(temp_sql):
                    raise UserError(_("Le fichier de dump SQL n'a pas été créé"))

                sql_size = os.path.getsize(temp_sql) / (1024 * 1024)  # En MB
                _logger.info(f"✓ Dump SQL créé: {sql_size:.2f} MB")

                # Créer l'archive ZIP
                _logger.info(f"Création de l'archive ZIP: {backup_file}")
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Ajouter le dump SQL
                    zf.write(temp_sql, f"{db_name}.sql")
                    _logger.info("✓ SQL ajouté au ZIP")

                    # Ajouter le filestore si demandé
                    if self.include_filestore:
                        filestore_path = config.filestore(db_name)

                        if filestore_path and os.path.exists(filestore_path):
                            _logger.info(f"Ajout du filestore depuis: {filestore_path}")

                            file_count = 0
                            total_size = 0

                            for root, dirs, files in os.walk(filestore_path):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        # Chemin relatif dans l'archive
                                        arc_path = os.path.join(
                                            'filestore',
                                            os.path.relpath(file_path, filestore_path)
                                        )
                                        zf.write(file_path, arc_path)
                                        file_count += 1
                                        total_size += os.path.getsize(file_path)

                                        # Log de progression
                                        if file_count % 100 == 0:
                                            _logger.info(f"Progression: {file_count} fichiers ajoutés...")
                                    except Exception as e:
                                        _logger.warning(f"Impossible d'ajouter {file}: {e}")

                            filestore_size_mb = total_size / (1024 * 1024)
                            _logger.info(f"✓ Filestore ajouté: {file_count} fichiers ({filestore_size_mb:.2f} MB)")
                        else:
                            _logger.warning(f"Filestore non trouvé ou vide: {filestore_path}")

                _logger.info("✓ Archive ZIP créée avec succès")

            # Vérifier la taille finale
            if os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file) / (1024 * 1024)  # En MB
                _logger.info(f"=== BACKUP TERMINÉ ===")
                _logger.info(f"Fichier: {backup_file}")
                _logger.info(f"Taille: {file_size:.2f} MB")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'title': _('✅ Sauvegarde réussie'),
                        'message': _(
                            '📦 Backup créé avec succès!\n'
                            '📁 Fichier: %s\n'
                            '💾 Taille: %.2f MB'
                        ) % (backup_file, file_size),
                        'sticky': True,
                    }
                }
            else:
                raise UserError(_("Le fichier de backup n'a pas été créé"))

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Erreur inattendue backup serveur: {str(e)}", exc_info=True)
            raise UserError(_("Erreur inattendue: %s") % str(e))

    def _backup_to_download(self, db_name, filename):
        """Créer un backup pour téléchargement direct"""
        try:
            _logger.info(f"Création du backup pour téléchargement: {filename}")

            # Utiliser un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                temp_path = tmp_file.name

                # Utiliser l'API native Odoo pour créer le backup
                db.dump_db(db_name, tmp_file, 'zip')

                # Lire le fichier créé
                with open(temp_path, 'rb') as f:
                    backup_data = f.read()

                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_path)
                except:
                    pass

            # Encoder en base64
            backup_base64 = base64.b64encode(backup_data).decode('utf-8')

            # Créer l'attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': backup_base64,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/zip',
                'description': f'Database backup of {db_name}',
            })

            _logger.info(f"✅ Téléchargement prêt: {attachment.name}")

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except Exception as e:
            _logger.error(f"Erreur création download: {str(e)}", exc_info=True)
            raise UserError(_("Impossible de créer le téléchargement: %s") % str(e))


# -*- coding: utf-8 -*-
import os
import base64
import subprocess
import logging
import tempfile
import zipfile
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import config
from odoo.service import db

_logger = logging.getLogger(__name__)


class DatabaseBackupWizard(models.TransientModel):
    """Wizard pour backup de base de données"""
    _name = 'database.backup.wizard'
    _description = 'Assistant de sauvegarde de base de données'

    backup_type = fields.Selection([
        ('download', 'Télécharger maintenant'),
      #  ('server', 'Sauvegarder sur le serveur'),
    ], string='Type de sauvegarde', default='download', required=True)

    backup_path = fields.Char(
        string='Dossier de destination',
        default='/home/odoo/backups',
        required=False,
        help='Chemin sur le serveur pour sauvegarder le fichier'
    )

    include_filestore = fields.Boolean(
        string='Inclure les fichiers joints',
        default=True,
        help='Inclure le filestore (pièces jointes) dans la sauvegarde'
    )

    database_name = fields.Char(
        string='Base de données',
        default=lambda self: self._get_database_name(),
        readonly=True
    )

    @api.model
    def _get_database_name(self):
        """Récupérer le nom de la base actuelle"""
        return self.env.cr.dbname

    def _safe_str(self, value, default=''):
        """Convertir toute valeur en chaîne de manière sûre"""
        if value in [False, None]:
            return default
        return str(value)

    def _get_db_config(self):
        """Récupérer la configuration PostgreSQL de manière sûre"""
        # Récupérer l'utilisateur
        db_user = config.get('db_user', False)
        if not db_user or db_user == False:
            db_user = os.environ.get('USER', 'odoo')

        # Récupérer le mot de passe
        db_password = config.get('db_password', False)
        if db_password in [False, None, '']:
            db_password = None

        # Récupérer l'hôte
        db_host = config.get('db_host', False)
        if not db_host or db_host == False:
            db_host = 'localhost'

        # Récupérer le port
        db_port = config.get('db_port', False)
        if not db_port or db_port == False:
            db_port = '5432'

        return {
            'user': self._safe_str(db_user, 'odoo'),
            'password': db_password if db_password else None,
            'host': self._safe_str(db_host, 'localhost'),
            'port': self._safe_str(db_port, '5432')
        }

    def action_backup_database(self):
        """Exécuter la sauvegarde ZIP uniquement"""
        self.ensure_one()

        # Vérifier les droits
        if not self.env.user.has_group('adi_server_control.group_server_control'):
            raise AccessError(_("Vous n'avez pas les droits pour effectuer une sauvegarde!"))

        db_name = self.database_name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{db_name}_backup_{timestamp}.zip"

        try:
            if self.backup_type == 'server':
                return self._backup_to_server(db_name, filename)
            else:
                return self._backup_to_download(db_name, filename)
        except Exception as e:
            _logger.error(f"Erreur backup: {str(e)}", exc_info=True)
            raise UserError(_("Erreur lors de la sauvegarde: %s") % str(e))

    def _backup_to_server(self, db_name, filename):
        """Sauvegarde ZIP sur le serveur - VERSION FINALE CORRIGÉE"""
        try:
            # Gérer le chemin de sauvegarde de manière sûre
            backup_path = self.backup_path

            # S'assurer que backup_path est une chaîne valide
            if not backup_path or backup_path in [False, None, '']:
                backup_path = '/tmp'
            else:
                backup_path = str(backup_path).strip()

            # Expandre le chemin utilisateur (~)
            backup_path = os.path.expanduser(backup_path)

            # Créer le dossier si nécessaire
            try:
                os.makedirs(backup_path, exist_ok=True)
            except Exception as e:
                _logger.error(f"Impossible de créer le dossier {backup_path}: {e}")
                # Utiliser /tmp comme fallback
                backup_path = '/tmp'
                _logger.warning(f"Utilisation de /tmp comme dossier de sauvegarde")

            # Construire le chemin complet du fichier
            backup_file = os.path.join(backup_path, filename)

            # Récupérer la configuration DB
            db_config = self._get_db_config()

            _logger.info(f"=== DÉBUT BACKUP ===")
            _logger.info(f"Base de données: {db_name}")
            _logger.info(f"Fichier de destination: {backup_file}")
            _logger.info(f"Config DB - Host: {db_config['host']}, User: {db_config['user']}, Port: {db_config['port']}")
            _logger.info(f"Inclure filestore: {self.include_filestore}")

            # Utiliser un dossier temporaire pour la création
            with tempfile.TemporaryDirectory() as temp_dir:
                # Créer le dump SQL
                temp_sql = os.path.join(temp_dir, f"{db_name}.sql")

                # Configuration des variables d'environnement
                env_vars = os.environ.copy()
                if db_config['password']:
                    env_vars['PGPASSWORD'] = str(db_config['password'])

                # Construire la commande pg_dump
                dump_cmd = [
                    'pg_dump',
                    '-h', db_config['host'],
                    '-p', db_config['port'],
                    '-U', db_config['user'],
                    '-d', db_name,
                    '-f', temp_sql,
                    '--no-owner',
                    '--no-acl',
                    '--verbose'
                ]

                _logger.info(f"Exécution de: {' '.join(dump_cmd)}")

                # Exécuter pg_dump
                try:
                    result = subprocess.run(
                        dump_cmd,
                        env=env_vars,
                        capture_output=True,
                        text=True,
                        timeout=300  # Timeout de 5 minutes
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr or result.stdout or "Erreur inconnue lors du dump"
                        _logger.error(f"Erreur pg_dump (code {result.returncode}): {error_msg}")

                        # Vérifier si c'est un problème d'authentification
                        if "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                            raise UserError(_(
                                "Erreur d'authentification PostgreSQL.\n"
                                "Vérifiez la configuration dans odoo.conf:\n"
                                "- db_user\n"
                                "- db_password\n"
                                "- db_host\n"
                                "- db_port"
                            ))
                        else:
                            raise UserError(_("Erreur pg_dump: %s") % error_msg)

                    _logger.info("✓ pg_dump exécuté avec succès")

                except subprocess.TimeoutExpired:
                    raise UserError(_("La sauvegarde a pris trop de temps (>5 minutes)"))
                except FileNotFoundError:
                    raise UserError(_(
                        "pg_dump n'est pas installé ou accessible.\n"
                        "Installez postgresql-client:\n"
                        "sudo apt-get install postgresql-client"
                    ))

                # Vérifier que le dump a été créé
                if not os.path.exists(temp_sql):
                    raise UserError(_("Le fichier de dump SQL n'a pas été créé"))

                sql_size = os.path.getsize(temp_sql) / (1024 * 1024)  # En MB
                _logger.info(f"✓ Dump SQL créé: {sql_size:.2f} MB")

                # Créer l'archive ZIP
                _logger.info(f"Création de l'archive ZIP: {backup_file}")
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Ajouter le dump SQL
                    zf.write(temp_sql, f"{db_name}.sql")
                    _logger.info("✓ SQL ajouté au ZIP")

                    # Ajouter le filestore si demandé
                    if self.include_filestore:
                        filestore_path = config.filestore(db_name)

                        if filestore_path and os.path.exists(filestore_path):
                            _logger.info(f"Ajout du filestore depuis: {filestore_path}")

                            file_count = 0
                            total_size = 0

                            for root, dirs, files in os.walk(filestore_path):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        # Chemin relatif dans l'archive
                                        arc_path = os.path.join(
                                            'filestore',
                                            os.path.relpath(file_path, filestore_path)
                                        )
                                        zf.write(file_path, arc_path)
                                        file_count += 1
                                        total_size += os.path.getsize(file_path)

                                        # Log de progression
                                        if file_count % 100 == 0:
                                            _logger.info(f"Progression: {file_count} fichiers ajoutés...")
                                    except Exception as e:
                                        _logger.warning(f"Impossible d'ajouter {file}: {e}")

                            filestore_size_mb = total_size / (1024 * 1024)
                            _logger.info(f"✓ Filestore ajouté: {file_count} fichiers ({filestore_size_mb:.2f} MB)")
                        else:
                            _logger.warning(f"Filestore non trouvé ou vide: {filestore_path}")

                _logger.info("✓ Archive ZIP créée avec succès")

            # Vérifier la taille finale
            if os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file) / (1024 * 1024)  # En MB
                _logger.info(f"=== BACKUP TERMINÉ ===")
                _logger.info(f"Fichier: {backup_file}")
                _logger.info(f"Taille: {file_size:.2f} MB")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'title': _('✅ Sauvegarde réussie'),
                        'message': _(
                            '📦 Backup créé avec succès!\n'
                            '📁 Fichier: %s\n'
                            '💾 Taille: %.2f MB'
                        ) % (backup_file, file_size),
                        'sticky': True,
                    }
                }
            else:
                raise UserError(_("Le fichier de backup n'a pas été créé"))

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Erreur inattendue backup serveur: {str(e)}", exc_info=True)
            raise UserError(_("Erreur inattendue: %s") % str(e))

    def _backup_to_download(self, db_name, filename):
        """Créer un backup pour téléchargement direct"""
        try:
            _logger.info(f"Création du backup pour téléchargement: {filename}")

            # Utiliser un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                temp_path = tmp_file.name

                # Utiliser l'API native Odoo pour créer le backup
                db.dump_db(db_name, tmp_file, 'zip')

                # Lire le fichier créé
                with open(temp_path, 'rb') as f:
                    backup_data = f.read()

                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_path)
                except:
                    pass

            # Encoder en base64
            backup_base64 = base64.b64encode(backup_data).decode('utf-8')

            # Créer l'attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': backup_base64,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/zip',
                'description': f'Database backup of {db_name}',
            })

            _logger.info(f"✅ Téléchargement prêt: {attachment.name}")

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except Exception as e:
            _logger.error(f"Erreur création download: {str(e)}", exc_info=True)
            raise UserError(_("Impossible de créer le téléchargement: %s") % str(e))
