# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.constrains('reception_id', 'amount')
    def _check_payment_amount(self):
        """Vérifie que le montant de l'avance ne dépasse pas le montant attendu"""
        for payment in self:
            if payment.reception_id:
                # Calculer le montant total attendu pour cette réception
                recap = self.env['gecafle.reception.recap'].search([
                    ('reception_id', '=', payment.reception_id.id),
                    ('state', '=', 'valide')
                ], limit=1)

                if recap:
                    # Total des paiements pour cette réception
                    total_payments = sum(self.search([
                        ('reception_id', '=', payment.reception_id.id),
                        ('state', '=', 'posted'),
                        ('id', '!=', payment.id)
                    ]).mapped('amount'))

                    if (total_payments + payment.amount) > recap.net_a_payer:
                        raise ValidationError(_(
                            "Le total des avances (%s) dépasserait le montant à payer (%s)"
                        ) % (total_payments + payment.amount, recap.net_a_payer))
