# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleAvoirProducteur(models.Model):
    _inherit = 'gecafle.avoir.producteur'

    def action_force_delete(self):
        """Action pour forcer la suppression de l'avoir producteur - accessible à tous"""
        self.ensure_one()

        # Avertissements selon l'état
        if self.state == 'comptabilise':
            if hasattr(self, 'credit_note_id') and self.credit_note_id:
                if self.credit_note_id.state == 'posted':
                    raise UserError(_(
                        "Impossible de supprimer cet avoir car la note de crédit est validée.\n"
                        "Vous devez d'abord annuler la note de crédit dans la comptabilité."
                    ))

        # Si une note de crédit en brouillon existe, la supprimer
        if hasattr(self, 'credit_note_id') and self.credit_note_id:
            if self.credit_note_id.state == 'draft':
                self.credit_note_id.with_context(force_delete=True).sudo().unlink()

        # Logger l'action avant suppression
        avoir_name = self.name
        self.message_post(body=_("⚠️ Avoir producteur supprimé par %s") % self.env.user.name)

        # Suppression effective
        self.sudo().unlink()

        # MODIFICATION : Retourner vers la vue liste des avoirs producteurs
        return {
            'name': _('Avoirs Producteurs'),
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.avoir.producteur',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'search_default_filter_not_cancelled': 1}
        }
