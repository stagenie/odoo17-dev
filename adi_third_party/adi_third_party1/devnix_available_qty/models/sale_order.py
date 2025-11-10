from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_qty = fields.Float(string="Qté Disponible", compute='compute_available_qty')

    @api.depends('product_id')
    def compute_available_qty(self):
        for line in self:
            available_quantity = self.env['stock.quant']._get_available_quantity(line.product_id,
                                                                                 line.warehouse_id.lot_stock_id,
                                                                                 allow_negative=True)
            line.available_qty = available_quantity
