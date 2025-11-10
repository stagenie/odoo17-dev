# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResCurrency(models.Model):
    _inherit = 'res.currency'


    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'res_currency_id', string='Blillets')
    cashbox_lines_coin_ids = fields.One2many('account.cashbox.line', 'res_currency_coin_id', string='Pièces')
