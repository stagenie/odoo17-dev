# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ========== Nouveaux Champs ==========
    allocation_line_ids = fields.One2many(
        'payment.allocation.line',
        'payment_id',
        string='Répartition des paiements',
        copy=False,
    )

    has_invoices = fields.Boolean(
        string='A des factures impayées',
        compute='_compute_has_invoices',
        store=False
    )

    total_allocated = fields.Monetary(
        string='Total alloué',
        compute='_compute_allocation_totals',
        store=True,
        currency_field='currency_id'
    )

    remaining_amount = fields.Monetary(
        string='Montant restant',
        compute='_compute_allocation_totals',
        store=True,
        currency_field='currency_id',
        help="Montant qui sera créé comme solde créditeur"
    )

    auto_allocate = fields.Boolean(
        string='Répartition automatique',
        default=True,
        help="Cocher pour répartir automatiquement le paiement sur les factures"
    )

    # ========== Computed Fields ==========
    @api.depends('partner_id', 'partner_type', 'company_id')
    def _compute_has_invoices(self):
        for payment in self:
            payment.has_invoices = bool(payment._get_unpaid_invoices())

    @api.depends('allocation_line_ids.allocated_amount', 'amount')
    def _compute_allocation_totals(self):
        for payment in self:
            total_allocated = sum(payment.allocation_line_ids.mapped('allocated_amount'))
            payment.total_allocated = total_allocated
            payment.remaining_amount = payment.amount - total_allocated

    # ========== Onchange Methods ==========
    @api.onchange('partner_id', 'partner_type')
    def _onchange_partner_id(self):
        """Charge les factures impayées dès la sélection du partenaire"""
        _logger.info(f"_onchange_partner_id called with partner_id={self.partner_id.id if self.partner_id else None}")

        # Vider d'abord toutes les lignes existantes
        self.allocation_line_ids = [(5, 0, 0)]

        if self.partner_id:
            self._prepare_allocation_lines_for_onchange()

    @api.onchange('amount')
    def _onchange_amount(self):
        """Recalcule uniquement la répartition quand le montant change"""
        if self.auto_allocate and self.partner_id and self.amount > 0:
            self._compute_allocation_amounts()

    # ========== Private Methods ==========
    def _get_unpaid_invoices(self):
        """Récupère toutes les factures impayées du partenaire"""
        self.ensure_one()
        if not self.partner_id:
            return self.env['account.move']

        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('company_id', '=', self.company_id.id),
        ]

        # Type de factures selon le type de paiement
        if self.partner_type == 'customer':
            domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
        else:  # supplier
            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))

        # Tri par date de facture (FIFO)
        invoices = self.env['account.move'].search(domain, order='invoice_date ASC, id ASC')

        _logger.info(f"Found {len(invoices)} unpaid invoices for partner {self.partner_id.name}")
        return invoices

    def _prepare_allocation_lines_for_onchange(self):
        """Prépare les lignes d'allocation pour un onchange (sans payment_id)"""
        self.ensure_one()

        invoices = self._get_unpaid_invoices()
        if not invoices:
            return

        # Dans un onchange, on utilise la syntaxe (0, 0, dict)
        lines_vals = []
        for invoice in invoices:
            if invoice and invoice.exists() and invoice.id:
                vals = {
                    'invoice_id': invoice.id,
                    'allocated_amount': 0.0,
                }
                lines_vals.append((0, 0, vals))
                _logger.info(f"Preparing line for invoice {invoice.name} (ID: {invoice.id})")

        if lines_vals:
            self.allocation_line_ids = lines_vals

    def _create_allocation_lines_after_save(self):
        """Crée les lignes d'allocation après la sauvegarde du paiement"""
        self.ensure_one()

        if not self.partner_id or not self.id:
            return

        # Supprimer les lignes existantes non lettrées
        self.allocation_line_ids.filtered(lambda l: l.state == 'draft').unlink()

        invoices = self._get_unpaid_invoices()
        if not invoices:
            return

        # Créer les lignes avec payment_id
        for invoice in invoices:
            if invoice and invoice.exists() and invoice.id:
                try:
                    self.env['payment.allocation.line'].create({
                        'payment_id': self.id,
                        'invoice_id': invoice.id,
                        'allocated_amount': 0.0,
                    })
                    _logger.info(f"Created allocation line for invoice {invoice.name}")
                except Exception as e:
                    _logger.error(f"Error creating allocation line: {str(e)}")

    def _compute_allocation_amounts(self):
        """Calcule uniquement les montants alloués sans toucher aux factures"""
        try:
            if not self.allocation_line_ids or self.amount <= 0:
                # Remise à zéro des montants alloués
                for line in self.allocation_line_ids:
                    line.allocated_amount = 0.0
                return

            remaining_amount = self.amount

            # Répartition sur les lignes existantes
            for line in self.allocation_line_ids:
                if remaining_amount <= 0:
                    line.allocated_amount = 0.0
                    continue

                # S'assurer qu'on a bien l'invoice_id
                if line.invoice_id:
                    # Montant à allouer = minimum entre le restant dû et le montant disponible
                    amount_to_allocate = min(line.invoice_id.amount_residual, remaining_amount)
                    line.allocated_amount = amount_to_allocate
                    remaining_amount -= amount_to_allocate
                else:
                    line.allocated_amount = 0.0

        except Exception as e:
            _logger.error(f"Erreur lors du calcul de la répartition: {str(e)}")

    # ========== Override Methods ==========
    @api.model_create_multi
    def create(self, vals_list):
        """Override pour gérer la création avec les allocations"""
        payments = super().create(vals_list)

        for payment in payments:
            if payment.partner_id:
                payment._create_allocation_lines_after_save()
                if payment.amount > 0 and payment.auto_allocate:
                    payment._compute_allocation_amounts()

        return payments

    def write(self, vals):
        """Override pour gérer les modifications"""
        # Si on change le partenaire
        if 'partner_id' in vals or 'partner_type' in vals:
            res = super().write(vals)

            # Recréer les lignes pour les paiements en brouillon
            for payment in self:
                if payment.state == 'draft' and payment.partner_id:
                    payment._create_allocation_lines_after_save()
                    if payment.amount > 0 and payment.auto_allocate:
                        payment._compute_allocation_amounts()
            return res

        # Si on change le montant
        elif 'amount' in vals:
            res = super().write(vals)
            for payment in self:
                if payment.state == 'draft' and payment.auto_allocate:
                    payment._compute_allocation_amounts()
            return res
        else:
            return super().write(vals)

    def action_post(self):
        """Override pour gérer la répartition automatique lors de la validation"""
        res = super().action_post()

        for payment in self:
            if payment.auto_allocate and payment.allocation_line_ids:
                payment._process_allocation()

        return res

    def action_draft(self):
        """Override pour annuler les allocations lors du retour en brouillon"""
        for payment in self:
            payment._cancel_allocation()

        return super().action_draft()

    def action_cancel(self):
        """Override pour annuler les allocations lors de l'annulation"""
        for payment in self:
            payment._cancel_allocation()

        return super().action_cancel()

    def unlink(self):
        """Override pour nettoyer les allocations avant suppression"""
        # Vérifier d'abord qu'on peut supprimer les paiements
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_("Vous ne pouvez supprimer que des paiements en brouillon."))

        # Suppression des allocations en premier
        self.mapped('allocation_line_ids').unlink()

        # Ensuite supprimer les paiements
        return super().unlink()

    # ========== Business Methods ==========
    def _process_allocation(self):
        """Traite la répartition et crée les écritures de lettrage"""
        self.ensure_one()

        if not self.allocation_line_ids:
            return

        # Récupération du compte approprié
        if self.partner_type == 'customer':
            account = self.partner_id.property_account_receivable_id
        else:
            account = self.partner_id.property_account_payable_id

        # Récupération des écritures du paiement
        payment_move_line = self.line_ids.filtered(
            lambda l: l.account_id == account and not l.reconciled
        )

        if not payment_move_line:
            raise UserError(_("Impossible de trouver l'écriture de paiement à lettrer."))

        # Lettrage avec chaque facture selon l'allocation
        for allocation in self.allocation_line_ids:
            if allocation.allocated_amount <= 0:
                continue

            invoice = allocation.invoice_id

            # Recherche de la ligne à lettrer dans la facture
            invoice_move_line = invoice.line_ids.filtered(
                lambda l: l.account_id == account and not l.reconciled
            )

            if invoice_move_line:
                # Lettrage partiel ou total
                try:
                    (payment_move_line + invoice_move_line).reconcile()
                    # Mise à jour du statut de l'allocation
                    allocation.write({'state': 'reconciled'})
                except Exception as e:
                    _logger.error(f"Erreur lors du lettrage: {str(e)}")

        # Gestion du surplus si nécessaire
        if self.remaining_amount > 0:
            self._create_payment_surplus_move()

    def _cancel_allocation(self):
        """Annule toutes les allocations et délettrage les écritures"""
        self.ensure_one()

        for allocation in self.allocation_line_ids.filtered(lambda a: a.state == 'reconciled'):
            try:
                # Recherche des écritures lettrées
                reconciled_lines = self.line_ids.filtered(lambda l: l.reconciled)

                # Délettrage
                if reconciled_lines:
                    reconciled_lines.remove_move_reconcile()

                # Mise à jour du statut
                allocation.write({'state': 'cancelled'})
            except Exception as e:
                _logger.error(f"Erreur lors de l'annulation du lettrage: {str(e)}")

    def action_compute_allocation(self):
        """Action manuelle pour recalculer la répartition"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("La répartition ne peut être recalculée que sur un paiement en brouillon."))

        self._compute_allocation_amounts()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Répartition calculée'),
                'message': _('La répartition a été recalculée avec succès.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_allocated_invoices(self):
        """Action pour voir les factures allouées"""
        self.ensure_one()

        invoice_ids = self.allocation_line_ids.mapped('invoice_id').ids

        action = {
            'name': _('Factures allouées'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoice_ids)],
            'context': dict(self.env.context),
        }

        if len(invoice_ids) == 1:
            action.update({
                'res_id': invoice_ids[0],
                'view_mode': 'form',
            })

        return action

    def _create_payment_surplus_move(self):
        """Crée l'écriture comptable pour le surplus (solde créditeur)"""
        self.ensure_one()

        if self.remaining_amount <= 0:
            return

        # Création de l'écriture pour le surplus
        move_vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'ref': _('Surplus paiement %s') % self.name,
        }

        # Détermination du compte
        if self.partner_type == 'customer':
            account = self.partner_id.property_account_receivable_id
        else:
            account = self.partner_id.property_account_payable_id

        # Lignes d'écriture
        line_vals = [
            {
                'account_id': self.journal_id.default_account_id.id,
                'debit': self.remaining_amount if self.partner_type == 'supplier' else 0,
                'credit': self.remaining_amount if self.partner_type == 'customer' else 0,
                'partner_id': self.partner_id.id,
                'name': _('Surplus - %s') % (self.ref or self.name),  # Utiliser ref au lieu de communication
            },
            {
                'account_id': account.id,
                'debit': self.remaining_amount if self.partner_type == 'customer' else 0,
                'credit': self.remaining_amount if self.partner_type == 'supplier' else 0,
                'partner_id': self.partner_id.id,
                'name': _('Surplus créditeur - %s') % (self.ref or self.name),  # Utiliser ref au lieu de communication
            }
        ]

        move_vals['line_ids'] = [(0, 0, line) for line in line_vals]

        # Création et validation
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        return move

