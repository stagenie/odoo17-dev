# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleAvoirClient(models.Model):
    _inherit = 'gecafle.avoir.client'

    # Champ pour tracer si l'avoir est lié à une facture protégée
    is_from_protected_invoice = fields.Boolean(
        string="Provient d'une facture protégée",
        compute='_compute_is_from_protected',
        store=True
    )

    @api.depends('vente_id', 'vente_id.invoice_id')
    def _compute_is_from_protected(self):
        """Détermine si l'avoir est lié à une facture protégée GECAFLE"""
        for avoir in self:
            if avoir.vente_id and avoir.vente_id.invoice_id:
                # Vérifier si la facture a le champ is_protected_gecafle
                if hasattr(avoir.vente_id.invoice_id, 'is_protected_gecafle'):
                    avoir.is_from_protected_invoice = avoir.vente_id.invoice_id.is_protected_gecafle
                else:
                    avoir.is_from_protected_invoice = False
            else:
                avoir.is_from_protected_invoice = False

    def unlink(self):
        """Override pour permettre la suppression des avoirs sous conditions"""
        for avoir in self:
            # Si l'avoir est lié à une facture GECAFLE protégée
            if avoir.is_from_protected_invoice:
                # Vérifier les conditions pour permettre la suppression
                if avoir.state not in ['brouillon', 'annule']:
                    raise UserError(_(
                        "Impossible de supprimer l'avoir %s car il n'est pas en brouillon ou annulé.\n"
                        "Vous devez d'abord annuler cet avoir."
                    ) % avoir.name)

                # Si l'avoir a une note de crédit comptabilisée
                if avoir.credit_note_id and avoir.credit_note_id.state == 'posted':
                    raise UserError(_(
                        "Impossible de supprimer l'avoir %s car la note de crédit associée est comptabilisée.\n"
                        "Annulez d'abord la note de crédit."
                    ) % avoir.name)

        return super().unlink()

    def action_cancel(self):
        """Permet l'annulation d'un avoir"""
        for avoir in self:
            if avoir.state == 'annule':
                continue

            # Si une note de crédit existe et est comptabilisée
            if avoir.credit_note_id and avoir.credit_note_id.state == 'posted':
                # Proposer d'annuler la note de crédit
                if self._context.get('force_cancel_credit_note'):
                    avoir.credit_note_id.button_cancel()
                else:
                    raise UserError(_(
                        "L'avoir %s a une note de crédit comptabilisée.\n"
                        "Voulez-vous annuler la note de crédit également ?\n\n"
                        "Si oui, utilisez l'action 'Forcer l'annulation'."
                    ) % avoir.name)

            # Mettre l'avoir en état annulé
            avoir.state = 'annule'

            # Logger l'action
            avoir.message_post(
                body=_("Avoir annulé par %s") % self.env.user.name,
                message_type='notification'
            )

    def action_force_cancel(self):
        """Force l'annulation avec la note de crédit"""
        return self.with_context(force_cancel_credit_note=True).action_cancel()
