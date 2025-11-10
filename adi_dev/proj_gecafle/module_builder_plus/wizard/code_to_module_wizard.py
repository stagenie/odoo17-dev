# -*- coding: utf-8 -*-
import base64
import zipfile
import io
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CodeToModuleWizard(models.TransientModel):
    _name = 'code.to.module.wizard'
    _description = 'Générateur de module depuis code'

    name = fields.Char('Nom du module', required=True)
    module_code = fields.Text('Code du module', required=True,
                              help="Collez votre code ici avec les marqueurs de fichiers")
    generated_file = fields.Binary('Module généré', readonly=True)
    generated_filename = fields.Char('Nom du fichier généré')
    state = fields.Selection([
        ('input', 'Saisie du code'),
        ('done', 'Module généré')
    ], default='input')

    def generate_module(self):
        """Génère un module ZIP à partir du code fourni"""
        self.ensure_one()

        if not self.module_code:
            raise UserError(_("Veuillez entrer le code du module."))

        # Parser le code pour extraire les fichiers
        files_dict = self._parse_module_code(self.module_code)

        if not files_dict:
            raise UserError(
                _("Aucun fichier trouvé. Utilisez des marqueurs comme: # nom_fichier.py, ### fichier.xml, etc."))

        # Créer le fichier ZIP
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Ajouter chaque fichier au ZIP
            for file_path, content in files_dict.items():
                # Ajouter le nom du module comme répertoire racine
                full_path = f"{self.name}/{file_path}"
                zip_file.writestr(full_path, content)

            # Vérifier et générer les fichiers essentiels si absents
            self._ensure_essential_files(zip_file, files_dict)

        # Encoder le ZIP en base64
        zip_buffer.seek(0)
        self.generated_file = base64.b64encode(zip_buffer.read())
        self.generated_filename = f"{self.name}.zip"
        self.state = 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _parse_module_code(self, code):
        """Parse le code pour extraire les différents fichiers de manière intelligente"""
        files_dict = {}
        current_file = None
        current_content = []

        lines = code.split('\n')

        for line in lines:
            # Détection intelligente des marqueurs de fichier
            file_info = self._detect_file_marker(line)

            if file_info:
                # Sauvegarder le fichier précédent
                if current_file and current_content:
                    # Nettoyer le contenu avant de sauvegarder
                    content = '\n'.join(current_content).strip()
                    if content:  # Ne sauvegarder que si le contenu n'est pas vide
                        files_dict[current_file] = content

                # Nouveau fichier détecté
                current_file = file_info['filename']
                current_content = []
            else:
                # Ajouter la ligne au contenu actuel
                if current_file is not None:
                    current_content.append(line)

        # Sauvegarder le dernier fichier
        if current_file and current_content:
            content = '\n'.join(current_content).strip()
            if content:
                files_dict[current_file] = content

        # Organiser les fichiers selon leur type
        return self._organize_files_structure(files_dict)

    def _detect_file_marker(self, line):
        """Détecte intelligemment si une ligne est un marqueur de fichier"""
        # Liste des patterns de marqueurs possibles
        patterns = [
            # Pattern principal : ### fichier.ext, ## fichier.ext, # fichier.ext
            r'^#{1,5}\s*(?:fichier\s*:)?\s*([a-zA-Z0-9_/\-\.]+)(?:\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb))?',
            # Pattern avec commentaires style programmation : // fichier.ext, -- fichier.ext
            r'^(?://|--)\s*(?:fichier\s*:)?\s*([a-zA-Z0-9_/\-\.]+)(?:\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb))?',
            # Pattern avec === ou --- : === fichier.ext ===
            r'^[=\-]{3,}\s*([a-zA-Z0-9_/\-\.]+)(?:\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb))?\s*[=\-]{0,}',
            # Pattern avec crochets : [fichier.ext]
            r'^\[([a-zA-Z0-9_/\-\.]+)(?:\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb))?\]',
            # Pattern avec >>> : >>> fichier.ext
            r'^>>>\s*([a-zA-Z0-9_/\-\.]+)(?:\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb))?',
            # Pattern simple avec extension obligatoire
            r'^([a-zA-Z0-9_/\-]+)\.(py|xml|csv|js|css|scss|yml|yaml|json|po|pot|rst|md|txt|html|qweb)\s*$',
        ]

        for pattern in patterns:
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                # Extraire le nom de fichier et l'extension
                groups = match.groups()
                filename = groups[0]
                extension = groups[1] if len(groups) > 1 and groups[1] else None

                # Si pas d'extension, essayer de la deviner
                if not extension:
                    extension = self._guess_file_extension(filename, line)

                # Construire le nom de fichier complet
                if extension and not filename.endswith(f'.{extension}'):
                    filename = f"{filename}.{extension}"

                # Normaliser le nom de fichier
                filename = self._normalize_filename(filename)

                return {
                    'filename': filename,
                    'extension': extension
                }

        return None

    def _guess_file_extension(self, filename, context_line):
        """Devine l'extension d'un fichier basé sur son nom et son contexte"""
        filename_lower = filename.lower()

        # Patterns de noms de fichiers courants
        common_patterns = {
            'py': ['model', 'wizard', 'controller', 'test', '__init__', '__manifest__',
                   'models', 'wizards', 'controllers', 'tests', 'views'],
            'xml': ['view', 'data', 'security', 'report', 'template', 'menu', 'action',
                    'views', 'templates', 'reports', 'actions'],
            'js': ['widget', 'script', 'app', 'main', 'controller', 'component'],
            'css': ['style', 'theme', 'custom', 'main'],
            'scss': ['style', 'theme', 'variables', 'mixins'],
            'csv': ['ir.model.access', 'security', 'data'],
            'yml': ['docker', 'config', 'travis'],
            'yaml': ['docker-compose', 'config'],
            'json': ['package', 'manifest', 'config'],
            'po': ['i18n', 'translation', 'locale'],
            'pot': ['i18n', 'translation'],
            'rst': ['readme', 'changelog', 'doc', 'index'],
            'md': ['readme', 'changelog', 'contributing'],
            'txt': ['requirements', 'readme', 'notes'],
            'html': ['index', 'template', 'email'],
            'qweb': ['template', 'report']
        }

        # Vérifier si le nom correspond à un pattern connu
        for ext, patterns in common_patterns.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return ext

        # Vérifications spécifiques
        if 'manifest' in filename_lower or filename == '__manifest__':
            return 'py'
        if filename == '__init__':
            return 'py'
        if 'ir.model.access' in filename:
            return 'csv'
        if filename_lower.startswith('test_'):
            return 'py'
        if filename_lower.endswith('_view') or filename_lower.endswith('_views'):
            return 'xml'
        if filename_lower.endswith('_wizard'):
            return 'py'
        if filename_lower.endswith('_report'):
            return 'xml'

        # Par défaut, retourner py pour les fichiers sans extension claire
        return 'py'

    def _normalize_filename(self, filename):
        """Normalise le nom de fichier"""
        # Remplacer les espaces par des underscores
        filename = filename.replace(' ', '_')

        # Enlever les caractères spéciaux sauf / - _ .
        filename = re.sub(r'[^a-zA-Z0-9/_\-\.]', '', filename)

        # Éviter les doubles slashes
        filename = re.sub(r'/+', '/', filename)

        # Enlever les slashes au début et à la fin
        filename = filename.strip('/')

        return filename

    def _organize_files_structure(self, files_dict):
        """Organise les fichiers selon la structure standard Odoo"""
        organized_files = {}

        for file_path, content in files_dict.items():
            # Si le fichier a déjà un chemin, le garder
            if '/' in file_path:
                organized_files[file_path] = content
                continue

            # Sinon, déterminer le bon répertoire selon le type
            if file_path.endswith('.py'):
                if file_path in ['__init__.py', '__manifest__.py']:
                    organized_files[file_path] = content
                elif 'wizard' in file_path:
                    organized_files[f'wizard/{file_path}'] = content
                elif 'controller' in file_path:
                    organized_files[f'controllers/{file_path}'] = content
                elif 'test' in file_path:
                    organized_files[f'tests/{file_path}'] = content
                else:
                    organized_files[f'models/{file_path}'] = content

            elif file_path.endswith('.xml'):
                if 'security' in file_path:
                    organized_files[f'security/{file_path}'] = content
                elif 'data' in file_path:
                    organized_files[f'data/{file_path}'] = content
                elif 'report' in file_path:
                    organized_files[f'report/{file_path}'] = content
                elif 'wizard' in file_path:
                    organized_files[f'wizard/{file_path}'] = content
                else:
                    organized_files[f'views/{file_path}'] = content

            elif file_path.endswith('.csv'):
                if 'ir.model.access' in file_path:
                    organized_files[f'security/{file_path}'] = content
                else:
                    organized_files[f'data/{file_path}'] = content

            elif file_path.endswith('.js'):
                organized_files[f'static/src/js/{file_path}'] = content

            elif file_path.endswith(('.css', '.scss', '.less')):
                organized_files[f'static/src/css/{file_path}'] = content

            elif file_path.endswith(('.po', '.pot')):
                lang = 'fr' if 'fr' in file_path else 'en'
                organized_files[f'i18n/{file_path}'] = content

            elif file_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
                if 'icon' in file_path.lower():
                    organized_files[f'static/description/{file_path}'] = content
                else:
                    organized_files[f'static/src/img/{file_path}'] = content

            elif file_path.endswith(('.yml', '.yaml')):
                organized_files[f'{file_path}'] = content

            elif file_path.endswith('.json'):
                if 'package' in file_path:
                    organized_files[file_path] = content
                else:
                    organized_files[f'static/src/{file_path}'] = content

            else:
                # Fichiers non reconnus à la racine
                organized_files[file_path] = content

        return organized_files

    def _ensure_essential_files(self, zip_file, existing_files):
        """S'assure que les fichiers essentiels sont présents"""
        module_name = self.name

        # Vérifier __init__.py à la racine
        init_exists = any('__init__.py' in path for path in existing_files)
        if not init_exists:
            # Déterminer quels imports inclure
            imports = []
            if any('models/' in path for path in existing_files):
                imports.append('from . import models')
            if any('wizard/' in path for path in existing_files):
                imports.append('from . import wizard')
            if any('controllers/' in path for path in existing_files):
                imports.append('from . import controllers')

            init_content = "# -*- coding: utf-8 -*-\n" + '\n'.join(imports) + '\n'
            zip_file.writestr(f"{module_name}/__init__.py", init_content)

        # Vérifier __manifest__.py
        manifest_exists = any('__manifest__.py' in path for path in existing_files)
        if not manifest_exists:
            manifest_content = self._generate_manifest(existing_files)
            zip_file.writestr(f"{module_name}/__manifest__.py", manifest_content)

        # Vérifier les __init__.py dans les sous-dossiers
        subdirs = set()
        for path in existing_files:
            if '/' in path:
                subdir = path.split('/')[0]
                subdirs.add(subdir)

        for subdir in subdirs:
            init_path = f"{subdir}/__init__.py"
            if not any(init_path in path for path in existing_files):
                # Créer un __init__.py pour le sous-dossier
                if subdir == 'models':
                    # Importer tous les fichiers Python du dossier models
                    model_files = [f for f in existing_files if
                                   f.startswith('models/') and f.endswith('.py') and '__init__' not in f]
                    imports = []
                    for model_file in model_files:
                        module_name_import = model_file.replace('models/', '').replace('.py', '')
                        imports.append(f'from . import {module_name_import}')
                    init_content = "# -*- coding: utf-8 -*-\n" + '\n'.join(imports) + '\n'
                else:
                    init_content = "# -*- coding: utf-8 -*-\n"

                zip_file.writestr(f"{module_name}/{init_path}", init_content)

    def _generate_manifest(self, existing_files=None):
        """Génère un fichier __manifest__.py intelligent basé sur les fichiers présents"""
        # Analyser les fichiers pour déterminer les dépendances et data files
        data_files = []
        depends = ['base']

        if existing_files:
            # Ajouter les fichiers de sécurité
            security_files = [f for f in existing_files if f.startswith('security/') and f.endswith('.csv')]
            data_files.extend(security_files)

            # Ajouter les vues XML
            view_files = [f for f in existing_files if f.endswith('.xml') and ('view' in f or f.startswith('views/'))]
            data_files.extend(sorted(view_files))

            # Ajouter les wizards
            wizard_files = [f for f in existing_files if f.endswith('.xml') and 'wizard' in f]
            data_files.extend(wizard_files)

            # Ajouter les données
            data_xml_files = [f for f in existing_files if f.endswith('.xml') and 'data' in f]
            data_files.extend(data_xml_files)

            # Ajouter les rapports
            report_files = [f for f in existing_files if f.endswith('.xml') and 'report' in f]
            data_files.extend(report_files)

            # Détecter les dépendances potentielles
            all_content = ' '.join(existing_files.keys())
            if 'sale' in all_content or 'order' in all_content:
                depends.append('sale')
            if 'purchase' in all_content:
                depends.append('purchase')
            if 'stock' in all_content or 'inventory' in all_content:
                depends.append('stock')
            if 'account' in all_content or 'invoice' in all_content:
                depends.append('account')
            if 'hr' in all_content or 'employee' in all_content:
                depends.append('hr')
            if 'website' in all_content:
                depends.append('website')

        # Formatter la liste des data files
        data_files_str = ''
        if data_files:
            data_files_str = '\n        '.join([f"'{f}'," for f in data_files])

        return f"""# -*- coding: utf-8 -*-
{{
    'name': '{self.name}',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Module généré automatiquement',
    'description': '''
        Module créé avec Module Builder Plus
        ====================================

        Ce module a été généré automatiquement par Module Builder Plus.
    ''',
    'author': 'Module Builder Plus',
    'depends': {depends},
    'data': [
        {data_files_str}
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}}
"""

    def download_module(self):
        """Télécharge le module généré"""
        self.ensure_one()

        if not self.generated_file:
            raise UserError(_("Aucun module généré."))

        # Créer une pièce jointe
        attachment = self.env['ir.attachment'].create({
            'name': self.generated_filename,
            'datas': self.generated_file,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
