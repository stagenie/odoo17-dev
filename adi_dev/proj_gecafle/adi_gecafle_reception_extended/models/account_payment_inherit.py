# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Nouveau champ pour paiement emballage
    is_payment_emballage = fields.Boolean(
        string="Paiement Emballage",
        default=False,
        help="Cocher si ce paiement est pour les emballages achetés"
    )

    type_de_paiement = fields.Selection(
        compute='_compute_type_de_paiement',
        selection=[
            ('standard', 'Paiement Standard'),
            ('avance_producteur', 'Avance Producteur'),
            ('avance_transport', 'Frais Transport'),
            ('emballage', 'Paiement Emballage'),
        ],
        string="Type de Paiement",
        store=True,
        help="Type de paiement pour identification rapide"
    )

    @api.depends('is_advance_producer', 'is_advance_transport', 'is_payment_emballage')
    def _compute_type_de_paiement(self):
        """Détermine le type de paiement basé sur les flags"""
        for payment in self:
            if payment.is_advance_producer:
                payment.type_de_paiement = 'avance_producteur'
            elif payment.is_advance_transport:
                payment.type_de_paiement = 'avance_transport'
            elif payment.is_payment_emballage:
                payment.type_de_paiement = 'emballage'
            else:
                payment.type_de_paiement = 'standard'

    def write(self, vals):
        """Synchronise les montants avec les champs de la réception"""
        res = super(AccountPayment, self).write(vals)

        for payment in self:
            if payment.reception_id and payment.state == 'posted':
                # Synchronisation selon le type
                if payment.is_advance_producer:
                    payment.reception_id.avance_producteur = payment.amount
                elif payment.is_advance_transport:
                    payment.reception_id.transport = payment.amount  # Utilise le champ 'transport'
                elif payment.is_payment_emballage:
                    payment.reception_id.paiement_emballage = payment.amount

                payment.reception_id.invalidate_recordset()

        return res
