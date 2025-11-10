from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    composition_ids = fields.One2many(
        string="Localités",
        comodel_name="res.country.state.composition",
        inverse_name="state_id",
    )

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

