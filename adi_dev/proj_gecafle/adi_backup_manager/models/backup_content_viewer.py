# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BackupContentViewer(models.TransientModel):
    """Viewer pour afficher le contenu des archives"""
    _name = 'backup.content.viewer'
    _description = 'Visualiseur de contenu backup'

    file_id = fields.Many2one(
        'backup.file',
        string='Fichier',
        readonly=True
    )

    content_text = fields.Text(
        string='Contenu',
        readonly=True
    )
