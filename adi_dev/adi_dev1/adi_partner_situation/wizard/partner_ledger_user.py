# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountPartnerLedgerUser(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    user_ids = fields.Many2many(
        'res.users',
        'account_partner_ledger_user_rel',
        'wizard_id',
        'user_id',
        string='Vendeurs',
        help="Filtrer par vendeur des factures. Laissez vide pour inclure tous les vendeurs."
    )

    def _get_report_data(self, data):
        """Override to add user_ids to report data"""
        data = super()._get_report_data(data)
        data['form'].update({'user_ids': self.user_ids.ids})
        return data
