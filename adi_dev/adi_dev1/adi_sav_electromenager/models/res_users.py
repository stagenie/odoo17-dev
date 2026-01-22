# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    sav_sales_point_id = fields.Many2one(
        'res.partner',
        string='Point de Vente SAV',
        domain="[('is_sales_point', '=', True)]",
        help='Point de vente assigné à cet utilisateur pour le module SAV',
    )
