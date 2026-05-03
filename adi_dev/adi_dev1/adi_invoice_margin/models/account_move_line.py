# -*- coding: utf-8 -*-

from odoo import api, fields, models

# Move types representing customer-facing revenue documents.
_CUSTOMER_MOVE_TYPES = ('out_invoice', 'out_refund')


class AccountMoveLine(models.Model):
    """Extend account.move.line with margin calculation fields.

    Pattern mirrors addons/sale_margin/models/sale_order_line.py but adapted
    for account.move.line: currency conversion uses move_id.date instead of
    order_id.date_order, and sign handling accounts for out_refund polarity.
    """

    _inherit = 'account.move.line'

    purchase_price = fields.Float(
        string='Coût',
        digits='Product Price',
        compute='_compute_purchase_price',
        store=True,
        readonly=False,
        precompute=True,
    )
    margin = fields.Monetary(
        string='Marge',
        compute='_compute_margin',
        store=True,
        currency_field='currency_id',
        precompute=True,
    )
    margin_percent = fields.Float(
        string='Marge (%)',
        compute='_compute_margin',
        store=True,
        precompute=True,
        group_operator='avg',
    )

    @api.depends('product_id', 'company_id', 'currency_id', 'date')
    def _compute_purchase_price(self):
        """Compute the unit cost in the line's currency.

        For customer invoice/refund lines: read product.standard_price (stored
        in the product's cost currency, i.e. company currency) and convert to
        the line's transaction currency using the invoice date as exchange date.
        UoM conversion is applied when line uom differs from product's base uom.

        For all other move types the cost is forced to 0 so no margin appears.
        """
        for line in self:
            if not line.product_id or line.move_id.move_type not in _CUSTOMER_MOVE_TYPES:
                line.purchase_price = 0.0
                continue

            # Work in the correct company context so standard_price is read
            # with the right company currency (mirrors sale_margin pattern).
            line_ctx = line.with_company(line.company_id)
            product = line_ctx.product_id

            # Convert from base UoM to line UoM if they differ.
            cost = product.uom_id._compute_price(
                product.standard_price,
                line.product_uom_id or product.uom_id,
            )

            # Convert cost from product cost currency to line transaction currency.
            cost_currency = product.cost_currency_id
            line_currency = line.currency_id or line.company_currency_id
            if cost_currency and line_currency and cost_currency != line_currency:
                conversion_date = line.date or fields.Date.context_today(line)
                company = line.company_id or line.env.company
                cost = cost_currency._convert(
                    from_amount=cost,
                    to_currency=line_currency,
                    company=company,
                    date=conversion_date,
                    round=False,
                )

            line.purchase_price = cost

    @api.depends('purchase_price', 'price_subtotal', 'quantity', 'move_id.move_type')
    def _compute_margin(self):
        """Compute margin amount and margin percent (markup convention).

        margin_percent = margin / cost_total
            où cost_total = purchase_price * quantity (en valeur absolue)

        C'est le « taux de marge sur coût » (anglais : markup) :
        un produit acheté 10 et vendu 15 → marge = 5, marge % = 5/10 = 50 %.

        Sign convention for out_refund:
          price_subtotal on a refund line is a positive number (the refunded
          amount). A refund reverses revenue, so we negate the margin so that
          posting a refund shows a negative contribution to margin (revenue lost).

        Si le coût est nul (produit sans standard_price ou ligne sans produit),
        margin_percent = 0 pour éviter une division par zéro.
        """
        for line in self:
            move_type = line.move_id.move_type

            if move_type not in _CUSTOMER_MOVE_TYPES:
                line.margin = 0.0
                line.margin_percent = 0.0
                continue

            gross_margin = line.price_subtotal - line.purchase_price * line.quantity

            if move_type == 'out_refund':
                # Negate: a credit note reduces margin by reversing the revenue.
                line.margin = -gross_margin
            else:
                line.margin = gross_margin

            cost_total = abs(line.purchase_price * line.quantity)
            # Stocké directement en valeur pourcent (50.0 = 50 %) pour un affichage
            # cohérent en form/tree ET en pivot/graph (qui n'ont pas de widget percentage).
            line.margin_percent = (line.margin / cost_total) * 100.0 if cost_total else 0.0
