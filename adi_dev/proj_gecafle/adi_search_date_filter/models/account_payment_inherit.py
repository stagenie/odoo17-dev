# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountPaymentSearchDate(models.Model):
    _inherit = 'account.payment'

    # Champ Date pour la recherche (basé sur le champ date existant)
    search_date = fields.Date(
        string="Rechercher Date",
        compute='_compute_search_date',
        store=True,
        help="Date du paiement pour la recherche"
    )

    @api.depends('date')
    def _compute_search_date(self):
        for record in self:
            record.search_date = record.date
