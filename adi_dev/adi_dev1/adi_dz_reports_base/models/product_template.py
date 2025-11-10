# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductPro(models.Model):
    _inherit = "product.template"
    # L'ajout du champ PArt Number au Produit 
    
    partnumber = fields.Char("Part Number")

