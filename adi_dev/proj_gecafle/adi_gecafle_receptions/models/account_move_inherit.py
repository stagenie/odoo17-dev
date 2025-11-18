# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Override action_post pour synchroniser les paiements avec les réceptions
        quand l'écriture comptable est validée
        """
        import logging
        _logger = logging.getLogger(__name__)

        # Appeler la méthode parent pour valider l'écriture
        res = super(AccountMove, self).action_post()

        # Synchroniser les paiements liés
        for move in self:
            # Chercher les paiements liés à cette écriture
            payments = self.env['account.payment'].search([('move_id', '=', move.id)])

            for payment in payments:
                if payment.reception_id:
                    # Déterminer le champ à mettre à jour
                    field_name = None
                    if payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif payment.is_advance_transport:
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
                                self.env.cr.execute(
                                    f'UPDATE gecafle_reception SET {field_name} = %s WHERE id = %s',
                                    (payment.amount, reception.id)
                                )
                                self.env.cr.commit()
                                _logger.info(f"[PAYMENT SYNC - POST] SQL update successful for {field_name}")
                        except Exception as e:
                            _logger.error(f"[PAYMENT SYNC - POST] Error updating {field_name}: {e}")

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
                if payment.reception_id:
                    field_name = None
                    if payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif payment.is_advance_transport:
                        field_name = 'transport'
                    elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                        field_name = 'paiement_emballage'

                    if field_name:
                        payments_to_reset.append((payment.reception_id, field_name))

        # Appeler la méthode parent
        res = super(AccountMove, self).button_draft()

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
                if payment.reception_id:
                    field_name = None
                    if payment.is_advance_producer:
                        field_name = 'avance_producteur'
                    elif payment.is_advance_transport:
                        field_name = 'transport'
                    elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                        field_name = 'paiement_emballage'

                    if field_name:
                        payments_to_reset.append((payment.reception_id, field_name))

        # Appeler la méthode parent
        res = super(AccountMove, self).button_cancel()

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