# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FundMotifFamily(models.Model):
    _name = 'fund.motif.family'
    _description = 'Famille du motif de la caisse'
    _order = "create_date desc"

    name = fields.Char(string='Famille motif', required=True)
