# -*- coding: utf-8 -*-

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.quant'

    user_id = fields.Many2one('res.users',
                              string="User",
                              default=lambda self: self.env.user, )

    allowed_location_ids = fields.Many2many('stock.location',
                                            compute='_compute_allowed_locations',
                                            )

    @api.depends('user_id')
    def _compute_allowed_locations(self):
        for record in self:
            user_warehouses = self.env.user.allowed_warehouse_ids
            record.allowed_location_ids = self.env['stock.location'].search(
                [
                    ('warehouse_id', 'in', user_warehouses.ids),
                    ('usage', '!=', 'view'),
                ])





