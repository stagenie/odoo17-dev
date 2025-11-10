# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'


class StockMove(models.Model):
    _inherit = 'stock.move'

    obs = fields.Char('Observation')
