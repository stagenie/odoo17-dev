from odoo import models, fields, api
from datetime import datetime


class PalletMovementWizard(models.TransientModel):
    _name = 'pallet.movement.wizard'
    _description = 'Assistant Mouvements Palettes'

    date_start = fields.Date(string='Date début')
    date_end = fields.Date(string='Date fin')
    product_template_ids = fields.Many2many(
        'product.template',
        string='Modèles de Palettes',
        domain=[('is_palet', '=', True)]
    )
    product_variant_ids = fields.Many2many(
        'product.product',
        string='Variantes de Palettes',
        domain=[('product_tmpl_id.is_palet', '=', True)]
    )
    include_all_variants = fields.Boolean(
        string='Inclure toutes les variantes',
        default=True
    )

    @api.onchange('product_template_ids', 'include_all_variants')
    def _onchange_products(self):
        if self.include_all_variants:
            domain = [('product_tmpl_id', 'in', self.product_template_ids.ids)]
            self.product_variant_ids = self.env['product.product'].search(domain)
        else:
            self.product_variant_ids = False

    def action_generate_report(self):
        data = {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'product_variant_ids': self.product_variant_ids.ids,
        }
        return self.env.ref('dsi_stock_moves_report.action_report_pallet_movements').report_action(self, data=data)