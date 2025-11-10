# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_protected_gecafle = fields.Boolean(
        string="Facture protégée GECAFLE",
        compute='_compute_is_protected',
        store=True
    )

    @api.depends('gecafle_vente_id')
    def _compute_is_protected(self):
        """Marque comme protégée si liée à une vente GECAFLE"""
        for move in self:
            move.is_protected_gecafle = bool(move.gecafle_vente_id)

    def write(self, vals):
        """Override pour empêcher la modification des factures GECAFLE"""
        for move in self:
            if move.is_protected_gecafle and move.state == 'posted':
                # Champs métier interdits (ceux qu'on veut vraiment protéger)
                protected_business_fields = {
                    'partner_id', 'invoice_line_ids', 'amount_total',
                    'invoice_date', 'ref', 'narration', 'invoice_origin',
                    'fiscal_position_id', 'journal_id', 'currency_id'
                }

                # Champs techniques toujours autorisés
                technical_allowed_fields = {
                    # Paiements
                    'payment_state', 'amount_residual', 'amount_residual_signed',
                    'payment_reference',
                    # Attachements et accès
                    'message_main_attachment_id', 'access_token',
                    # Termes de paiement et échéances (Odoo 17)
                    'needed_terms_dirty', 'needed_terms', 'invoice_payment_term_id',
                    'invoice_date_due', 'show_payment_term_details', 'payment_term_details',
                    # Autres champs techniques
                    'invoice_has_outstanding', 'has_reconciled_entries',
                    'restrict_mode_hash_table', 'secure_sequence_number',
                    # Champs de workflow
                    'activity_ids', 'message_ids', 'message_follower_ids'
                }

                # Vérifier si on modifie des champs protégés
                modified_protected_fields = set(vals.keys()) & protected_business_fields

                if modified_protected_fields and not self.env.context.get('force_gecafle_update'):
                    raise UserError(_(
                        "Les factures générées depuis les ventes GECAFLE ne peuvent pas être modifiées.\n"
                        "Champs protégés modifiés : %s\n\n"
                        "Utilisez la fonction de remise en brouillon de la vente pour modifier."
                    ) % ', '.join(modified_protected_fields))

        return super().write(vals)

    payment_count = fields.Integer(
        string="Nombre de paiements",
        compute='_compute_payment_info_smart'
    )

    has_payments = fields.Boolean(
        string="A des paiements",
        compute='_compute_payment_info_smart'
    )

    payment_ids_smart = fields.Many2many(
        'account.payment',
        string="Paiements",
        compute='_compute_payment_info_smart'
    )

    @api.depends('payment_state', 'line_ids')
    def _compute_payment_info_smart(self):
        """Calcule les informations de paiement pour le bouton intelligent"""
        for move in self:
            try:
                # Récupérer tous les paiements liés
                payments = move._get_reconciled_payments()
                # Vérifier que les paiements existent encore
                existing_payments = payments.exists() if payments else self.env['account.payment']

                move.payment_ids_smart = existing_payments
                move.payment_count = len(existing_payments)
                move.has_payments = bool(existing_payments)

            except Exception as e:
               # _logger.warning(f"Erreur lors du calcul des paiements pour {move.name}: {str(e)}")
                move.payment_ids_smart = False
                move.payment_count = 0
                move.has_payments = False

    def action_view_payments_smart(self):
        """Action pour afficher les paiements liés à la facture"""
        self.ensure_one()

        if not self.has_payments:
            raise UserError(_("Aucun paiement n'est lié à cette facture."))

        payments = self.payment_ids_smart

        # Si un seul paiement, l'ouvrir directement
        if len(payments) == 1:
            return {
                'name': _('Paiement'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'res_id': payments[0].id,
                'target': 'current',
                'context': {'create': False}
            }
        else:
            # Sinon, ouvrir la liste des paiements
            return {
                'name': _('Paiements de la facture %s') % self.name,
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'account.payment',
                'domain': [('id', 'in', payments.ids)],
                'target': 'current',
                'context': {
                    'create': False,
                    'default_partner_id': self.partner_id.id,
                    'default_move_id': self.id,
                }
            }

    def button_draft(self):
        """Override pour empêcher la remise en brouillon des factures GECAFLE"""
        for move in self:
            if move.is_protected_gecafle and not self.env.context.get('force_gecafle_update'):
                raise UserError(_(
                    "Cette facture a été générée depuis une vente GECAFLE et ne peut pas être remise en brouillon.\n\n"
                    "Pour modifier cette facture, utilisez la fonction 'Remise en brouillon' "
                    "depuis la vente d'origine."
                ))

        return super().button_draft()

    def button_cancel(self):
        """Override pour protéger l'annulation des factures GECAFLE"""
        for move in self:
            if move.is_protected_gecafle and not self.env.context.get('force_gecafle_update'):
                raise UserError(_(
                    "Cette facture a été générée depuis une vente GECAFLE et ne peut pas être annulée directement.\n\n"
                    "Pour annuler cette facture, utilisez les fonctions disponibles "
                    "depuis la vente d'origine."
                ))

        return super().button_cancel()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Override pour empêcher la création d'avoirs sur les factures GECAFLE"""
        for move in self:
            if move.is_protected_gecafle and not self.env.context.get('force_gecafle_update'):
                raise UserError(_(
                    "Impossible de créer un avoir pour cette facture GECAFLE.\n\n"
                    "Les avoirs doivent être créés depuis le module de gestion des ventes GECAFLE.\n"
                    "Utilisez les fonctions d'avoir disponibles dans le bon de vente."
                ))

        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def action_reverse(self):
        """Override pour bloquer l'assistant de création d'avoir"""
        for move in self:
            if move.is_protected_gecafle:
                raise UserError(_(
                    "Création d'avoir non autorisée\n\n"
                    "Cette facture est liée à un bon de vente GECAFLE.\n"
                    "Les avoirs doivent être créés depuis le module GECAFLE.\n\n"
                    "Allez dans le bon de vente %s et utilisez les fonctions d'avoir disponibles."
                ) % (move.gecafle_vente_id.name if move.gecafle_vente_id else ''))

        return super().action_reverse()
