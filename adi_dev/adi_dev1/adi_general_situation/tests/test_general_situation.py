# -*- coding: utf-8 -*-
"""
Tests du wizard `general.situation` — Situation Générale.

Couverture :
  Groupe 1 — Presets de période (_onchange_period_preset)
  Groupe 2 — Validation des dates (_check_dates)
  Groupe 3 — Reconstruction historique du solde trésorerie
  Groupe 4 — Formules de calcul (balance_net, profit_net, isolation société)
  Groupe 5 — Actions (action_calculate, action_print_pdf)

Lancement :
  ./odoo-bin -c odoo17.conf -d <db> -i adi_general_situation \\
      --test-enable --test-tags adi_general_situation --stop-after-init
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('adi_general_situation', 'post_install', '-at_install')
class TestGeneralSituationPresets(TransactionCase):
    """Groupe 1 — Presets de période et Groupe 2 — Validation des dates."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_wizard(self, preset, date_from=None, date_to=None):
        """Instancie le wizard via new() pour activer les onchanges.

        :param preset: valeur du champ period_preset
        :param date_from: date de début optionnelle (pour preset='custom')
        :param date_to: date de fin optionnelle (pour preset='custom')
        :returns: enregistrement `general.situation` en mémoire
        """
        vals = {'period_preset': preset}
        if date_from:
            vals['date_from'] = date_from
        if date_to:
            vals['date_to'] = date_to
        return self.env['general.situation'].new(vals)

    # ------------------------------------------------------------------
    # Groupe 1 — Presets
    # ------------------------------------------------------------------

    def test_preset_today(self):
        """preset='today' doit positionner date_from = date_to = aujourd'hui."""
        wizard = self._new_wizard('today')
        wizard._onchange_period_preset()

        today = date.today()
        self.assertEqual(wizard.date_from, today,
                         "date_from doit être aujourd'hui pour le preset 'today'")
        self.assertEqual(wizard.date_to, today,
                         "date_to doit être aujourd'hui pour le preset 'today'")

    def test_preset_this_month(self):
        """preset='this_month' doit couvrir du 1er au dernier jour du mois courant."""
        wizard = self._new_wizard('this_month')
        wizard._onchange_period_preset()

        today = date.today()
        expected_from = today.replace(day=1)
        expected_to = today.replace(day=1) + relativedelta(months=1, days=-1)

        self.assertEqual(wizard.date_from, expected_from,
                         "date_from doit être le 1er du mois courant")
        self.assertEqual(wizard.date_to, expected_to,
                         "date_to doit être le dernier jour du mois courant")

    def test_preset_last_month(self):
        """preset='last_month' doit couvrir le mois précédent complet."""
        wizard = self._new_wizard('last_month')
        wizard._onchange_period_preset()

        today = date.today()
        expected_from = today.replace(day=1) - relativedelta(months=1)
        expected_to = today.replace(day=1) - timedelta(days=1)

        self.assertEqual(wizard.date_from, expected_from,
                         "date_from doit être le 1er du mois précédent")
        self.assertEqual(wizard.date_to, expected_to,
                         "date_to doit être le dernier jour du mois précédent")

    def test_preset_this_year(self):
        """preset='this_year' doit couvrir du 01/01 au 31/12 de l'année courante."""
        wizard = self._new_wizard('this_year')
        wizard._onchange_period_preset()

        year = date.today().year
        self.assertEqual(wizard.date_from, date(year, 1, 1),
                         "date_from doit être le 01/01 de l'année courante")
        self.assertEqual(wizard.date_to, date(year, 12, 31),
                         "date_to doit être le 31/12 de l'année courante")

    def test_preset_last_year(self):
        """preset='last_year' doit couvrir du 01/01 au 31/12 de l'année précédente."""
        wizard = self._new_wizard('last_year')
        wizard._onchange_period_preset()

        year = date.today().year - 1
        self.assertEqual(wizard.date_from, date(year, 1, 1),
                         "date_from doit être le 01/01 de l'année N-1")
        self.assertEqual(wizard.date_to, date(year, 12, 31),
                         "date_to doit être le 31/12 de l'année N-1")

    def test_preset_custom_does_not_modify_dates(self):
        """preset='custom' ne doit pas modifier les dates saisies par l'utilisateur."""
        fixed_from = date(2025, 3, 10)
        fixed_to = date(2025, 3, 25)
        wizard = self._new_wizard('custom', date_from=fixed_from, date_to=fixed_to)
        wizard._onchange_period_preset()

        self.assertEqual(wizard.date_from, fixed_from,
                         "date_from ne doit pas être modifiée par le preset 'custom'")
        self.assertEqual(wizard.date_to, fixed_to,
                         "date_to ne doit pas être modifiée par le preset 'custom'")

    @freeze_time("2026-03-15")
    def test_preset_quarter_correct_boundaries_q1(self):
        """preset='this_quarter' le 15 mars 2026 → 01/01/2026–31/03/2026."""
        wizard = self._new_wizard('this_quarter')
        wizard._onchange_period_preset()

        self.assertEqual(wizard.date_from, date(2026, 1, 1),
                         "Q1 2026 doit commencer le 01/01/2026")
        self.assertEqual(wizard.date_to, date(2026, 3, 31),
                         "Q1 2026 doit se terminer le 31/03/2026")

    @freeze_time("2026-08-15")
    def test_preset_quarter_correct_boundaries_q3(self):
        """preset='this_quarter' le 15 août 2026 → 01/07/2026–30/09/2026."""
        wizard = self._new_wizard('this_quarter')
        wizard._onchange_period_preset()

        self.assertEqual(wizard.date_from, date(2026, 7, 1),
                         "Q3 2026 doit commencer le 01/07/2026")
        self.assertEqual(wizard.date_to, date(2026, 9, 30),
                         "Q3 2026 doit se terminer le 30/09/2026")

    # ------------------------------------------------------------------
    # Groupe 2 — Validation des dates
    # ------------------------------------------------------------------

    def test_date_from_after_date_to_raises(self):
        """date_from > date_to doit lever une UserError lors du create()."""
        with self.assertRaises(UserError,
                               msg="Une UserError doit être levée si date_from > date_to"):
            self.env['general.situation'].create({
                'period_preset': 'custom',
                'date_from': date(2026, 4, 30),
                'date_to': date(2026, 4, 1),
            })


