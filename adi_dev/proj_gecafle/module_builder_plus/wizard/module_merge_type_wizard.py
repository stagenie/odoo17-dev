# -*- coding: utf-8 -*-
import base64
import zipfile
import io
from odoo import models, fields, api, _


class ModuleMergeTypeWizard(models.TransientModel):
    _name = 'module.merge.type.wizard'
    _description = 'Sélection des types de fichiers à fusionner'

    merge_wizard_id = fields.Many2one('module.merge.wizard', string='Wizard parent')
    module_ids = fields.Many2many('module.content.plus', string='Modules')

    # Types de fichiers à inclure
    include_python = fields.Boolean('Fichiers Python (.py)', default=True)
    include_xml = fields.Boolean('Fichiers XML (.xml)', default=True)
    include_js = fields.Boolean('Fichiers JavaScript (.js)', default=False)
    include_css = fields.Boolean('Fichiers CSS/SCSS', default=False)
    include_csv = fields.Boolean('Fichiers CSV', default=False)
    include_translation = fields.Boolean('Fichiers de traduction (.po)', default=False)

    def action_merge_selected_types(self):
        """Fusionne uniquement les types sélectionnés"""
        self.ensure_one()

        content_parts = []

        for module in self.module_ids:
            module_content = []

            # Extraire le contenu selon les types sélectionnés
            extracted_content = self._extract_content_by_type(module)

            if extracted_content:
                content_parts.append(f"\n{'=' * 80}\nMODULE: {module.name}\n{'=' * 80}\n")
                content_parts.append(extracted_content)

        # Créer le fichier final
        final_content = '\n'.join(content_parts)

        # Créer l'attachement et télécharger
        attachment = self.env['ir.attachment'].create({
            'name': f'merged_specific_{fields.Date.today()}.txt',
            'datas': base64.b64encode(final_content.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'text/plain',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _extract_content_by_type(self, module):
        """Extrait le contenu du module selon les types sélectionnés"""
        if not module.module_file:
            return ""

        content_sections = []
        file_content = base64.b64decode(module.module_file)

        try:
            with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_ref:
                file_list = zip_ref.namelist()

                # Filtrer et traiter les fichiers Python
                if self.include_python:
                    py_files = [f for f in file_list if f.endswith('.py') and '__pycache__' not in f]
                    if py_files:
                        content_sections.append("### PYTHON FILES ###\n")
                        for file_path in sorted(py_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

                # Filtrer et traiter les fichiers XML
                if self.include_xml:
                    xml_files = [f for f in file_list if f.endswith('.xml')]
                    if xml_files:
                        content_sections.append("\n### XML FILES ###\n")
                        for file_path in sorted(xml_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

                # Filtrer et traiter les fichiers JavaScript
                if self.include_js:
                    js_files = [f for f in file_list if f.endswith('.js')]
                    if js_files:
                        content_sections.append("\n### JAVASCRIPT FILES ###\n")
                        for file_path in sorted(js_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

                # Filtrer et traiter les fichiers CSS/SCSS
                if self.include_css:
                    css_files = [f for f in file_list if
                                 any(f.endswith(ext) for ext in ['.css', '.scss', '.sass', '.less'])]
                    if css_files:
                        content_sections.append("\n### STYLE FILES ###\n")
                        for file_path in sorted(css_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

                # Filtrer et traiter les fichiers CSV
                if self.include_csv:
                    csv_files = [f for f in file_list if f.endswith('.csv')]
                    if csv_files:
                        content_sections.append("\n### CSV FILES ###\n")
                        for file_path in sorted(csv_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

                # Filtrer et traiter les fichiers de traduction
                if self.include_translation:
                    po_files = [f for f in file_list if f.endswith(('.po', '.pot'))]
                    if po_files:
                        content_sections.append("\n### TRANSLATION FILES ###\n")
                        for file_path in sorted(po_files):
                            try:
                                with zip_ref.open(file_path) as f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    content_sections.append(f"# {file_path}")
                                    content_sections.append("=" * 60)
                                    content_sections.append(content)
                                    content_sections.append("\n")
                            except Exception as e:
                                content_sections.append(f"# Erreur lecture {file_path}: {str(e)}\n")

        except Exception as e:
            content_sections.append(f"Erreur traitement du module {module.name}: {str(e)}\n")

        return '\n'.join(content_sections)
