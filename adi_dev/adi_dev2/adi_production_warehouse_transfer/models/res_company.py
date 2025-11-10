# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    raw_material_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt Matières Premières',
        help='Entrepôt par défaut pour stocker les matières premières'
    )

    production_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt Production',
        help='Entrepôt par défaut pour la production'
    )

    finished_goods_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt Produits Finis',
        help='Entrepôt par défaut pour stocker les produits finis'
    )

    auto_validate_internal_transfers = fields.Boolean(
        string='Validation automatique des transferts internes',
        default=False,
        help='Si activé, les transferts entre entrepôts seront validés automatiquement si le stock est disponible'
    )