@tagged('adi_general_situation', 'post_install', '-at_install')
class TestGeneralSituationHistoricalCash(TransactionCase):
    """Groupe 3 — Reconstruction historique du solde trésorerie."""

    def test_cash_balance_uses_live_when_date_to_is_today(self):
        """date_to = aujourd'hui → on utilise current_balance (valeur live)."""
        today = fields.Date.today()
        wizard = self.env['general.situation'].create({
            'period_preset': 'today',
            'date_from': today,
            'date_to': today,
        })
        # Sans caisse en base, le solde live = 0 → la valeur retournée doit
        # être 0.0. Ce qui valide aussi que le code n'erreure pas.
        result = wizard._compute_cash_balance_value()
        self.assertEqual(result, 0.0,
                         "Sans caisse, solde live = 0.0")

    def test_cash_balance_reconstructs_when_date_to_is_past(self):
        """date_to < aujourd'hui → branche reconstruction historique.

        Le test vérifie que la méthode ne lève pas d'exception et retourne
        une valeur numérique. Le détail de la reconstruction (closings +
        opérations) est validé en intégration sur la base réelle.
        """
        yesterday = fields.Date.today() - timedelta(days=1)
        first_of_month = yesterday.replace(day=1)
        wizard = self.env['general.situation'].create({
            'period_preset': 'custom',
            'date_from': first_of_month,
            'date_to': yesterday,
        })
        result = wizard._compute_cash_balance_value()
        self.assertIsInstance(result, (int, float),
                              "La reconstruction doit retourner un nombre")


