# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class PaymentAllocationLine(models.Model):
    _name = 'payment.allocation.line'
    _description = 'Ligne de répartition de paiement'
    _order = 'invoice_date ASC, id ASC'

    # ========== Champs de Base ==========
    payment_id = fields.Many2one(
        'account.payment',
        string='Paiement',
        required=False,  # IMPORTANT: Mettre à False
        ondelete='cascade',
        index=True
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=False,  # TEMPORAIREMENT False pour debug
        ondelete='cascade',
        domain="[('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]"
    )

    allocated_amount = fields.Monetary(
        string='Montant alloué',
        required=True,
        default=0.0,
        currency_field='currency_id'
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('reconciled', 'Lettré'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft', required=True)

    # ========== Champs Relationnels ==========
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        compute='_compute_currency_id',
        store=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        compute='_compute_partner_id',
        store=True
    )

    # ========== Champs de la Facture ==========
    invoice_date = fields.Date(
        related='invoice_id.invoice_date',
        string='Date facture',
        store=True
    )

    invoice_date_due = fields.Date(
        related='invoice_id.invoice_date_due',
        string='Date échéance',
        store=True
    )

    invoice_amount_total = fields.Monetary(
        related='invoice_id.amount_total',
        string='Montant total facture',
        currency_field='currency_id'
    )

    invoice_amount_residual_before = fields.Monetary(
        string='Montant dû',
        compute='_compute_amounts',
        currency_field='currency_id',
        help="Montant restant dû sur la facture avant ce paiement"
    )

    invoice_amount_residual_after = fields.Monetary(
        string='Restera dû',
        compute='_compute_amounts',
        currency_field='currency_id',
        help="Montant restant dû sur la facture après ce paiement"
    )

    amount_already_paid = fields.Monetary(
        string='Déjà payé',
        compute='_compute_amounts',
        currency_field='currency_id',
        help="Montant déjà payé sur cette facture"
    )

    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='État paiement',
        store=True
    )

    is_overdue = fields.Boolean(
        string='Échue',
        compute='_compute_is_overdue',
        help="Indique si la facture est échue"
    )

    # ========== Computed Methods ==========
    @api.depends('payment_id', 'invoice_id')
    def _compute_currency_id(self):
        """Calcule la devise depuis le paiement ou la facture"""
        for record in self:
            if record.payment_id and record.payment_id.currency_id:
                record.currency_id = record.payment_id.currency_id
            elif record.invoice_id and record.invoice_id.currency_id:
                record.currency_id = record.invoice_id.currency_id
            else:
                record.currency_id = self.env.company.currency_id

    @api.depends('payment_id', 'invoice_id')
    def _compute_partner_id(self):
        """Calcule le partenaire depuis le paiement ou la facture"""
        for record in self:
            if record.payment_id and record.payment_id.partner_id:
                record.partner_id = record.payment_id.partner_id
            elif record.invoice_id and record.invoice_id.partner_id:
                record.partner_id = record.invoice_id.partner_id
            else:
                record.partner_id = False

    @api.depends('invoice_id', 'allocated_amount')
    def _compute_amounts(self):
        for line in self:
            if line.invoice_id:
                line.invoice_amount_residual_before = line.invoice_id.amount_residual
                line.invoice_amount_residual_after = max(0, line.invoice_id.amount_residual - line.allocated_amount)
                line.amount_already_paid = line.invoice_id.amount_total - line.invoice_id.amount_residual
            else:
                line.invoice_amount_residual_before = 0
                line.invoice_amount_residual_after = 0
                line.amount_already_paid = 0

    @api.depends('invoice_date_due')
    def _compute_is_overdue(self):
        today = date.today()
        for line in self:
            line.is_overdue = bool(line.invoice_date_due and line.invoice_date_due < today)

    # ========== Constraints ==========
    @api.constrains('invoice_id')
    def _check_invoice_id(self):
        """Vérifier que invoice_id est défini pour les lignes sauvegardées"""
        for record in self:
            # Ne vérifier que si l'enregistrement a un ID (est sauvegardé)
            if record.id and not record.invoice_id:
                raise ValidationError(_("Une facture doit être sélectionnée pour la ligne d'allocation."))

    @api.constrains('payment_id', 'state')
    def _check_payment_id(self):
        """Vérifier que payment_id est défini pour les lignes non-brouillon"""
        for record in self:
            if record.state != 'draft' and not record.payment_id:
                raise ValidationError(_("Un paiement doit être défini pour valider la ligne d'allocation."))

    # ========== CRUD Methods ==========
    @api.model_create_multi
    def create(self, vals_list):
        """Override pour logging et validation"""
        for vals in vals_list:
            _logger.info(f"Creating allocation line with values: {vals}")
            if not vals.get('invoice_id'):
                _logger.warning("Tentative de création d'une ligne sans invoice_id")

        return super().create(vals_list)

    def write(self, vals):
        """Override pour empêcher la modification de certains champs"""
        if self.filtered(lambda r: r.state == 'reconciled'):
            if any(field in vals for field in ['invoice_id', 'allocated_amount', 'payment_id']):
                raise ValidationError(_("Impossible de modifier une allocation lettrée."))
        return super().write(vals)

    # ========== Business Methods ==========
    def action_view_invoice(self):
        """Ouvre la vue formulaire de la facture"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    is_fully_paid = fields.Boolean(
        string='Payée',
        compute='_compute_is_fully_paid',
        store=True,
        help="Indique si la facture sera totalement payée après cette allocation"
    )

    # ========== Computed Methods ==========
    # [Méthodes existantes...]

    @api.depends('invoice_amount_residual_after', 'allocated_amount')
    def _compute_is_fully_paid(self):
        """Calcule si la facture sera totalement payée après cette allocation"""
        for line in self:
            # La facture est considérée comme totalement payée si :
            # 1. Le montant restant dû après allocation est 0
            # 2. ET qu'on a alloué quelque chose
            line.is_fully_paid = (
                    line.invoice_amount_residual_after == 0 and
                    line.allocated_amount > 0
            )

