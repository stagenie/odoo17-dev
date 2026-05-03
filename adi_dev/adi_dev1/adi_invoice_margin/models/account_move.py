# -*- coding: utf-8 -*-

from odoo import api, fields, models

# Move types representing customer-facing revenue documents.
_CUSTOMER_MOVE_TYPES = ('out_invoice', 'out_refund')


class AccountMove(models.Model):
    """Extend account.move with aggregate margin fields.

    Mirrors addons/sale_margin/models/sale_order.py: sum line margins,
    compute percent against amount_untaxed.  Restricted to customer
    invoices/refunds — all other move types yield 0.
    """

    _inherit = 'account.move'

    margin = fields.Monetary(
        string='Marge',
        compute='_compute_margin',
        store=True,
        currency_field='currency_id',
    )
    margin_percent = fields.Float(
        string='Marge (%)',
        compute='_compute_margin',
        store=True,
        group_operator='avg',
    )

    @api.depends(
        'invoice_line_ids.margin',
        'invoice_line_ids.purchase_price',
        'invoice_line_ids.quantity',
        'move_type',
    )
    def _compute_margin(self):
        """Aggregate line margins to the invoice level (markup convention).

        margin_percent = sum(margin) / sum(purchase_price * quantity)
        soit le taux de marge sur coût total des lignes.

        On itère sur invoice_line_ids (déjà préchargé via le depends) plutôt
        que de cumuler purchase_price/quantity en SQL : les lignes sont déjà
        en cache et le calcul reste O(n) sur la facture.
        """
        for move in self:
            if move.move_type not in _CUSTOMER_MOVE_TYPES:
                move.margin = 0.0
                move.margin_percent = 0.0
                continue
            lines = move.invoice_line_ids
            move.margin = sum(lines.mapped('margin'))
            cost_total = abs(sum(
                line.purchase_price * line.quantity for line in lines
            ))
            # Stocké en valeur pourcent (50.0 = 50 %) — voir commentaire compute ligne.
            move.margin_percent = (move.margin / cost_total) * 100.0 if cost_total else 0.0
