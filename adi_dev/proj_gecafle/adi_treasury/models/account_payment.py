# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Champ related pour le type de journal
    journal_type = fields.Selection(
        related='journal_id.type',
        string='Type de journal',
        readonly=True
    )

    treasury_operation_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération de caisse',
        readonly=True
    )

    # Nouveau champ pour marquer manuellement
    is_cash_collected = fields.Boolean(
        string='Prélevé en caisse',
        default=False,
        help="Cocher si ce paiement a été collecté/déboursé en caisse"
    )

    cash_id = fields.Many2one(
        'treasury.cash',
        string='Caisse',
        domain="[('state', '=', 'open')]",
        help="Caisse concernée par ce paiement"
    )

    def action_post(self):
        """Override pour créer automatiquement une opération de caisse"""
        res = super().action_post()

        for payment in self:
            # IMPORTANT : Vérifier qu'il n'y a pas déjà une opération
            if payment.treasury_operation_id:
                continue

            # Créer une opération UNIQUEMENT si :
            # 1. Le journal est de type 'cash'
            # 2. Il n'y a pas déjà une opération liée
            if payment.journal_id.type == 'cash':
                # Chercher la caisse associée au journal
                cash = self.env['treasury.cash'].search([
                    ('journal_id', '=', payment.journal_id.id),
                    ('state', '=', 'open')
                ], limit=1)

                if cash:
                    # Vérifier qu'une clôture est en cours pour cette caisse
                    pending_closing = self.env['treasury.cash.closing'].search([
                        ('cash_id', '=', cash.id),
                        ('state', 'in', ['draft', 'confirmed'])
                    ], limit=1)

                    if not pending_closing:
                        # Pas de clôture en cours, ne pas créer l'opération
                        # Ou créer une notification
                        payment.message_post(
                            body=_(
                                "⚠️ Aucune clôture en cours pour la caisse %s. L'opération de caisse n'a pas été créée.") % cash.name
                        )
                        continue

                    # Déterminer le type et la catégorie
                    if payment.payment_type == 'inbound':
                        if payment.partner_type == 'customer':
                            operation_type = 'in'
                            category = self.env['treasury.operation.category'].search([
                                ('is_customer_payment', '=', True)
                            ], limit=1)
                        else:  # supplier refund
                            operation_type = 'in'
                            category = self.env['treasury.operation.category'].search([
                                ('code', '=', 'REFUND_SUPPLIER')
                            ], limit=1)
                    else:  # outbound
                        if payment.partner_type == 'supplier':
                            operation_type = 'out'
                            category = self.env['treasury.operation.category'].search([
                                ('is_vendor_payment', '=', True)
                            ], limit=1)
                        else:  # customer refund
                            operation_type = 'out'
                            category = self.env['treasury.operation.category'].search([
                                ('code', '=', 'REFUND_CUSTOMER')
                            ], limit=1)

                    if category:
                        # Créer l'opération de caisse
                        operation_vals = {
                            'cash_id': cash.id,
                            'operation_type': operation_type,
                            'category_id': category.id,
                            'amount': payment.amount,
                            'date': fields.Datetime.to_datetime(payment.date),
                            'partner_id': payment.partner_id.id,
                            'description': _("Paiement %s - %s (%s %s)") % (
                                payment.name,
                                payment.partner_id.name or 'N/A',
                                dict(payment._fields['payment_type'].selection).get(payment.payment_type, ''),
                                dict(payment._fields['partner_type'].selection).get(payment.partner_type, '')
                            ),
                            'reference': payment.name,
                            'payment_id': payment.id,
                            'closing_id': pending_closing.id,  # Assigner directement à la clôture
                        }

                        operation = self.env['treasury.cash.operation'].create(operation_vals)

                        # Comptabiliser automatiquement
                        operation.action_post()

                        # Lier l'opération au paiement
                        payment.treasury_operation_id = operation

                        # Message de confirmation
                        payment.message_post(
                            body=_("✓ Opération de caisse créée : %s") % operation.name
                        )

        return res

    def action_cancel(self):
        """Override pour annuler l'opération de caisse associée"""
        res = super().action_cancel()

        for payment in self:
            if payment.treasury_operation_id and payment.treasury_operation_id.state == 'posted':
                # Vérifier si l'opération n'est pas déjà dans une clôture validée
                if payment.treasury_operation_id.closing_id and payment.treasury_operation_id.closing_id.state == 'validated':
                    raise UserError(
                        _("Impossible d'annuler ce paiement car l'opération de caisse associée "
                          "fait partie de la clôture validée '%s'.") % payment.treasury_operation_id.closing_id.name
                    )
                payment.treasury_operation_id.action_cancel()

        return res

    def action_draft(self):
        """Override pour empêcher la mise en brouillon si l'opération est dans une clôture"""
        for payment in self:
            if payment.treasury_operation_id:
                # Vérifier si l'opération est dans une clôture
                if payment.treasury_operation_id.closing_id:
                    closing = payment.treasury_operation_id.closing_id

                    # Empêcher si la clôture est validée
                    if closing.state == 'validated':
                        raise UserError(
                            _("Impossible de remettre ce paiement en brouillon car l'opération de caisse associée "
                              "fait partie de la clôture validée '%s'.") % closing.name
                        )

                    # Empêcher aussi si la clôture est confirmée
                    elif closing.state == 'confirmed':
                        raise UserError(
                            _("Impossible de remettre ce paiement en brouillon car l'opération de caisse associée "
                              "fait partie de la clôture confirmée '%s'.\n"
                              "Veuillez d'abord remettre la clôture en brouillon.") % closing.name
                        )

                    # Avertir si la clôture est en brouillon
                    elif closing.state == 'draft':
                        # Message d'avertissement dans le chatter
                        payment.message_post(
                            body=_(
                                "⚠️ Attention : Ce paiement est lié à la clôture de caisse '%s' en brouillon.") % closing.name
                        )

        # Appeler la méthode parent
        res = super().action_draft()

        # Si tout s'est bien passé, mettre à jour l'opération de caisse
        for payment in self:
            if payment.treasury_operation_id and payment.treasury_operation_id.state == 'posted':
                # Remettre l'opération en brouillon aussi
                payment.treasury_operation_id.write({'state': 'draft'})
                payment.treasury_operation_id.message_post(
                    body=_("Opération remise en brouillon suite à la modification du paiement %s") % payment.name
                )

        return res

    def action_mark_cash_collected(self):
        """Marquer le paiement comme prélevé en caisse"""
        for payment in self:
            if payment.state == 'posted' and not payment.treasury_operation_id:
                payment.is_cash_collected = True
                # Créer l'opération de caisse
                payment.with_context(force_cash_operation=True).action_post()
