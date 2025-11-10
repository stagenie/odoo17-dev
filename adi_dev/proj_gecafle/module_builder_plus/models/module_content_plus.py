# -*- coding: utf-8 -*-
import base64
import zipfile
import tempfile
import os
import io
from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import rarfile

    RAR_SUPPORT = True
except ImportError:
    RAR_SUPPORT = False


class ModuleContentPlus(models.Model):
    _name = 'module.content.plus'
    _description = 'Module Content Plus - Advanced Builder'
    _rec_name = 'name'

    name = fields.Char('Nom du module', required=True)
    description = fields.Text('Description')
    module_file = fields.Binary('Fichier du module (ZIP/RAR)')
    file_name = fields.Char('Nom du fichier')
    processed_content = fields.Html('Contenu traité', readonly=True)

    # Stockage temporaire des différents types de fichiers
    python_files_content = fields.Text('Contenu Python', compute='_compute_file_contents', store=True)
    xml_files_content = fields.Text('Contenu XML', compute='_compute_file_contents', store=True)
    js_files_content = fields.Text('Contenu JS', compute='_compute_file_contents', store=True)
    css_files_content = fields.Text('Contenu CSS', compute='_compute_file_contents', store=True)

    @api.depends('processed_content')
    def _compute_file_contents(self):
        """Sépare le contenu par type de fichier pour l'export"""
        for record in self:
            record.python_files_content = ''
            record.xml_files_content = ''
            record.js_files_content = ''
            record.css_files_content = ''

    def import_module_file(self):
        """Importe et traite le fichier module"""
        self.ensure_one()
        if not self.module_file:
            raise UserError(_("Veuillez charger un fichier module."))

        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(base64.b64decode(self.module_file))
            temp_path = temp_file.name

        try:
            if self.file_name.endswith('.zip'):
                content = self._process_zip_file(temp_path)
                self.processed_content = content
            elif self.file_name.endswith('.rar') and RAR_SUPPORT:
                content = self._process_rar_file(temp_path)
                self.processed_content = content
            else:
                if self.file_name.endswith('.rar') and not RAR_SUPPORT:
                    raise UserError(_("Le support RAR nécessite l'installation de 'rarfile'."))
                else:
                    raise UserError(_("Format non supporté. Utilisez ZIP ou RAR."))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        return True

    def _process_rar_file(self, rar_path):
        """Traite les fichiers RAR si rarfile est installé"""
        if not RAR_SUPPORT:
            raise UserError(_("Le support RAR nécessite l'installation de 'rarfile'."))

        with rarfile.RarFile(rar_path, 'r') as rar_ref:
            with tempfile.TemporaryDirectory() as temp_dir:
                rar_ref.extractall(temp_dir)

                # Créer un ZIP temporaire
                zip_path = os.path.join(temp_dir, 'temp.zip')
                with zipfile.ZipFile(zip_path, 'w') as zip_ref:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file != 'temp.zip':
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, temp_dir)
                                zip_ref.write(file_path, arcname)

                return self._process_zip_file(zip_path)
