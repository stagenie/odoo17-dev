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
        # Permettre la suppression si force_delete est dans le contexte
        if self.env.context.get('force_delete'):
            return
        for move in self:
            if hasattr(move, 'recap_id') and move.recap_id:
                if move.state != 'draft':
                    raise UserError(_(
                        "Impossible de supprimer la facture %s car elle n'est pas en brouillon. "
                        "Annulez-la d'abord."
                    ) % move.name)

    def action_post(self):
        """
        Override action_post pour synchroniser les paiements avec les réceptions
        quand l'écriture comptable est validée
        """
        import logging
        _logger = logging.getLogger(__name__)

        # Appeler la méthode parent pour valider l'écriture
        res = super(AccountMoveInherit, self).action_post()

        # Synchroniser les paiements liés
        for move in self:
            # Chercher les paiements liés à cette écriture
            payments = self.env['account.payment'].search([('move_id', '=', move.id)])

            for payment in payments:
                if hasattr(payment, 'reception_id') and payment.reception_id:
                    _logger.info(f"[PAYMENT SYNC - POST] Processing payment {payment.id} for reception {payment.reception_id.id}")

                    # Déterminer le champ à mettre à jour
                    field_name = None
                    if hasattr(payment, 'is_advance_producer') and payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif hasattr(payment, 'is_advance_transport') and payment.is_advance_transport:
                        field_name = 'transport'
                    elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                        field_name = 'paiement_emballage'

                    if field_name:
                        try:
                            reception = payment.reception_id
                            # Utiliser l'ORM pour mettre à jour
                            if hasattr(reception, field_name):
                                reception.sudo().write({field_name: payment.amount})
                                _logger.info(f"[PAYMENT SYNC - POST] Successfully updated {field_name} = {payment.amount} for reception {reception.id}")
                            else:
                                # Fallback SQL
                                _logger.warning(f"[PAYMENT SYNC - POST] Field {field_name} not found in model, using SQL")
                                self.env.cr.execute(
                                    f'UPDATE gecafle_reception SET {field_name} = %s WHERE id = %s',
                                    (payment.amount, reception.id)
                                )
                                self.env.cr.commit()
                                _logger.info(f"[PAYMENT SYNC - POST] SQL update successful for {field_name}")
                        except Exception as e:
                            _logger.error(f"[PAYMENT SYNC - POST] Error updating {field_name}: {e}")
                            import traceback
                            _logger.error(traceback.format_exc())

        return res

    def button_draft(self):
        """
        Override button_draft pour réinitialiser les montants dans les réceptions
        quand l'écriture comptable est remise en brouillon
        """
        import logging
        _logger = logging.getLogger(__name__)

        # D'abord capturer les paiements avant de remettre en brouillon
        payments_to_reset = []
        for move in self:
            payments = self.env['account.payment'].search([('move_id', '=', move.id)])
            for payment in payments:
                if hasattr(payment, 'reception_id') and payment.reception_id:
                    field_name = None
                    if hasattr(payment, 'is_advance_producer') and payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif hasattr(payment, 'is_advance_transport') and payment.is_advance_transport:
                        field_name = 'transport'
                    elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                        field_name = 'paiement_emballage'

                    if field_name:
                        payments_to_reset.append((payment.reception_id, field_name))
                        _logger.info(f"[PAYMENT SYNC - DRAFT] Will reset {field_name} for reception {payment.reception_id.id}")

        # Appeler la méthode parent
        res = super(AccountMoveInherit, self).button_draft()

        # Réinitialiser les montants dans les réceptions
        for reception, field_name in payments_to_reset:
            try:
                if hasattr(reception, field_name):
                    reception.sudo().write({field_name: 0.0})
                    _logger.info(f"[PAYMENT SYNC - DRAFT] Reset {field_name} = 0 for reception {reception.id}")
                else:
                    # Fallback SQL
                    self.env.cr.execute(
                        f'UPDATE gecafle_reception SET {field_name} = 0 WHERE id = %s',
                        (reception.id,)
                    )
                    self.env.cr.commit()
                    _logger.info(f"[PAYMENT SYNC - DRAFT] SQL reset successful for {field_name}")
            except Exception as e:
                _logger.error(f"[PAYMENT SYNC - DRAFT] Error resetting {field_name}: {e}")

        return res

    def button_cancel(self):
        """
        Override button_cancel pour réinitialiser les montants dans les réceptions
        quand l'écriture comptable est annulée
        """
        import logging
        _logger = logging.getLogger(__name__)

        # D'abord capturer les paiements avant d'annuler
        payments_to_reset = []
        for move in self:
            payments = self.env['account.payment'].search([('move_id', '=', move.id)])
            for payment in payments:
                if hasattr(payment, 'reception_id') and payment.reception_id:
                    field_name = None
                    if hasattr(payment, 'is_advance_producer') and payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif hasattr(payment, 'is_advance_transport') and payment.is_advance_transport:
                        field_name = 'transport'
                    elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                        field_name = 'paiement_emballage'

                    if field_name:
                        payments_to_reset.append((payment.reception_id, field_name))

        # Appeler la méthode parent
        res = super(AccountMoveInherit, self).button_cancel()

        # Réinitialiser les montants dans les réceptions
        for reception, field_name in payments_to_reset:
            try:
                if hasattr(reception, field_name):
                    reception.sudo().write({field_name: 0.0})
                    _logger.info(f"[PAYMENT SYNC - CANCEL] Reset {field_name} = 0 for reception {reception.id}")
                else:
                    # Fallback SQL
                    self.env.cr.execute(
                        f'UPDATE gecafle_reception SET {field_name} = 0 WHERE id = %s',
                        (reception.id,)
                    )
                    self.env.cr.commit()
                    _logger.info(f"[PAYMENT SYNC - CANCEL] SQL reset successful for {field_name}")
            except Exception as e:
                _logger.error(f"[PAYMENT SYNC - CANCEL] Error resetting {field_name}: {e}")

        return res
