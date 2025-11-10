# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def unlink(self):
        """Override unlink pour gérer l'état du récapitulatif lors de la suppression"""
        # Sauvegarder les récaps liés avant suppression
        recaps_to_update = self.mapped('recap_id')

        # Appeler la méthode parent pour supprimer
        res = super(AccountMoveInherit, self).unlink()

        # Mettre à jour l'état des récaps
        for recap in recaps_to_update:
            if recap and recap.state == 'facture' and not recap.invoice_id:
                # Remettre en état validé si la facture était la seule
                recap.state = 'valide'
                recap.message_post(
                    body=_("L'état a été remis à 'Validé' suite à la suppression de la facture associée."),
                    subtype_xmlid='mail.mt_note'
                )

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_check_recap(self):
        """Vérifie et met à jour l'état du récapitulatif lors de la suppression"""
        for move in self:
            if hasattr(move, 'recap_id') and move.recap_id:
                if move.state != 'draft':
                    raise UserError(_(
                        "Impossible de supprimer la facture %s car elle n'est pas en brouillon. "
                        "Annulez-la d'abord."
                    ) % move.name)
