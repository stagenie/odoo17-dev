# -*- coding: utf-8 -*-
import base64
import zipfile
import io
from odoo import models, api, _
from odoo.exceptions import UserError
import html2text
import pdfkit


class ModuleContentPlusExport(models.Model):
    _inherit = 'module.content.plus'

    def export_python_files(self):
        """Exporte uniquement les fichiers Python"""
        return self._export_specific_files('.py', 'python_files.txt')

    def export_xml_files(self):
        """Exporte uniquement les fichiers XML"""
        return self._export_specific_files('.xml', 'xml_files.txt')

    def export_js_files(self):
        """Exporte uniquement les fichiers JavaScript"""
        return self._export_specific_files('.js', 'javascript_files.txt')

    def export_css_files(self):
        """Exporte uniquement les fichiers CSS/SCSS"""
        return self._export_specific_files(['.css', '.scss', '.sass', '.less'], 'style_files.txt')

    def export_translation_files(self):
        """Exporte les fichiers de traduction"""
        return self._export_specific_files(['.po', '.pot'], 'translation_files.txt')

    def export_data_files(self):
        """Exporte les fichiers de données (CSV, JSON, YAML)"""
        return self._export_specific_files(['.csv', '.json', '.yml', '.yaml'], 'data_files.txt')

    def _export_specific_files(self, extensions, filename):
        """Méthode générique pour exporter des fichiers spécifiques"""
        self.ensure_one()
        if not self.module_file:
            raise UserError(_("Aucun fichier module chargé."))

        # Décoder le fichier
        file_content = base64.b64decode(self.module_file)
        output_content = []

        with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_ref:
            file_list = zip_ref.namelist()

            # Filtrer les fichiers selon l'extension
            if isinstance(extensions, str):
                filtered_files = [f for f in file_list if f.endswith(extensions)]
            else:
                filtered_files = [f for f in file_list if any(f.endswith(ext) for ext in extensions)]

            # Extraire le contenu
            for file_path in sorted(filtered_files):
                if '__pycache__' not in file_path and not file_path.endswith('.pyc'):
                    try:
                        with zip_ref.open(file_path) as f:
                            content = f.read().decode('utf-8', errors='replace')
                            output_content.append(f"# {file_path}")
                            output_content.append("=" * 80)
                            output_content.append(content)
                            output_content.append("\n\n")
                    except Exception as e:
                        output_content.append(f"# Error reading {file_path}: {str(e)}\n\n")

        # Créer le fichier de sortie
        final_content = '\n'.join(output_content)

        # Créer une pièce jointe
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(final_content.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


    def convert_html_to_txt(self):
        """Convertit le contenu HTML en fichier TXT et le propose en téléchargement"""
        self.ensure_one()
        if not self.processed_content:
            return

        # Conversion du HTML en texte brut
        h = html2text.HTML2Text()
        h.ignore_links = False
        text_content = h.handle(self.processed_content)

        # Création d'une pièce jointe à télécharger
        attachment_value = {
            'name': 'contenu.txt',
            'datas': base64.b64encode(text_content.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        }
        attachment_id = self.env['ir.attachment'].create(attachment_value)

        # Retourne une action pour télécharger le fichier
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment_id.id,
            'target': 'self',
        }

    def convert_html_to_pdf(self):
        """Convertit le contenu HTML en fichier PDF et le propose en téléchargement"""
        self.ensure_one()
        if not self.processed_content:
            return

        # Conversion du HTML en PDF
        pdf_content = pdfkit.from_string(self.processed_content, False)

        # Création d'une pièce jointe à télécharger
        attachment_value = {
            'name': 'contenu.pdf',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        }
        attachment_id = self.env['ir.attachment'].create(attachment_value)

        # Retourne une action pour télécharger le fichier
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment_id.id,
            'target': 'self',
        }

