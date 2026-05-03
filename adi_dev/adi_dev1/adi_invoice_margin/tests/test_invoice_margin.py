# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.fields import Command


class TestInvoiceMargin(TransactionCase):
    """Unit tests for adi_invoice_margin.

    Each test is tagged so it can be run in isolation:
      --test-tags adi_invoice_margin
    """

    _test_tags = ('adi_invoice_margin',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Minimal chart of accounts — use the first available journal.
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        company = cls.env.company

        # Revenue account for invoice lines.
        cls.account_revenue = cls.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'income'),
            ('deprecated', '=', False),
        ], limit=1)
        if not cls.account_revenue:
            cls.account_revenue = cls.env['account.account'].create({
                'name': 'Test Revenue',
                'code': 'TEST_REV',
                'account_type': 'income',
                'company_id': company.id,
            })

        # Partner.
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner Margin'})

        # Product with known cost and sale price.
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Margin',
            'type': 'service',
            'standard_price': 10.0,
            'list_price': 15.0,
        })

        # Sales journal.
        cls.journal = cls.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'sale'),
        ], limit=1)

    def _make_invoice(self, move_type='out_invoice', qty=1.0, price_unit=15.0, product=None):
        """Helper: create and post an invoice of the given type."""
        product = product or self.product
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': product.name,
                'quantity': qty,
                'price_unit': price_unit,
                'account_id': self.account_revenue.id,
            })],
        })
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Test 1: basic margin on a customer invoice
    # ------------------------------------------------------------------
    def test_invoice_margin_basic(self):
        """A posted customer invoice must show correct margin and percent.

        Convention « marge sur coût » :
            product cost = 10, sale price = 15, qty = 1
            margin = 15 - 10 = 5
            margin_percent = 5 / 10 = 0.5  (50 %)
        """
        move = self._make_invoice(move_type='out_invoice', qty=1.0, price_unit=15.0)
        line = move.invoice_line_ids[0]

        self.assertAlmostEqual(line.purchase_price, 10.0, places=4,
                               msg='purchase_price should equal standard_price')
        self.assertAlmostEqual(line.margin, 5.0, places=4,
                               msg='line margin should be price_subtotal - cost * qty')
        self.assertAlmostEqual(line.margin_percent, 50.0, places=4,
                               msg='margin_percent = (5/10) * 100 = 50.0 (sur coût)')

        self.assertAlmostEqual(move.margin, 5.0, places=4,
                               msg='move margin = sum of line margins')
        self.assertAlmostEqual(move.margin_percent, 50.0, places=4,
                               msg='move margin_percent = (margin / total_cost) * 100')

    # ------------------------------------------------------------------
    # Test 2: refund shows negative margin
    # ------------------------------------------------------------------
    def test_refund_margin_negative(self):
        """A customer credit note must show a negative margin contribution.

        Same product (cost=10, price=15, qty=1): the refund reverses the sale
        so margin must be -5 (revenue lost).
        """
        move = self._make_invoice(move_type='out_refund', qty=1.0, price_unit=15.0)
        line = move.invoice_line_ids[0]

        self.assertAlmostEqual(line.margin, -5.0, places=4,
                               msg='refund line margin should be negative (revenue lost)')
        self.assertAlmostEqual(line.margin_percent, -50.0, places=4,
                               msg='refund margin_percent = (-5/10) * 100 = -50.0')

        self.assertAlmostEqual(move.margin, -5.0, places=4,
                               msg='move margin should be negative for credit note')

    # ------------------------------------------------------------------
    # Test 3: invoice line without product → margin must be zero
    # ------------------------------------------------------------------
    def test_invoice_no_product_zero_margin(self):
        """An invoice line with no product must have margin = 0."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [Command.create({
                'name': 'Service sans produit',
                'quantity': 1.0,
                'price_unit': 100.0,
                'account_id': self.account_revenue.id,
                # No product_id intentionally.
            })],
        })
        move.action_post()
        line = move.invoice_line_ids[0]

        self.assertEqual(line.purchase_price, 0.0,
                         'purchase_price must be 0 when no product')
        self.assertEqual(line.margin, 0.0,
                         'margin must be 0 when purchase_price is 0 and product absent')

    # ------------------------------------------------------------------
    # Test 4: aggregate margin across multiple lines
    # ------------------------------------------------------------------
    def test_aggregate_margin_on_move(self):
        """Two lines on the same invoice: move.margin = sum of line margins."""
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'service',
            'standard_price': 20.0,
            'list_price': 30.0,
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'quantity': 2.0,
                    'price_unit': 15.0,   # subtotal=30, cost=10*2=20 → margin=10
                    'account_id': self.account_revenue.id,
                }),
                Command.create({
                    'product_id': product2.id,
                    'name': product2.name,
                    'quantity': 1.0,
                    'price_unit': 30.0,   # subtotal=30, cost=20*1=20 → margin=10
                    'account_id': self.account_revenue.id,
                }),
            ],
        })
        move.action_post()

        line1, line2 = move.invoice_line_ids

        self.assertAlmostEqual(line1.margin, 10.0, places=4)
        self.assertAlmostEqual(line2.margin, 10.0, places=4)
        self.assertAlmostEqual(move.margin, 20.0, places=4,
                               msg='move margin = 10 + 10 = 20')
        # cost_total = 10*2 + 20*1 = 40 → margin_percent = (20/40)*100 = 50.0
        self.assertAlmostEqual(move.margin_percent, 50.0, places=4)

    # ------------------------------------------------------------------
    # Test 5: vendor bill must have zero margin (not a customer move type)
    # ------------------------------------------------------------------
    def test_non_customer_move_zero(self):
        """A vendor bill (in_invoice) must never compute margin."""
        # Find or create a purchase journal.
        purchase_journal = self.env['account.journal'].search([
            ('company_id', '=', self.env.company.id),
            ('type', '=', 'purchase'),
        ], limit=1)

        expense_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('account_type', '=', 'expense'),
            ('deprecated', '=', False),
        ], limit=1)
        if not expense_account:
            expense_account = self.env['account.account'].create({
                'name': 'Test Expense',
                'code': 'TEST_EXP',
                'account_type': 'expense',
                'company_id': self.env.company.id,
            })

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': purchase_journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'price_unit': 15.0,
                'account_id': expense_account.id,
            })],
        })
        move.action_post()
        line = move.invoice_line_ids[0]

        self.assertEqual(line.purchase_price, 0.0,
                         'purchase_price must be 0 on vendor bills')
        self.assertEqual(line.margin, 0.0,
                         'margin must be 0 on vendor bills')
        self.assertEqual(move.margin, 0.0,
                         'move.margin must be 0 on vendor bills')
