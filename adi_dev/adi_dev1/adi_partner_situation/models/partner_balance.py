# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PartnerBalanceWizard(models.TransientModel):
    _name = 'partner.balance.wizard'
    _description = 'Consulter les Soldes Partenaires'

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company
    )
    date_from = fields.Date(string='Date debut')
    date_to = fields.Date(string='Date fin')
    user_ids = fields.Many2many(
        'res.users',
        'partner_balance_wizard_user_rel',
        'wizard_id',
        'user_id',
        string='Vendeurs',
        help="Filtrer par vendeur des factures. Laissez vide pour inclure tous les vendeurs."
    )
    partner_ids = fields.Many2many(
        'res.partner',
        'partner_balance_wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string='Partenaires'
    )
    result_selection = fields.Selection([
        ('customer', 'Comptes Clients'),
        ('supplier', 'Comptes Fournisseurs'),
        ('customer_supplier', 'Clients et Fournisseurs')
    ], string='Type de Partenaire', required=True, default='customer')
    target_move = fields.Selection([
        ('posted', 'Ecritures Comptabilisees'),
        ('all', 'Toutes les Ecritures'),
    ], string='Ecritures Cibles', required=True, default='posted')
    reconciled = fields.Boolean('Inclure Lettrees', default=True)
    line_ids = fields.One2many(
        'partner.balance.line',
        'wizard_id',
        string='Lignes'
    )

    def action_compute(self):
        """Compute partner balances and display results"""
        self.ensure_one()
        self.line_ids.unlink()

        # Determine account types
        if self.result_selection == 'supplier':
            account_types = ['liability_payable']
        elif self.result_selection == 'customer':
            account_types = ['asset_receivable']
        else:
            account_types = ['asset_receivable', 'liability_payable']

        # Get account IDs
        self.env.cr.execute("""
            SELECT id FROM account_account
            WHERE account_type IN %s
            AND company_id = %s
            AND NOT deprecated
        """, (tuple(account_types), self.company_id.id))
        account_ids = [row[0] for row in self.env.cr.fetchall()]

        if not account_ids:
            return self._return_action()

        # Build move state filter
        move_states = ['posted'] if self.target_move == 'posted' else ['draft', 'posted']

        # Build user filter
        user_clause = ""
        params = [tuple(move_states), tuple(account_ids), self.company_id.id]
        if self.user_ids:
            user_clause = " AND am.invoice_user_id IN %s "
            params.append(tuple(self.user_ids.ids))

        # Build partner filter
        partner_clause = ""
        if self.partner_ids:
            partner_clause = " AND aml.partner_id IN %s "
            params.append(tuple(self.partner_ids.ids))

        # Build date filter
        date_clause = ""
        if self.date_from:
            date_clause += " AND aml.date >= %s "
            params.append(self.date_from)
        if self.date_to:
            date_clause += " AND aml.date <= %s "
            params.append(self.date_to)

        # Build reconcile filter
        reconcile_clause = "" if self.reconciled else " AND aml.full_reconcile_id IS NULL "

        # Main query to get partner balances with user info
        query = """
            SELECT
                aml.partner_id,
                am.invoice_user_id as user_id,
                SUM(aml.debit) as total_debit,
                SUM(aml.credit) as total_credit,
                SUM(aml.debit - aml.credit) as balance
            FROM account_move_line aml
            INNER JOIN account_move am ON am.id = aml.move_id
            WHERE am.state IN %s
                AND aml.account_id IN %s
                AND aml.company_id = %s
                AND aml.partner_id IS NOT NULL
                """ + user_clause + partner_clause + date_clause + reconcile_clause + """
            GROUP BY aml.partner_id, am.invoice_user_id
            HAVING SUM(aml.debit) != 0 OR SUM(aml.credit) != 0
            ORDER BY aml.partner_id, am.invoice_user_id
        """

        self.env.cr.execute(query, tuple(params))
        results = self.env.cr.dictfetchall()

        # Create balance lines
        lines_vals = []
        for row in results:
            partner = self.env['res.partner'].browse(row['partner_id'])
            lines_vals.append({
                'wizard_id': self.id,
                'partner_id': row['partner_id'],
                'partner_ref': partner.ref or '',
                'user_id': row['user_id'] or False,
                'debit': row['total_debit'] or 0.0,
                'credit': row['total_credit'] or 0.0,
                'balance': row['balance'] or 0.0,
            })

        self.env['partner.balance.line'].create(lines_vals)

        return self._return_action()

    def _return_action(self):
        """Return action to display wizard with computed lines"""
        return {
            'name': 'Soldes Partenaires',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.balance.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_view_list(self):
        """Open computed lines in a separate list view with search/group capabilities"""
        self.ensure_one()
        if not self.line_ids:
            # Compute first if no lines
            self.action_compute()

        return {
            'name': 'Soldes Partenaires',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.balance.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('adi_partner_situation.partner_balance_line_tree').id, 'tree')],
            'search_view_id': [self.env.ref('adi_partner_situation.partner_balance_line_search').id, 'search'],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': {
                'search_default_group_user': 1,
            },
        }


class PartnerBalanceLine(models.TransientModel):
    _name = 'partner.balance.line'
    _description = 'Ligne Solde Partenaire'
    _order = 'partner_ref, partner_id, user_id'

    wizard_id = fields.Many2one('partner.balance.wizard', string='Wizard', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partenaire', readonly=True)
    partner_ref = fields.Char(string='Reference', readonly=True)
    user_id = fields.Many2one('res.users', string='Vendeur', readonly=True)
    debit = fields.Float(string='Debit', readonly=True, digits='Account')
    credit = fields.Float(string='Credit', readonly=True, digits='Account')
    balance = fields.Float(string='Solde', readonly=True, digits='Account')

    def action_view_details(self):
        """Open detailed partner ledger view"""
        self.ensure_one()
        wizard = self.wizard_id

        # Build domain for move lines
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('company_id', '=', wizard.company_id.id),
        ]

        # Account type filter
        if wizard.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
        elif wizard.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        else:
            domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))

        # Move state filter
        if wizard.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        # Date filter
        if wizard.date_from:
            domain.append(('date', '>=', wizard.date_from))
        if wizard.date_to:
            domain.append(('date', '<=', wizard.date_to))

        # User filter - use line's user_id if set, otherwise wizard's user_ids
        if self.user_id:
            domain.append(('move_id.invoice_user_id', '=', self.user_id.id))
        elif wizard.user_ids:
            domain.append(('move_id.invoice_user_id', 'in', wizard.user_ids.ids))

        # Reconcile filter
        if not wizard.reconciled:
            domain.append(('full_reconcile_id', '=', False))

        # Build name
        name = f'Details - {self.partner_id.name}'
        if self.user_id:
            name += f' ({self.user_id.name})'

        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'search_default_group_by_move': 1},
        }
