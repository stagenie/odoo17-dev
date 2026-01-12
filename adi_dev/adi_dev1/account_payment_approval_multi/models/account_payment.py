# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_approve_multi(self):
        """Approuver plusieurs paiements à la fois.
        Seul l'utilisateur ayant les droits d'approbation peut effectuer cette action.
        """
        # Vérifier si l'utilisateur est l'approbateur
        approval = self.env['ir.config_parameter'].sudo().get_param(
            'account_payment_approval.payment_approval')
        approver_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'account_payment_approval.approval_user_id') or 0)

        if not approval or self.env.user.id != approver_id:
            raise UserError(_("Vous n'avez pas les droits pour approuver les paiements."))

        # Filtrer les paiements en attente d'approbation
        payments_to_approve = self.filtered(lambda p: p.state == 'waiting_approval')

        if not payments_to_approve:
            raise UserError(_("Aucun paiement en attente d'approbation dans la sélection."))

        # Approuver et poster les paiements
        payments_to_approve.write({'state': 'approved'})

        # Poster automatiquement les paiements approuvés pour assigner les numéros
        for payment in payments_to_approve:
            payment.action_post()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Paiements Approuvés'),
                'message': _('%d paiement(s) approuvé(s) et posté(s) avec succès.') % len(payments_to_approve),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_reject_multi(self):
        """Rejeter plusieurs paiements à la fois.
        Seul l'utilisateur ayant les droits d'approbation peut effectuer cette action.
        """
        # Vérifier si l'utilisateur est l'approbateur
        approval = self.env['ir.config_parameter'].sudo().get_param(
            'account_payment_approval.payment_approval')
        approver_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'account_payment_approval.approval_user_id') or 0)

        if not approval or self.env.user.id != approver_id:
            raise UserError(_("Vous n'avez pas les droits pour rejeter les paiements."))

        # Filtrer les paiements en attente d'approbation
        payments_to_reject = self.filtered(lambda p: p.state == 'waiting_approval')

        if not payments_to_reject:
            raise UserError(_("Aucun paiement en attente d'approbation dans la sélection."))

        # Rejeter les paiements
        payments_to_reject.write({'state': 'rejected'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Paiements Rejetés'),
                'message': _('%d paiement(s) rejeté(s).') % len(payments_to_reject),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
