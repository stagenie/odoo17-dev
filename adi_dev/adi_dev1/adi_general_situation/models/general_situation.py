# -*- coding: utf-8 -*-
"""
Modèle TransientModel `general.situation` — Situation Générale.

Calcule à la demande une balance (actif net) et un bénéfice (résultat net)
pour une période configurable via un preset ou des dates libres. Les données
proviennent de treasury.cash, stock.valuation.layer, account.move.line (SQL),
account.move.margin et depenses.depense.
"""
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GeneralSituation(models.TransientModel):
    """Tableau de bord Balance & Bénéfice calculé sur une période."""

    _name = 'general.situation'
    _description = 'Situation Générale (Balance & Bénéfice)'

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    period_preset = fields.Selection(
        selection=[
            ('today', "Aujourd'hui"),
            ('this_week', 'Cette Semaine'),
            ('this_month', 'Ce Mois'),
            ('last_month', 'Mois Précédent'),
            ('this_quarter', 'Ce Trimestre'),
            ('this_year', 'Cette Année'),
            ('last_year', 'Année Précédente'),
            ('custom', 'Personnalisée'),
        ],
        string='Période',
        default='this_month',
        required=True,
    )
    date_from = fields.Date(
        string='Du',
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='Au',
        required=True,
        default=lambda self: (
            date.today().replace(day=1) + relativedelta(months=1, days=-1)
        ),
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Composants Balance (actif net)
    # ------------------------------------------------------------------

    cash_balance = fields.Monetary(
        string='Trésorerie (caisses)',
        currency_field='currency_id',
        readonly=True,
    )
    stock_value = fields.Monetary(
        string='Valeur Stock Actuel',
        currency_field='currency_id',
        readonly=True,
    )
    receivables_total = fields.Monetary(
        string='Créances Clients',
        currency_field='currency_id',
        readonly=True,
    )
    payables_total = fields.Monetary(
        string='Dettes Fournisseurs',
        currency_field='currency_id',
        readonly=True,
    )
    balance_net = fields.Monetary(
        string='Balance Nette',
        currency_field='currency_id',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Composants Bénéfice (résultat net)
    # ------------------------------------------------------------------

    gross_margin = fields.Monetary(
        string='Marge Brute (factures)',
        currency_field='currency_id',
        readonly=True,
    )
    expenses_total = fields.Monetary(
        string='Total Frais (dépenses)',
        currency_field='currency_id',
        readonly=True,
    )
    profit_net = fields.Monetary(
        string='Bénéfice Net',
        currency_field='currency_id',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Détails (One2many)
    # ------------------------------------------------------------------

    cash_line_ids = fields.One2many(
        'general.situation.cash.line',
        'situation_id',
        string='Détail caisses',
    )
    stock_line_ids = fields.One2many(
        'general.situation.stock.line',
        'situation_id',
        string='Détail entrepôts',
    )

    # ------------------------------------------------------------------
    # Métadonnées
    # ------------------------------------------------------------------

    last_computed = fields.Datetime(
        string='Dernier calcul',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Onchange — preset de période
    # ------------------------------------------------------------------

    @api.onchange('period_preset')
    def _onchange_period_preset(self):
        """Ajuste date_from et date_to selon le preset sélectionné.

        Pour le preset 'custom', les dates sont laissées à la saisie libre.
        """
        if self.period_preset == 'custom':
            return

        today = date.today()

        mapping = {
            'today': (today, today),
            'this_week': (
                today - timedelta(days=today.weekday()),
                today,
            ),
            'this_month': (
                today.replace(day=1),
                today.replace(day=1) + relativedelta(months=1, days=-1),
            ),
            'last_month': (
                today.replace(day=1) - relativedelta(months=1),
                today.replace(day=1) - timedelta(days=1),
            ),
            'this_quarter': self._quarter_range(today),
            'this_year': (
                date(today.year, 1, 1),
                date(today.year, 12, 31),
            ),
            'last_year': (
                date(today.year - 1, 1, 1),
                date(today.year - 1, 12, 31),
            ),
        }

        self.date_from, self.date_to = mapping[self.period_preset]

    # ------------------------------------------------------------------
    # Contrainte
    # ------------------------------------------------------------------

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Lève une UserError si date_from est postérieure à date_to."""
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(
                    _("La date de début (%s) ne peut pas être postérieure "
                      "à la date de fin (%s).")
                    % (rec.date_from, rec.date_to)
                )

    # ------------------------------------------------------------------
    # Actions boutons
    # ------------------------------------------------------------------

    def action_calculate(self):
        """Calcule les 6 composants puis balance_net et profit_net.

        Rafraîchit l'enregistrement courant et renvoie une action qui
        réaffiche ce même formulaire.
        """
        self.ensure_one()

        cash_total, cash_lines_vals = self._compute_cash_balance_value()
        self.cash_balance = cash_total
        self.cash_line_ids.unlink()
        if cash_lines_vals:
            self.env['general.situation.cash.line'].create([
                dict(vals, situation_id=self.id) for vals in cash_lines_vals
            ])

        stock_total, stock_lines_vals = self._compute_stock_value_value()
        self.stock_value = stock_total
        self.stock_line_ids.unlink()
        if stock_lines_vals:
            self.env['general.situation.stock.line'].create([
                dict(vals, situation_id=self.id) for vals in stock_lines_vals
            ])

        self.receivables_total = self._compute_partner_balance('asset_receivable')
        self.payables_total = abs(self._compute_partner_balance('liability_payable'))
        self.gross_margin = self._compute_gross_margin_value()
        self.expenses_total = self._compute_expenses_total_value()

        self.balance_net = (
            self.cash_balance
            + self.stock_value
            + self.receivables_total
            - self.payables_total
        )
        self.profit_net = self.gross_margin - self.expenses_total
        self.last_computed = fields.Datetime.now()

        # Réaffiche le même enregistrement pour que les nouvelles valeurs
        # soient visibles dans la vue formulaire.
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_pdf(self):
        """Retourne l'action d'impression PDF pour cet enregistrement."""
        self.ensure_one()
        return self.env.ref(
            'adi_general_situation.action_report_general_situation'
        ).report_action(self)

    # ------------------------------------------------------------------
    # Helpers de calcul (privés)
    # ------------------------------------------------------------------

    def _compute_cash_balance_value(self):
        """Retourne (total, [{cash_id, name, code, balance}, ...]) à `date_to`.

        Si `date_to >= today`, on utilise la valeur live `current_balance`
        (déjà calculée par adi_treasury, plus rapide).

        Sinon, on reconstruit le solde historique pour chaque caisse :
            1. Cherche le dernier closing **validé** avec `closing_date <= date_to`.
            2. Part de `balance_end_real` du closing (ou 0 si aucun closing).
            3. Ajoute les opérations posted entre la fin du closing et la fin
               de journée de `date_to` ('in' = +amount, 'out' = -amount).
            4. Somme sur toutes les caisses de la société.

        Pattern d'après treasury_cash._compute_current_balance (treasury_cash.py:281).
        """
        self.ensure_one()
        today = fields.Date.today()
        caisses = self.env['treasury.cash'].search([
            ('company_id', '=', self.company_id.id),
        ])

        # Cas live : pas de reconstruction nécessaire
        if not self.date_to or self.date_to >= today:
            lines = [{
                'cash_id': c.id,
                'name': c.name,
                'code': c.code,
                'balance': c.current_balance,
            } for c in caisses]
            return sum(c.current_balance for c in caisses), lines

        # Cas historique : reconstruction par caisse
        Closing = self.env['treasury.cash.closing']
        Operation = self.env['treasury.cash.operation']
        end_of_day = datetime.combine(self.date_to, datetime.max.time())

        total = 0.0
        lines = []
        for caisse in caisses:
            last_closing = Closing.search([
                ('cash_id', '=', caisse.id),
                ('state', '=', 'validated'),
                ('closing_date', '<=', self.date_to),
            ], order='closing_date desc, closing_number desc', limit=1)

            if last_closing:
                balance = last_closing.balance_end_real or 0.0
                ops_lower_bound = datetime.combine(
                    last_closing.closing_date, datetime.max.time(),
                ) + timedelta(seconds=1)
                ops = Operation.search([
                    ('cash_id', '=', caisse.id),
                    ('state', '=', 'posted'),
                    ('date', '>=', ops_lower_bound),
                    ('date', '<=', end_of_day),
                ])
            else:
                # Aucun closing validé avant date_to : sommer toutes les ops
                # posted ≤ date_to depuis le début.
                balance = 0.0
                ops = Operation.search([
                    ('cash_id', '=', caisse.id),
                    ('state', '=', 'posted'),
                    ('date', '<=', end_of_day),
                ])

            for op in ops:
                if op.operation_type == 'in':
                    balance += op.amount
                elif op.operation_type == 'out':
                    balance -= op.amount

            total += balance
            lines.append({
                'cash_id': caisse.id,
                'name': caisse.name,
                'code': caisse.code,
                'balance': balance,
            })

        return total, lines

    def _compute_stock_value_value(self):
        """Retourne (total, [{warehouse_id, name, code, value}, ...]) à date_to.

        Le total provient de stock.valuation.layer (filtré par create_date ≤
        fin de journée de date_to) pour rester cohérent avec l'historique.

        Le détail par entrepôt utilise stock.quant.value (snapshot courant)
        car la valuation_layer n'a pas de lien direct avec un entrepôt.
        Les quants sont regroupés via location_id.warehouse_id et limités
        aux emplacements internes.
        """
        # Fin de journée de date_to : dernier instant du jour (23:59:59)
        date_to_end = fields.Datetime.to_datetime(self.date_to) + timedelta(
            days=1, seconds=-1
        )
        groups = self.env['stock.valuation.layer']._read_group(
            domain=[
                ('company_id', '=', self.company_id.id),
                ('create_date', '<=', date_to_end),
            ],
            aggregates=['value:sum'],
        )
        total = (groups[0][0] or 0.0) if groups else 0.0

        # Détail par entrepôt — snapshot courant (sudo pour contourner les
        # restrictions de groupe sur stock.quant.value).
        warehouses = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id),
        ])
        Quant = self.env['stock.quant'].sudo()
        lines = []
        for wh in warehouses:
            quants = Quant.search([
                ('company_id', '=', self.company_id.id),
                ('location_id.warehouse_id', '=', wh.id),
                ('location_id.usage', '=', 'internal'),
            ])
            wh_value = sum(quants.mapped('value'))
            if wh_value:
                lines.append({
                    'warehouse_id': wh.id,
                    'name': wh.name,
                    'code': wh.code,
                    'value': wh_value,
                })

        return total, lines

    def _compute_partner_balance(self, account_type):
        """Retourne SUM(debit − credit) au date_to pour un account_type donné.

        Utilise une requête SQL directe pour les performances sur de grandes
        bases. Retourne une valeur algébrique : positif pour asset_receivable,
        négatif pour liability_payable.

        :param account_type: 'asset_receivable' ou 'liability_payable'
        :return: float
        """
        accounts = self.env['account.account'].search([
            ('account_type', '=', account_type),
            ('company_id', '=', self.company_id.id),
            ('deprecated', '=', False),
        ])
        if not accounts:
            return 0.0

        self.env.cr.execute(
            """
            SELECT COALESCE(SUM(aml.debit - aml.credit), 0.0)
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
             WHERE am.state = 'posted'
               AND aml.account_id IN %s
               AND aml.company_id = %s
               AND aml.date <= %s
            """,
            (tuple(accounts.ids), self.company_id.id, self.date_to),
        )
        return self.env.cr.fetchone()[0] or 0.0

    def _compute_gross_margin_value(self):
        """Retourne la somme des marges brutes des factures clients postées sur la période.

        Les avoirs (out_refund) ont une marge négative et sont donc
        naturellement soustraits sans traitement supplémentaire.
        """
        groups = self.env['account.move']._read_group(
            domain=[
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', self.date_from),
                ('invoice_date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
            ],
            aggregates=['margin:sum'],
        )
        return groups[0][0] or 0.0 if groups else 0.0

    def _compute_expenses_total_value(self):
        """Retourne la somme des montants des dépenses comptabilisées sur la période.

        Le modèle `depenses.depense` n'a pas de champ `company_id` direct,
        mais il porte `caisse_id` (treasury.cash) qui en a un. On filtre
        donc via `caisse_id.company_id` pour isoler les frais de la société
        courante (sécurité multi-société).
        """
        groups = self.env['depenses.depense']._read_group(
            domain=[
                ('state', '=', 'posted'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('caisse_id.company_id', '=', self.company_id.id),
            ],
            aggregates=['montant:sum'],
        )
        return groups[0][0] or 0.0 if groups else 0.0

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    @staticmethod
    def _quarter_range(ref_date):
        """Retourne (premier_jour, dernier_jour) du trimestre contenant ref_date.

        :param ref_date: date de référence
        :return: tuple (date, date)
        """
        # Trimestre 0..3 → mois de début 1, 4, 7, 10
        quarter = (ref_date.month - 1) // 3
        start_month = quarter * 3 + 1
        start = date(ref_date.year, start_month, 1)
        end = start + relativedelta(months=3, days=-1)
        return start, end
