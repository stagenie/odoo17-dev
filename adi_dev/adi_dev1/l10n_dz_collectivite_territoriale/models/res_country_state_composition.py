from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCountryStateComposition(models.Model):
    _name = 'res.country.state.composition'

    state_id = fields.Many2one(
        string="Wilaya",
        comodel_name="res.country.state",
    )

    name = fields.Char(
        string="Localité",
    )

    code = fields.Char(
        string='Code',
    )

    address = fields.Char(
        string='Adresse',
    )

    commune = fields.Char(
        string='Commune',
    )

    daira = fields.Char(
        string='Daira',
    )
