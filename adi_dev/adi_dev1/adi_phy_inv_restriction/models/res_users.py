from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse', string='Allowed Warehouse',
        help='Allowed Warehouse for user.')


    allowed_location_ids = fields.Many2many(
        'stock.location',
        compute='_compute_allowed_locations',
        string="Allowed Locations"
    )

    @api.depends('allowed_warehouse_ids')
    def _compute_allowed_locations(self):
        for user in self:
            if user.allowed_warehouse_ids:
                # Recherche des emplacements liés aux entrepôts autorisés
                user.allowed_location_ids = self.env['stock.location'].search(
                    [
                        ('warehouse_id', 'in', user.allowed_warehouse_ids.ids),
                        ('usage', '!=', 'view'),  # Exclusion des locations de type "view"
                    ]
                )
            else:
                user.allowed_location_ids = False
