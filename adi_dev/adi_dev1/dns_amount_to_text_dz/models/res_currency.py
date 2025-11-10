# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text_dz(self, montant):
        currency_id = self or self.env.ref('base.DZD')
        res = currency_id.amount_to_text(montant)
        if round(montant % 1, 2) == 0.0:
            res += " et zéro centime"
        if montant > 1.0:
            res = res.replace('Dinar', 'Dinars')
        return res.lower().capitalize()
