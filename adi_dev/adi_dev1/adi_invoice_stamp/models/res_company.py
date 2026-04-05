from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    stamp_image = fields.Binary(string="Cachet / Signature", attachment=True)
    stamp_show = fields.Boolean(string="Afficher le cachet sur les factures", default=False)
    stamp_size_mode = fields.Selection([
        ('small', 'Petit (3×3 cm)'),
        ('medium', 'Standard (4×4 cm)'),
        ('large', 'Grand (5×5 cm)'),
        ('custom', 'Personnalisé'),
    ], string="Taille du cachet", default='medium')
    stamp_width = fields.Float(string="Largeur (cm)", default=4.0)
    stamp_height = fields.Float(string="Hauteur (cm)", default=4.0)

    def _get_stamp_dimensions(self):
        """Return stamp width and height in cm based on size mode."""
        self.ensure_one()
        sizes = {
            'small': (3.0, 3.0),
            'medium': (4.0, 4.0),
            'large': (5.0, 5.0),
        }
        if self.stamp_size_mode == 'custom':
            return (self.stamp_width or 4.0, self.stamp_height or 4.0)
        return sizes.get(self.stamp_size_mode, (4.0, 4.0))
