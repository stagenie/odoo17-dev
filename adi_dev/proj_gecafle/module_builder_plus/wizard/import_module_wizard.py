# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ImportModuleWizard(models.TransientModel):
    _name = 'import.module.wizard.plus'
    _description = 'Assistant d\'importation de module Plus'

    module_file = fields.Binary('Fichier Module (ZIP/RAR)', required=True)
    file_name = fields.Char('Nom du fichier')

    def action_import(self):
        """Importe le fichier dans le module content"""
        self.ensure_one()
        module_content = self.env['module.content.plus'].browse(self._context.get('active_id'))
        module_content.write({
            'module_file': self.module_file,
            'file_name': self.file_name,
        })
        module_content.import_module_file()
        return {'type': 'ir.actions.act_window_close'}
