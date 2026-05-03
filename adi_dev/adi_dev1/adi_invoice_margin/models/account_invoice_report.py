# -*- coding: utf-8 -*-

from odoo import api, fields, models

# Design : account.invoice.report est un modèle SQL view (_auto=False) reconstruit
# par _table_query = _select() + _from() + _where(). On étend en overridant
# _select() pour ajouter nos colonnes propres : `margin` (montant) et
# `margin_percent` (pourcent stocké en valeur 0-100).
#
# On inline les sous-expressions car PostgreSQL n'autorise pas la référence
# d'alias dans le même SELECT. Les colonnes ajoutées :
#
#   margin         = revenue - cost
#   margin_percent = (revenue - cost) * 100 / NULLIF(cost, 0)        ← convention "sur coût"
#
# avec :
#   revenue       = -line.balance * currency_table.rate
#   cost          = qty_converted * standard_price
#   qty_converted = line.quantity / (uom_line.factor / uom_template.factor)
#
# `margin` et `margin_percent` sont à 0 hors out_invoice/out_receipt, en
# cohérence avec les compute Python de account.move(.line).


# Sous-expression de coût réutilisée par margin et margin_percent.
_COST_SQL = """(
    line.quantity
    / NULLIF(
        COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1),
        0.0
    )
) * COALESCE(product_standard_price.value_float, 0.0)"""

# Sous-expression de chiffre d'affaires (revenue) en devise du rapport.
_REVENUE_SQL = "-line.balance * currency_table.rate"


class AccountInvoiceReport(models.Model):
    """Extend account.invoice.report with margin and margin_percent columns."""

    _inherit = 'account.invoice.report'

    margin = fields.Float(
        string='Marge',
        readonly=True,
    )
    margin_percent = fields.Float(
        string='Marge (%)',
        readonly=True,
        group_operator='avg',
    )

    @api.model
    def _select(self):
        parent_select = super()._select()

        extra_sql = f""",
            CASE
                WHEN move.move_type NOT IN ('out_invoice', 'out_receipt') THEN 0.0
                ELSE ({_REVENUE_SQL}) - ({_COST_SQL})
            END AS margin,
            CASE
                WHEN move.move_type NOT IN ('out_invoice', 'out_receipt') THEN 0.0
                ELSE (
                    (({_REVENUE_SQL}) - ({_COST_SQL})) * 100.0
                ) / NULLIF({_COST_SQL}, 0)
            END AS margin_percent
        """

        return parent_select + extra_sql
