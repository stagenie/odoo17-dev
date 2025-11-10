# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import re


class ResCompany(models.Model):
    _inherit = 'res.company'

    rc = fields.Char(
        string="N° RC",
        help="Numéro du registre de commerce",
    )

    nis = fields.Char(
        string="NIS",      
        help="Numéro d'Identification Statistique",
    )

    nif = fields.Char(
        string="NIF",        
        help="Numéro d’Identification Fiscal",
    )

    ai = fields.Char(
        string="AI",        
        help="Numéro d'article d'imposition",
    )

    forme_juridique = fields.Many2one(
        comodel_name='forme.juridique',
        string="Forme juridique"
    )

    capital_social = fields.Monetary(
        string="Capital social",
    )

   

   