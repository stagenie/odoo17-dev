# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        ondelete='cascade',
        help="Réception liée à ce paiement"
    )

    is_advance_producer = fields.Boolean(
        string="Avance Producteur",
        default=False,
        help="Cocher si ce paiement est une avance producteur (à distinguer de l'avance transport, etc.)"
    )

    is_advance_transport = fields.Boolean(
        string="Frais de Transport",
        default=False,
        help="Cocher si ce paiement est pour les frais de transport"
    )

    type_de_paiement = fields.Selection(
        compute='_compute_type_de_paiement',
        selection=[
            ('standard', 'Paiement Standard'),
            ('avance_producteur', 'Avance Producteur'),
            ('avance_transport', 'Avance Transport'),
        ],
        string="Type de Paiement",
        store=True,
        help="Type de paiement pour identification rapide"
    )

    @api.depends('is_advance_producer', 'is_advance_transport')
    def _compute_type_de_paiement(self):
        """Détermine le type de paiement basé sur les flags"""
        for payment in self:
            if payment.is_advance_producer:
                payment.type_de_paiement = 'avance_producteur'
            elif payment.is_advance_transport:
                payment.type_de_paiement = 'avance_transport'
            else:
                payment.type_de_paiement = 'standard'

    def write(self, vals):
        """
        Synchronise le montant du paiement avec le champ avance_producteur de la réception
        UNIQUEMENT quand le paiement est validé (state='posted').
        """
        res = super(AccountPayment, self).write(vals)

        # Synchroniser UNIQUEMENT si le paiement est validé ET c'est un paiement d'avance producteur
        for payment in self:
            if (payment.reception_id and
                payment.is_advance_producer and
                payment.state == 'posted'):  # Vérifier que le paiement est validé
                # Synchroniser avance producteur via SQL direct
                self.env.cr.execute(
                    'UPDATE gecafle_reception SET avance_producteur = %s WHERE id = %s',
                    (payment.amount, payment.reception_id.id)
                )
                # Invalider le cache pour forcer le rechargement
                payment.reception_id._invalidate_cache()

        return res

