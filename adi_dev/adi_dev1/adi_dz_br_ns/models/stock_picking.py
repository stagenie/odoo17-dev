# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'


class StockMove(models.Model):
    _inherit = 'stock.move'

    ns = fields.Text('N°(s) de Série(s)')
    obs = fields.Char('Observation')
    result = fields.Char('Résultat')
    driver = fields.Char('Chauffeur')
