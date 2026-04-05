from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stamp_image = fields.Binary(
        related='company_id.stamp_image', readonly=False,
        string="Cachet / Signature",
    )
    stamp_show = fields.Boolean(
        related='company_id.stamp_show', readonly=False,
        string="Afficher le cachet sur les factures",
    )
    stamp_size_mode = fields.Selection(
        related='company_id.stamp_size_mode', readonly=False,
        string="Taille du cachet",
    )
    stamp_width = fields.Float(
        related='company_id.stamp_width', readonly=False,
        string="Largeur (cm)",
    )
    stamp_height = fields.Float(
        related='company_id.stamp_height', readonly=False,
        string="Hauteur (cm)",
    )
