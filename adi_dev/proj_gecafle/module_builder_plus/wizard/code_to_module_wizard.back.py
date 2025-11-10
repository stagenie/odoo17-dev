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
            raise UserError(_("Aucun fichier trouvé. Utilisez le format: # fichier: nom_fichier.py"))

        # Créer le fichier ZIP
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Ajouter chaque fichier au ZIP
            for file_path, content in files_dict.items():
                # Ajouter le nom du module comme répertoire racine
                full_path = f"{self.name}/{file_path}"
                zip_file.writestr(full_path, content)

            # Générer un __init__.py minimal si absent
            init_path = f"{self.name}/__init__.py"
            if init_path not in [f"{self.name}/{fp}" for fp in files_dict.keys()]:
                zip_file.writestr(init_path, "# -*- coding: utf-8 -*-\nfrom . import models\n")

            # Générer un __manifest__.py minimal si absent
            manifest_path = f"{self.name}/__manifest__.py"
            if manifest_path not in [f"{self.name}/{fp}" for fp in files_dict.keys()]:
                manifest_content = self._generate_manifest()
                zip_file.writestr(manifest_path, manifest_content)

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
        """Parse le code pour extraire les différents fichiers"""
        files_dict = {}
        current_file = None
        current_content = []

        lines = code.split('\n')

        for line in lines:
            # Détecter les marqueurs de fichier
            file_match = re.match(
                r'#\s*(fichier\s*:)?\s*([a-zA-Z0-9_/\-\.]+\.(py|xml|csv|js|css|yml|yaml|json|po|pot|rst|md|txt|html|qweb))',
                line, re.IGNORECASE)

            if file_match:
                # Sauvegarder le fichier précédent
                if current_file and current_content:
                    files_dict[current_file] = '\n'.join(current_content)

                # Nouveau fichier
                current_file = file_match.group(2).strip()
                current_content = []
            else:
                # Ajouter la ligne au contenu actuel
                if current_file is not None:
                    current_content.append(line)

        # Sauvegarder le dernier fichier
        if current_file and current_content:
            files_dict[current_file] = '\n'.join(current_content)

        # Créer la structure de répertoires appropriée
        organized_files = {}
        for file_path, content in files_dict.items():
            # Nettoyer le contenu
            content = content.strip()

            # Déterminer le bon chemin selon le type de fichier
            if file_path.endswith('.py') and '/' not in file_path:
                if file_path == '__init__.py' or file_path == '__manifest__.py':
                    organized_files[file_path] = content
                else:
                    organized_files[f'models/{file_path}'] = content
            elif file_path.endswith('.xml') and '/' not in file_path:
                organized_files[f'views/{file_path}'] = content
            elif file_path.endswith('.csv') and '/' not in file_path:
                organized_files[f'security/{file_path}'] = content
            elif file_path.endswith('.js') and '/' not in file_path:
                organized_files[f'static/src/js/{file_path}'] = content
            elif file_path.endswith(('.css', '.scss')) and '/' not in file_path:
                organized_files[f'static/src/css/{file_path}'] = content
            else:
                organized_files[file_path] = content

        return organized_files

    def _generate_manifest(self):
        """Génère un fichier __manifest__.py basique"""
        return f"""# -*- coding: utf-8 -*-
{{
    'name': '{self.name}',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Module généré automatiquement',
    'description': '''
        Module créé avec Module Builder Plus
    ''',
    'author': 'Module Builder Plus',
    'depends': ['base'],
    'data': [
        # Ajouter vos fichiers XML ici
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
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
