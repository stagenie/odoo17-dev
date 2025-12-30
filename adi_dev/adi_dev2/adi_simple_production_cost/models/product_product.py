# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    """Extension du template produit pour la gestion des rebuts récupérables."""
    _inherit = 'product.template'

    is_recoverable_scrap = fields.Boolean(
        string='Est un Rebut Récupérable',
        default=False,
        help="Cochez si ce produit est un rebut récupérable (vendable) issu de la production"
    )


class ProductProduct(models.Model):
    """Extension du produit pour la gestion des rebuts récupérables."""
    _inherit = 'product.product'

    is_recoverable_scrap = fields.Boolean(
        string='Est un Rebut Récupérable',
        related='product_tmpl_id.is_recoverable_scrap',
        store=True,
        readonly=False
    )
