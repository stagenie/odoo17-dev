# -*- coding: utf-8 -*-
import os
import html
import zipfile
from odoo import models, api


class ModuleContentPlusProcessing(models.Model):
    _inherit = 'module.content.plus'

    def _process_zip_file(self, zip_path):
        """Traite les fichiers ZIP avec support étendu"""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Supprimer cette ligne qui cause l'erreur :
            # self.zip_ref = zip_ref

            file_list = zip_ref.namelist()
            file_list.sort()

            # Organiser par répertoire
            dirs = {}
            for file_path in file_list:
                components = file_path.split('/')
                if len(components) > 1:
                    main_dir = components[0]
                    if main_dir not in dirs:
                        dirs[main_dir] = []
                    dirs[main_dir].append(file_path)

            # Construire le HTML
            html_result = '<div style="font-family: monospace;">'
            html_result += f'<h2 style="color: #0A5688;"># Module {self.name}</h2>'

            for dir_name, files in sorted(dirs.items()):
                html_result += f'<h3 style="color: #0A5688; margin-top: 20px;"># {dir_name}</h3>'

                # Grouper par type
                py_files = [f for f in files if f.endswith('.py') and '__pycache__' not in f]
                xml_files = [f for f in files if f.endswith('.xml')]
                js_files = [f for f in files if f.endswith('.js')]
                css_files = [f for f in files if f.endswith(('.css', '.scss', '.sass', '.less'))]
                json_files = [f for f in files if f.endswith('.json')]
                yaml_files = [f for f in files if f.endswith(('.yml', '.yaml'))]
                csv_files = [f for f in files if f.endswith('.csv')]
                po_files = [f for f in files if f.endswith(('.po', '.pot'))]
                doc_files = [f for f in files if f.endswith(('.rst', '.md', '.txt'))]

                # Traiter chaque type
                if py_files:
                    html_result += self._process_python_files(py_files, zip_ref)
                if xml_files:
                    html_result += self._process_xml_files(xml_files, zip_ref)
                if js_files:
                    html_result += self._process_javascript_files(js_files, zip_ref)
                if css_files:
                    html_result += self._process_style_files(css_files, zip_ref)
                if json_files:
                    html_result += self._process_json_files(json_files, zip_ref)
                if yaml_files:
                    html_result += self._process_yaml_files(yaml_files, zip_ref)
                if csv_files:
                    html_result += self._process_csv_files(csv_files, zip_ref)
                if po_files:
                    html_result += self._process_translation_files(po_files, zip_ref)
                if doc_files:
                    html_result += self._process_doc_files(doc_files, zip_ref)

            html_result += '</div>'
            return html_result

    def _process_python_files(self, py_files, zip_ref):
        """Traite les fichiers Python"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># Python Files</h4>'

        for file_path in py_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_xml_files(self, xml_files, zip_ref):
        """Traite les fichiers XML"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># XML Files</h4>'

        for file_path in xml_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_javascript_files(self, js_files, zip_ref):
        """Traite les fichiers JavaScript"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># JavaScript Files</h4>'

        for file_path in js_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_style_files(self, style_files, zip_ref):
        """Traite les fichiers CSS/SCSS/LESS"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># Style Files (CSS/SCSS/LESS)</h4>'

        for file_path in style_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_json_files(self, json_files, zip_ref):
        """Traite les fichiers JSON"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># JSON Files</h4>'

        for file_path in json_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_yaml_files(self, yaml_files, zip_ref):
        """Traite les fichiers YAML"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># YAML Files</h4>'

        for file_path in yaml_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_csv_files(self, csv_files, zip_ref):
        """Traite les fichiers CSV"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># CSV Files</h4>'

        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'

                    # Créer un tableau HTML
                    rows = content.strip().split('\n')
                    html_result += '<table style="border-collapse: collapse; width: 100%;">'

                    for i, row in enumerate(rows):
                        cells = row.split(',')
                        html_result += '<tr>'

                        for cell in cells:
                            if i == 0:
                                html_result += f"<th style=\"border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2;\">{cell.strip('\"')}</th>"
                            else:
                                html_result += f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{cell.strip('\"')}</td>"

                        html_result += '</tr>'

                    html_result += '</table>'
                    html_result += '</div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_translation_files(self, po_files, zip_ref):
        """Traite les fichiers PO/POT"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># Translation Files</h4>'

        for file_path in po_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result

    def _process_doc_files(self, doc_files, zip_ref):
        """Traite les fichiers de documentation"""
        html_result = '<div style="margin-left: 20px;">'
        html_result += '<h4 style="color: #407676;"># Documentation Files</h4>'

        for file_path in doc_files:
            file_name = os.path.basename(file_path)
            try:
                with zip_ref.open(file_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    html_result += f'<h5 style="color: #666;">{file_name}</h5>'
                    html_result += '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">'
                    html_result += '<pre style="margin: 0; white-space: pre-wrap;">'
                    html_result += html.escape(content)
                    html_result += '</pre></div>'
            except Exception as e:
                html_result += f'<p>Error: {str(e)}</p>'

        html_result += '</div>'
        return html_result
