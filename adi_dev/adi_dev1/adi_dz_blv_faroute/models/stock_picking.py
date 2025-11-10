# -*- coding: utf-8 -*-

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    num_fact = fields.Char("N° de Facture de R")

    sale_order_amount = fields.Float(string="Sale Order Amount",
                                     compute="_compute_sale_order_amount", store=True)

    @api.depends('move_ids', 'sale_id')
    def _compute_sale_order_amount(self):
        for picking in self:
            total_amount = 0.0
            # Loop through the stock.move lines of the picking
            for move in picking.move_ids:
                # Get the sale order line associated with the product in the stock.move
                sale_order_line = move.sale_line_id
                if sale_order_line:
                    # Calculate the amount based on the sale order line
                    total_amount += sale_order_line.price_total
            picking.sale_order_amount = total_amount

    # Champ calculé pour la TVA (19 % du Montant HT)
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.user.company_id.currency_id
    )

    tva_amount = fields.Monetary(
        string="TVA (19%)",
        compute='_compute_ttc',
        store=True,
        currency_field='currency_id'
    )

    # Champ calculé pour le total HT + TVA
    total_ttc = fields.Monetary(
        string="Total TTC ",
        compute='_compute_ttc',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('sale_order_amount')
    def _compute_ttc(self):
        for order in self:
            # Calcul de la TVA : 19% du Montant HT
            order.tva_amount = order.sale_order_amount * 0.19
            # Calcul du Total avec TVA : Montant HT + TVA
            order.total_ttc = order.sale_order_amount + order.tva_amount

    def get_amount_to_text_ttcdz(self):
        return self.currency_id.amount_to_text_dz(self.total_ttc)


