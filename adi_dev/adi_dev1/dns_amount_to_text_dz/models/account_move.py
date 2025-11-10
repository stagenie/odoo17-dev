from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_amount_to_text_dz(self):
        return self.currency_id.amount_to_text_dz(self.amount_total)
