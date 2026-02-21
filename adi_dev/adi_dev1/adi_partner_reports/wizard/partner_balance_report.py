# -*- coding: utf-8 -*-

from odoo import fields, models


class PartnerBalanceSummaryReport(models.TransientModel):
    _name = "partner.balance.summary.report"
    _inherit = "account.common.partner.report"
    _description = "Rapport Récapitulatif Solde Partenaire"

    reconciled = fields.Boolean('Écritures lettrées')

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled})
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref(
            'adi_partner_reports.action_report_partner_balance'
        ).with_context(landscape=False).report_action(self, data=data)
