# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportPartnerBalance(models.AbstractModel):
    _name = 'report.adi_partner_reports.report_partner_balance'
    _description = 'Rapport Solde Partenaire'

    def _get_partners_data(self, data, query_get_data, account_ids):
        """Retrieve partner balances for given account IDs."""
        reconcile_clause = ""
        if not data['form'].get('reconciled'):
            reconcile_clause = ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [
            tuple(data['computed']['move_state']),
            tuple(account_ids),
        ] + query_get_data[2]

        query = """
            SELECT
                "account_move_line".partner_id,
                rp.ref,
                rp.name,
                SUM("account_move_line".debit) AS total_debit,
                SUM("account_move_line".credit) AS total_credit,
                SUM("account_move_line".debit - "account_move_line".credit) AS balance
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_move m ON (m.id = "account_move_line".move_id)
            LEFT JOIN res_partner rp ON (rp.id = "account_move_line".partner_id)
            WHERE "account_move_line".partner_id IS NOT NULL
                AND m.state IN %s
                AND "account_move_line".account_id IN %s
                AND """ + query_get_data[1] + reconcile_clause + """
            GROUP BY "account_move_line".partner_id, rp.ref, rp.name
            ORDER BY rp.ref, rp.name
        """
        self.env.cr.execute(query, tuple(params))
        partners_data = self.env.cr.dictfetchall()

        # Filter by selected partners if any
        if data['form'].get('partner_ids'):
            partner_ids = data['form']['partner_ids']
            partners_data = [
                p for p in partners_data if p['partner_id'] in partner_ids]

        return partners_data

    def _get_account_ids(self, account_types):
        """Get account IDs for given account types."""
        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.account_type IN %s
            AND NOT a.deprecated""",
            (tuple(account_types),))
        return [a for (a,) in self.env.cr.fetchall()]

    @staticmethod
    def _compute_totals(partners_data):
        """Compute totals for a list of partner data."""
        return {
            'debit': sum(p['total_debit'] or 0.0 for p in partners_data),
            'credit': sum(p['total_credit'] or 0.0 for p in partners_data),
            'balance': sum(p['balance'] or 0.0 for p in partners_data),
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))

        data['computed'] = {}

        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()

        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']

        result_selection = data['form'].get('result_selection', 'customer')

        if result_selection == 'customer_supplier':
            # Combined mode: two separate sections
            customer_account_ids = self._get_account_ids(['asset_receivable'])
            supplier_account_ids = self._get_account_ids(['liability_payable'])

            if not customer_account_ids and not supplier_account_ids:
                raise UserError(_("No accounts found for the selected type."))

            data['computed']['account_ids'] = customer_account_ids + supplier_account_ids

            customer_data = self._get_partners_data(
                data, query_get_data, customer_account_ids) if customer_account_ids else []
            supplier_data = self._get_partners_data(
                data, query_get_data, supplier_account_ids) if supplier_account_ids else []

            customer_totals = self._compute_totals(customer_data)
            supplier_totals = self._compute_totals(supplier_data)

            grand_totals = {
                'debit': customer_totals['debit'] + supplier_totals['debit'],
                'credit': customer_totals['credit'] + supplier_totals['credit'],
                'balance': customer_totals['balance'] + supplier_totals['balance'],
            }

            return {
                'doc_ids': docids,
                'doc_model': 'res.partner',
                'data': data,
                'time': time,
                'report_title': 'RAPPORT CRÉANCES ET DETTES',
                'is_combined': True,
                'customer_data': customer_data,
                'customer_totals': customer_totals,
                'supplier_data': supplier_data,
                'supplier_totals': supplier_totals,
                'grand_totals': grand_totals,
                # Compatibility keys (unused in combined mode template)
                'partners_data': [],
                'total_debit': grand_totals['debit'],
                'total_credit': grand_totals['credit'],
                'total_balance': grand_totals['balance'],
            }

        else:
            # Single mode: customer or supplier
            if result_selection == 'supplier':
                account_types = ['liability_payable']
                report_title = 'RAPPORT DETTE FOURNISSEURS'
            else:
                account_types = ['asset_receivable']
                report_title = 'RAPPORT CRÉANCE CLIENTS'

            account_ids = self._get_account_ids(account_types)
            data['computed']['ACCOUNT_TYPE'] = account_types
            data['computed']['account_ids'] = account_ids

            if not account_ids:
                raise UserError(_("No accounts found for the selected type."))

            partners_data = self._get_partners_data(
                data, query_get_data, account_ids)
            totals = self._compute_totals(partners_data)

            return {
                'doc_ids': docids,
                'doc_model': 'res.partner',
                'data': data,
                'time': time,
                'report_title': report_title,
                'is_combined': False,
                'partners_data': partners_data,
                'total_debit': totals['debit'],
                'total_credit': totals['credit'],
                'total_balance': totals['balance'],
            }
