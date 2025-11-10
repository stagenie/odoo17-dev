from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_amount_to_text_dz(self):
        return self.currency_id.amount_to_text_dz(self.amount_total)
