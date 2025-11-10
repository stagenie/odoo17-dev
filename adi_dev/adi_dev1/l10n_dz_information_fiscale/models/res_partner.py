# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import re



class ResPartner(models.Model):
    _inherit = 'res.partner'

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

    