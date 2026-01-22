from odoo import models, fields, api

class ProductMovementWizard(models.TransientModel):
    _name = 'product.movement.wizard'
    _description = 'Assistant Mouvements Produits'

    date_start = fields.Date(string='Date début')
    date_end = fields.Date(string='Date fin')
    category_ids = fields.Many2many('product.category', string='Catégories')
    product_ids = fields.Many2many('product.product', string='Produits')
    show_all = fields.Boolean(string='Afficher tous les produits', default=False)

    @api.onchange('show_all')
    def _onchange_show_all(self):
        if self.show_all:
            self.category_ids = False
            self.product_ids = False

    def action_generate_report(self):
        domain = []
        if not self.show_all:
            if self.category_ids:
                domain.append(('categ_id', 'in', self.category_ids.ids))
            if self.product_ids:
                domain.append(('id', 'in', self.product_ids.ids))

        products = self.env['product.product'].search(domain)
        data = {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'product_ids': products.ids,
        }
        return self.env.ref('adi_stock_moves_report.action_report_product_movements').report_action(self, data=data)