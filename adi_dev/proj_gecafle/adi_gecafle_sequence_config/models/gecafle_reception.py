from odoo import models, api


class GecafleReception(models.Model):
    _inherit = 'gecafle.reception'

    @api.model
    def create(self, vals):
        """Surcharge pour utiliser le format de séquence configuré."""
        if not vals.get('name') or vals.get('name') == '/':
            company = self.env.company
            # Utiliser la nouvelle méthode avec format configurable
            vals['name'] = company.get_next_reception_number()
        return super().create(vals)
