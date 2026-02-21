# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPartnerLedgerDetailed(models.TransientModel):
    _name = "account.report.partner.ledger.detailed"
    _inherit = "account.common.partner.report"
    _description = "Rapport Grand Livre Détaillé Partenaire"

    amount_currency = fields.Boolean(
        "Avec Devise",
        help="Ajoute la colonne devise au rapport si la devise "
             "diffère de la devise de la société.")
    reconciled = fields.Boolean('Écritures lettrées')

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({
            'reconciled': self.reconciled,
            'amount_currency': self.amount_currency,
        })
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref(
            'adi_partner_reports.action_report_partner_ledger_detailed'
        ).with_context(landscape=False).report_action(self, data=data)
