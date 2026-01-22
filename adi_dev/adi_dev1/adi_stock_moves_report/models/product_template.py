# -*- coding: utf-8 -*-
# models/product_template.py
from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_variant_name(self):
        """Retourne le nom complet de la variante avec ses attributs"""
        variant_name = self.display_name
        if self.product_template_attribute_value_ids:
            attributes = []
            for attr_value in self.product_template_attribute_value_ids:
                attributes.append(f"{attr_value.attribute_id.name}: {attr_value.name}")
            variant_name = f"{self.product_tmpl_id.name} ({', '.join(attributes)})"
        return variant_name