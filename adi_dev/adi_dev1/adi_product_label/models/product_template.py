from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_print_label(self):
        products = self.mapped('product_variant_ids')
        return self.env.ref('adi_product_label.action_report_product_label').report_action(products)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_barcode_base64(self):
        if self.barcode:
            try:
                barcode_bytes = self.env['ir.actions.report'].barcode('Code128', self.barcode, width=250, height=35, humanreadable=1)
                import base64
                return base64.b64encode(barcode_bytes).decode()
            except Exception:
                return False
        return False
