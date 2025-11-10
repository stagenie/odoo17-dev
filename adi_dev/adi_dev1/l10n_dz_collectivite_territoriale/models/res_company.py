from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    composition_id = fields.Many2one(
        string="Localité",
        comodel_name="res.country.state.composition",
    )

    @api.onchange('composition_id')
    def onchange_composition_id(self):
        for record in self:
            if record.composition_id:
                code = record.composition_id.code
                # recuperer le code de base de la wilaya si la localité n'as pas de code
                if not code and record.state_id.composition_ids:
                    code = record.state_id.composition_ids[0].code

                record.zip = code

    @api.onchange('state_id')
    def _onchange_state(self):
        res = super(ResCompany, self)._onchange_state()

        for record in self:
            if not record.state_id:
                record.zip = record.composition_id = False

        return res