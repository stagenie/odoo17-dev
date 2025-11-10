from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    region_id = fields.Many2one('res.country.state',
                                string="Région par défaut")
