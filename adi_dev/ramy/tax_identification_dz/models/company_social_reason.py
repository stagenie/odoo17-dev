# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CompanySocialReason(models.Model):
    _name = 'company.social.reason'
    _description = 'Company social reason'

    name = fields.Char(string="Raison sociale")