@tagged('adi_general_situation', 'post_install', '-at_install')
class TestGeneralSituationCalculations(TransactionCase):
    """Groupe 4 & 5 — Formules de calcul et actions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Désactiver le tracking mail pour alléger les fixtures
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        # Compte de revenus pour les factures
        cls.account_revenue = cls.env['account.account'].search([
            ('company_id', '=', cls.company.id),
            ('account_type', '=', 'income'),
            ('deprecated', '=', False),
        ], limit=1)
        if not cls.account_revenue:
            cls.account_revenue = cls.env['account.account'].create({
                'name': 'Test Revenue GS',
                'code': 'TEST_GS_REV',
                'account_type': 'income',
                'company_id': cls.company.id,
            })

        # Partenaire client
        cls.partner = cls.env['res.partner'].create({'name': 'Client Test GS'})

        # Produit avec prix de revient connu pour tester la marge
        cls.product = cls.env['product.product'].create({
            'name': 'Produit Test GS',
            'type': 'service',
            'standard_price': 60.0,
            'list_price': 100.0,
        })

        # Journal de vente
        cls.journal_sale = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'sale'),
        ], limit=1)

        # Catégorie de dépense
        cls.depense_categ = cls.env['depenses.categorie'].create({
            'name': 'Charges Test GS',
        })

        # Caisse (treasury.cash crée le journal automatiquement si absent)
        cls.cash = cls.env['treasury.cash'].create({
            'name': 'Caisse Test GS',
            'code': 'TGSXX',
        })

        # Clôture ouverte pour que les opérations de caisse soient acceptées
        cls.closing = cls.env['treasury.cash.closing'].create({
            'cash_id': cls.cash.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_wizard(self, date_from=None, date_to=None):
        """Crée un wizard `general.situation` pour la période donnée.

        :param date_from: date de début (défaut: 1er du mois courant)
        :param date_to: date de fin (défaut: dernier du mois courant)
        :returns: enregistrement `general.situation`
        """
        today = fields.Date.today()
        if date_from is None:
            date_from = today.replace(day=1)
        if date_to is None:
            date_to = today.replace(day=1) + relativedelta(months=1, days=-1)
        return self.env['general.situation'].create({
            'period_preset': 'custom',
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.company.id,
        })

    def _make_invoice(self, price_unit=100.0, qty=1.0, invoice_date=None):
        """Crée et poste une facture client avec prix de vente et coût connus.

        :param price_unit: prix de vente unitaire HT
        :param qty: quantité
        :param invoice_date: date de facturation (défaut: aujourd'hui)
        :returns: `account.move` posté
        """
        if invoice_date is None:
            invoice_date = fields.Date.today()
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal_sale.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': qty,
                'price_unit': price_unit,
                'account_id': self.account_revenue.id,
            })],
        })
        move.action_post()
        return move

    def _make_expense(self, montant=100.0, expense_date=None):
        """Crée et poste une dépense sur la caisse de test.

        :param montant: montant de la dépense
        :param expense_date: date de la dépense (défaut: aujourd'hui)
        :returns: `depenses.depense` postée
        """
        if expense_date is None:
            expense_date = fields.Date.today()
        depense = self.env['depenses.depense'].create({
            'date': expense_date,
            'montant': montant,
            'categorie': self.depense_categ.id,
            'description': 'Charge test GS',
            'caisse_id': self.cash.id,
        })
        depense.action_post()
        return depense

    # ------------------------------------------------------------------
    # Groupe 4 — Formules de calcul
    # ------------------------------------------------------------------

    def test_zero_data(self):
        """Sans données métier, tous les composants doivent valoir 0."""
        wizard = self._make_wizard()
        wizard.action_calculate()

        self.assertEqual(wizard.gross_margin, 0.0,
                         "gross_margin doit être 0 sans factures")
        self.assertEqual(wizard.expenses_total, 0.0,
                         "expenses_total doit être 0 sans dépenses")
        self.assertEqual(wizard.balance_net, wizard.cash_balance
                         + wizard.stock_value
                         + wizard.receivables_total
                         - wizard.payables_total,
                         "balance_net doit respecter la formule")
        self.assertEqual(wizard.profit_net, 0.0,
                         "profit_net doit être 0 quand marge=0 et frais=0")

    def test_profit_formula(self):
        """profit_net = gross_margin - expenses_total.

        Facture  : prix=100, coût=60, marge=40
        Dépense  : 15
        Résultat : 40 - 15 = 25
        """
        today = fields.Date.today()
        self._make_invoice(price_unit=100.0, qty=1.0, invoice_date=today)
        self._make_expense(montant=15.0, expense_date=today)

        wizard = self._make_wizard(date_from=today, date_to=today)
        wizard.action_calculate()

        # La marge produit : (price_unit - standard_price) * qty = (100-60)*1 = 40
        self.assertAlmostEqual(wizard.gross_margin, 40.0, places=2,
                               msg="gross_margin doit être 40 pour (100-60)*1")
        self.assertAlmostEqual(wizard.expenses_total, 15.0, places=2,
                               msg="expenses_total doit être 15")
        self.assertAlmostEqual(wizard.profit_net, 25.0, places=2,
                               msg="profit_net doit être gross_margin - expenses_total = 25")

    def test_payables_displayed_as_positive(self):
        """payables_total doit être positif (valeur absolue de la balance comptable).

        On vérifie que la formule de balance_net soustrait bien payables_total
        (qui est déjà positif), sans double négation.
        """
        wizard = self._make_wizard()
        wizard.action_calculate()

        self.assertGreaterEqual(wizard.payables_total, 0.0,
                                "payables_total ne doit jamais être négatif")
        self.assertAlmostEqual(
            wizard.balance_net,
            wizard.cash_balance + wizard.stock_value
            + wizard.receivables_total - wizard.payables_total,
            places=2,
            msg="balance_net = cash + stock + créances - dettes",
        )

    def test_company_isolation(self):
        """Les opérations d'une autre société ne doivent pas contaminer les calculs.

        Une facture postée sur une 2e société ne doit pas modifier la marge
        ni le profit calculés pour la société courante.
        """
        # Mémoriser le profit de référence sur la société courante
        today = fields.Date.today()
        wizard_before = self._make_wizard(date_from=today, date_to=today)
        wizard_before.action_calculate()
        ref_margin = wizard_before.gross_margin

        # Créer une 2e société et y poster une facture
        other_company = self.env['res.company'].create({
            'name': 'Société Isolée Test GS',
        })

        # Chercher un journal de vente sur l'autre société
        other_journal = self.env['account.journal'].search([
            ('company_id', '=', other_company.id),
            ('type', '=', 'sale'),
        ], limit=1)

        if other_journal:
            other_revenue = self.env['account.account'].search([
                ('company_id', '=', other_company.id),
                ('account_type', '=', 'income'),
                ('deprecated', '=', False),
            ], limit=1)

            other_partner = self.env['res.partner'].sudo().create(
                {'name': 'Partenaire Autre Société GS'}
            )
            other_move = self.env['account.move'].sudo().with_company(
                other_company
            ).create({
                'move_type': 'out_invoice',
                'partner_id': other_partner.id,
                'journal_id': other_journal.id,
                'invoice_date': today,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'name': 'Produit autre société',
                    'quantity': 1.0,
                    'price_unit': 9999.0,
                    'account_id': other_revenue.id,
                })],
            })
            other_move.sudo().with_company(other_company).action_post()

        # Vérifier que la marge de la société courante est inchangée
        wizard_after = self._make_wizard(date_from=today, date_to=today)
        wizard_after.action_calculate()

        self.assertAlmostEqual(
            wizard_after.gross_margin,
            ref_margin,
            places=2,
            msg="La marge de la société courante ne doit pas inclure "
                "les factures de la 2e société",
        )

    # ------------------------------------------------------------------
    # Groupe 5 — Actions
    # ------------------------------------------------------------------

    def test_action_calculate_returns_action(self):
        """action_calculate() doit retourner un dict d'action ir.actions.act_window."""
        wizard = self._make_wizard()
        result = wizard.action_calculate()

        self.assertIsInstance(result, dict,
                              "action_calculate doit retourner un dict")
        self.assertEqual(result.get('type'), 'ir.actions.act_window',
                         "Le type doit être 'ir.actions.act_window'")
        self.assertEqual(result.get('res_model'), 'general.situation',
                         "res_model doit être 'general.situation'")
        self.assertEqual(result.get('res_id'), wizard.id,
                         "res_id doit pointer vers le wizard courant")

    def test_action_print_pdf_returns_report(self):
        """action_print_pdf() doit retourner un dict d'action de rapport."""
        wizard = self._make_wizard()
        result = wizard.action_print_pdf()

        self.assertIsInstance(result, dict,
                              "action_print_pdf doit retourner un dict")
        self.assertIn(result.get('type'), ('ir.actions.report', 'ir.actions.act_url'),
                      "Le type doit être un type de rapport")
