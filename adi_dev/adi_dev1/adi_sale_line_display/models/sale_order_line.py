# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_number = fields.Integer(
        string='N°',
        compute='_compute_line_number',
        store=False,
    )
    product_name_only = fields.Char(
        string='Nom du produit',
        compute='_compute_product_name_only',
        store=True,
    )

    @api.depends('sequence', 'order_id.order_line')
    def _compute_line_number(self):
        for order in self.mapped('order_id'):
            num = 1
            for line in order.order_line:
                if line.display_type:
                    line.line_number = 0
                else:
                    line.line_number = num
                    num += 1

    @api.depends('product_id', 'product_id.name')
    def _compute_product_name_only(self):
        for line in self:
            if line.product_id:
                line.product_name_only = line.product_id.name
            else:
                line.product_name_only = False
