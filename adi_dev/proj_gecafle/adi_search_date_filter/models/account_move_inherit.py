# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveSearchDate(models.Model):
    _inherit = 'account.move'

    # Champ Date pour la recherche (basé sur invoice_date)
    search_date = fields.Date(
        string="Rechercher Date",
        compute='_compute_search_date',
        store=True,
        help="Date de la facture pour la recherche"
    )

    @api.depends('invoice_date', 'date')
    def _compute_search_date(self):
        for record in self:
            # Utiliser invoice_date pour les factures, sinon date
            record.search_date = record.invoice_date or record.date
