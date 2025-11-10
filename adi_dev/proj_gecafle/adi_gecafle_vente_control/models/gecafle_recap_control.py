# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleReceptionRecapControl(models.Model):
    _inherit = 'gecafle.reception.recap'

    # IMPORTANT : Ajouter l'état 'annule' dans la sélection
    state = fields.Selection(
        selection_add=[('annule', 'Annulé')],
        ondelete={'annule': 'cascade'}
    )

    # Champs calculés pour les contrôles
    can_cancel = fields.Boolean(
        string="Peut être annulé",
        compute='_compute_can_actions',
        store=False
    )

    can_reset_to_draft = fields.Boolean(
        string="Peut être remis en brouillon",
        compute='_compute_can_actions',
        store=False
    )

    @api.depends('state', 'invoice_id', 'bon_achat_id')
    def _compute_can_actions(self):
        """Détermine si le récap peut être annulé ou remis en brouillon"""
        for recap in self:
            # Peut être annulé si validé et sans facture/bon d'achat
            recap.can_cancel = (
                    recap.state == 'valide' and
                    not recap.invoice_id and
                    not recap.bon_achat_id
            )

            # Peut être remis en brouillon si annulé
            recap.can_reset_to_draft = (recap.state == 'annule')

    def action_cancel(self):
        """Annule le récapitulatif"""
        self.ensure_one()

        # Vérifications
        if self.state != 'valide':
            raise UserError(_("Seul un récapitulatif validé peut être annulé."))

        if self.invoice_id:
            raise UserError(_(
                "Impossible d'annuler ce récapitulatif car il a une facture fournisseur associée.\n"
                "Facture : %s\n"
                "Pour annuler ce récapitulatif, vous devez d'abord supprimer ou annuler la facture."
            ) % self.invoice_id.name)

        if self.bon_achat_id:
            raise UserError(_(
                "Impossible d'annuler ce récapitulatif car il a un bon d'achat associé.\n"
                "Bon d'achat : %s\n"
                "Pour annuler ce récapitulatif, vous devez d'abord annuler le bon d'achat."
            ) % self.bon_achat_id.name)

        # Annulation
        self.write({'state': 'annule'})

        # Message de traçabilité
        self.message_post(
            body=_("Récapitulatif annulé par %s") % self.env.user.name,
            message_type='notification'
        )

        return True

    def action_reset_to_draft(self):
        """Remet le récapitulatif en brouillon"""
        self.ensure_one()

        # Vérifications
        if self.state != 'annule':
            raise UserError(_("Seul un récapitulatif annulé peut être remis en brouillon."))

        # Remise en brouillon
        self.write({'state': 'brouillon'})

        # Régénérer les lignes si nécessaire
        if not self.recap_line_ids:
            self.generate_recap_lines()
            self.generate_original_lines()
            self.generate_sale_lines()

        # Message de traçabilité
        self.message_post(
            body=_("Récapitulatif remis en brouillon par %s") % self.env.user.name,
            message_type='notification'
        )

        return True

    def unlink(self):
        """Permet la suppression sous conditions"""
        for recap in self:
            # Interdire la suppression si facture ou bon d'achat
            if recap.invoice_id:
                raise UserError(_(
                    "Impossible de supprimer le récapitulatif %s car il a une facture associée."
                ) % recap.name)

            if recap.bon_achat_id:
                raise UserError(_(
                    "Impossible de supprimer le récapitulatif %s car il a un bon d'achat associé."
                ) % recap.name)

            # Permettre la suppression si brouillon ou annulé
            if recap.state not in ['brouillon', 'annule']:
                raise UserError(_(
                    "Le récapitulatif %s ne peut être supprimé que s'il est en brouillon ou annulé."
                ) % recap.name)

        return super().unlink()
