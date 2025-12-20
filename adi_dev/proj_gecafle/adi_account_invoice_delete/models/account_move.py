# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    can_delete_cancelled = fields.Boolean(
        string="Peut être supprimée",
        compute='_compute_can_delete_cancelled',
        help="Indique si cette facture annulée peut être supprimée"
    )

    @api.depends('state', 'move_type')
    def _compute_can_delete_cancelled(self):
        """Détermine si la facture peut être supprimée"""
        for record in self:
            # Seules les factures annulées peuvent être supprimées
            record.can_delete_cancelled = (
                record.state == 'cancel' and
                record.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
            )

    def action_delete_cancelled_invoice(self):
        """
        Supprime les factures annulées après avoir dissocié les liens
        avec les bordereaux (recaps) et autres documents liés
        """
        self.ensure_one()

        if self.state != 'cancel':
            raise UserError(_(
                "Seules les factures annulées peuvent être supprimées.\n"
                "Veuillez d'abord annuler la facture '%s'."
            ) % self.name)

        # Dissocier les bordereaux (recaps) liés à cette facture
        self._unlink_related_recaps()

        # Dissocier les ventes liées (invoice_ids)
        self._unlink_related_sales()

        # Supprimer la facture
        self.with_context(force_delete=True).unlink()

        # Retourner une action pour fermer et rafraîchir la vue
        return {
            'type': 'ir.actions.act_window_close',
        }

    def _unlink_related_recaps(self):
        """Dissocie les bordereaux (gecafle.reception.recap) liés à cette facture"""
        self.ensure_one()

        # Chercher les recaps qui référencent cette facture
        Recap = self.env.get('gecafle.reception.recap')
        if Recap is not None:
            recaps = Recap.search([('invoice_id', '=', self.id)])
            if recaps:
                for recap in recaps:
                    # Sauvegarder l'ancien état
                    old_state = recap.state

                    # Dissocier la facture et remettre en état 'valide' si nécessaire
                    vals = {'invoice_id': False}
                    if old_state == 'facture':
                        vals['state'] = 'valide'

                    recap.write(vals)

                    # Invalider le cache pour forcer le recalcul des champs calculés
                    recap.invalidate_recordset(['can_cancel', 'can_reset_to_draft'])

                    # Logger l'action
                    message = _("Facture fournisseur '%s' dissociée suite à sa suppression.") % self.name
                    if old_state == 'facture':
                        message += _(" L'état a été remis à 'Validé'.")
                    recap.message_post(body=message)

    def _unlink_related_sales(self):
        """Dissocie les ventes (gecafle.vente) liées à cette facture"""
        self.ensure_one()

        # Chercher les ventes qui référencent cette facture via invoice_ids
        Vente = self.env.get('gecafle.vente')
        if Vente is not None:
            # Les factures client sont liées via invoice_ids (Many2many ou One2many)
            if hasattr(Vente, 'invoice_ids'):
                ventes = Vente.search([('invoice_ids', 'in', self.id)])
                if ventes:
                    for vente in ventes:
                        vente.message_post(
                            body=_("Facture '%s' supprimée du système.") % self.name
                        )

    def unlink(self):
        """Override unlink pour permettre la suppression des factures annulées"""
        for move in self:
            if move.state == 'cancel' and self.env.context.get('force_delete'):
                # Permettre la suppression avec le contexte force_delete
                continue
            elif move.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "Vous ne pouvez pas supprimer une facture qui n'est pas en brouillon ou annulée.\n"
                    "Facture: %s (État: %s)"
                ) % (move.name, move.state))

        return super(AccountMove, self).unlink()
