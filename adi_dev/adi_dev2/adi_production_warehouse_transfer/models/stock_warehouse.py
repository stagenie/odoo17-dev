# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    warehouse_type = fields.Selection([
        ('raw_material', 'Matières Premières'),
        ('production', 'Production'),
        ('finished_goods', 'Produits Finis'),
        ('other', 'Autre')
    ], string='Type d\'entrepôt', default='other')

    auto_transfer_to_production = fields.Boolean(
        string='Transfert auto vers production',
        help='Génère automatiquement des transferts vers l\'entrepôt de production'
    )
