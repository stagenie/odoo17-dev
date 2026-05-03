# -*- coding: utf-8 -*-
"""
Tests d'intégration pour le workflow Frais ADI <-> Trésorerie.

Couverture :
  - Création d'une opération de trésorerie au post d'un frais
  - Refus de poster sans clôture en cours
  - Annulation avant validation de clôture (autorisée)
  - Refus d'annulation après validation de clôture
  - Refus de suppression d'un frais comptabilisé
  - Carry-forward : frais en draft non emporté par une clôture validée

Lancement :
  ./odoo-bin -c odoo17.conf -d <db> -i adi_expenses_treasury \\
      --test-enable --test-tags adi_expenses_treasury --stop-after-init
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('adi_expenses_treasury', 'post_install', '-at_install')
class TestExpenseTreasury(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Cash = cls.env['treasury.cash']
        Closing = cls.env['treasury.cash.closing']
        Operation = cls.env['treasury.cash.operation']

        cls.cash = Cash.create({
            'name': 'Caisse Test Frais ADI',
            'code': 'TFA',
        })

        cls.category_in = cls.env.ref('adi_treasury.category_vente')
        cls.category_frais = cls.env.ref('adi_expenses_treasury.category_frais_adi')

        cls.depenses_categ = cls.env['depenses.categorie'].create({
            'name': 'Fournitures bureau',
        })

        cls.closing = Closing.create({
            'cash_id': cls.cash.id,
        })

        # Alimenter la caisse pour permettre les sorties
        cls.funding_op = Operation.create({
            'cash_id': cls.cash.id,
            'operation_type': 'in',
            'category_id': cls.category_in.id,
            'amount': 10000.0,
            'description': 'Fonds initiaux test',
            'state': 'posted',
        })

    def _make_expense(self, montant=150.0, partner=None):
        return self.env['depenses.depense'].create({
            'date': '2026-04-29',
            'montant': montant,
            'categorie': self.depenses_categ.id,
            'description': 'Fournitures de bureau du jour',
            'caisse_id': self.cash.id,
            'partner_id': partner.id if partner else False,
        })

    # ------------------------------------------------------------------
    def test_post_creates_treasury_operation(self):
        expense = self._make_expense(montant=150.0)
        self.assertEqual(expense.state, 'draft')
        self.assertFalse(expense.treasury_operation_id)

        expense.action_post()

        self.assertEqual(expense.state, 'posted')
        self.assertTrue(expense.treasury_operation_id)
        op = expense.treasury_operation_id
        self.assertEqual(op.state, 'posted')
        self.assertEqual(op.amount, 150.0)
        self.assertEqual(op.operation_type, 'out')
        self.assertEqual(op.cash_id, self.cash)
        self.assertEqual(op.category_id, self.category_frais)
        self.assertEqual(expense.treasury_closing_id, self.closing)

    # ------------------------------------------------------------------
    def test_post_without_closing_raises(self):
        self.closing.action_cancel()

        expense = self._make_expense(montant=50.0)
        with self.assertRaises(UserError):
            expense.action_post()

        self.assertEqual(expense.state, 'draft')
        self.assertFalse(expense.treasury_operation_id)

    # ------------------------------------------------------------------
    def test_cancel_before_validation_works(self):
        expense = self._make_expense(montant=80.0)
        expense.action_post()
        op = expense.treasury_operation_id
        self.assertEqual(op.state, 'posted')
        self.assertEqual(self.closing.state, 'draft')

        expense.action_cancel()

        self.assertEqual(expense.state, 'cancel')
        self.assertEqual(op.state, 'cancel')

    # ------------------------------------------------------------------
    def test_cancel_after_validation_raises(self):
        expense = self._make_expense(montant=120.0)
        expense.action_post()

        self.closing.action_confirm()
        self.closing.action_validate()
        self.assertEqual(self.closing.state, 'validated')

        with self.assertRaises(UserError):
            expense.action_cancel()
        self.assertEqual(expense.state, 'posted')

    # ------------------------------------------------------------------
    def test_unlink_posted_raises(self):
        expense = self._make_expense(montant=60.0)
        expense.action_post()
        with self.assertRaises(UserError):
            expense.unlink()

    # ------------------------------------------------------------------
    def test_draft_carry_forward(self):
        expense = self._make_expense(montant=40.0)
        self.assertEqual(expense.state, 'draft')

        self.closing.action_confirm()
        self.closing.action_validate()
        self.assertEqual(self.closing.state, 'validated')

        # Le frais reste draft
        self.assertEqual(expense.state, 'draft')
        self.assertFalse(expense.treasury_operation_id)

        # Une nouvelle clôture permet de le poster sur la session suivante
        new_closing = self.env['treasury.cash.closing'].create({
            'cash_id': self.cash.id,
        })
        expense.action_post()
        self.assertEqual(expense.state, 'posted')
        self.assertEqual(expense.treasury_operation_id.closing_id, new_closing)
