# -*- coding: utf-8 -*-

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    num_fact = fields.Char("N° de Facture de R")

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

    @api.depends('amount_untaxed')
    def _compute_ttc(self):
        for order in self:
            # Calcul de la TVA : 19% du Montant HT
            order.tva_amount = order.amount_untaxed * 0.19
            # Calcul du Total avec TVA : Montant HT + TVA
            order.total_ttc = order.amount_untaxed + order.tva_amount

    def get_amount_to_text_ttcdz(self):
        return self.currency_id.amount_to_text_dz(self.total_ttc)

    
