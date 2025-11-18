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

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create pour synchroniser dès la création si le paiement est posté
        """
        import logging
        _logger = logging.getLogger(__name__)

        payments = super(AccountPayment, self).create(vals_list)

        for payment in payments:
            # Dans Odoo 17, l'état est dans move_id.state, pas dans payment.state
            if payment.reception_id and payment.move_id and payment.move_id.state == 'posted':
                # Synchroniser immédiatement si créé en état posted
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
                        if hasattr(reception, field_name):
                            reception.sudo().write({field_name: payment.amount})
                            _logger.info(f"[PAYMENT CREATE] Successfully set {field_name} = {payment.amount} for reception {reception.id}")
                        else:
                            # Fallback SQL si le champ n'est pas dans le modèle
                            self.env.cr.execute(
                                f'UPDATE gecafle_reception SET {field_name} = %s WHERE id = %s',
                                (payment.amount, reception.id)
                            )
                            self.env.cr.commit()
                            _logger.info(f"[PAYMENT CREATE] SQL update successful for {field_name}")
                    except Exception as e:
                        _logger.error(f"[PAYMENT CREATE] Error setting {field_name}: {e}")

        return payments

    def write(self, vals):
        """
        Synchronise les montants des paiements avec les champs de la réception.
        Gère : avance_producteur, transport, paiement_emballage
        """
        import logging
        _logger = logging.getLogger(__name__)

        # Mémoriser l'état précédent pour détecter les changements
        old_data = {}
        for payment in self:
            # Dans Odoo 17, l'état est dans move_id.state
            old_data[payment.id] = {
                'state': payment.move_id.state if payment.move_id else 'draft',
                'amount': payment.amount,
                'reception_id': payment.reception_id.id if payment.reception_id else False,
                'is_advance_producer': payment.is_advance_producer,
                'is_advance_transport': payment.is_advance_transport,
                'is_payment_emballage': getattr(payment, 'is_payment_emballage', False),
            }

        res = super(AccountPayment, self).write(vals)

        for payment in self:
            # Dans Odoo 17, l'état est dans move_id.state
            current_state = payment.move_id.state if payment.move_id else 'draft'

            # Log pour debug
            _logger.info(f"[PAYMENT SYNC] Payment {payment.id} - reception_id: {payment.reception_id.id if payment.reception_id else 'None'}, "
                        f"state: {current_state}, amount: {payment.amount}, "
                        f"is_advance_producer: {payment.is_advance_producer}, "
                        f"is_advance_transport: {payment.is_advance_transport}, "
                        f"is_payment_emballage: {getattr(payment, 'is_payment_emballage', False)}")

            if not payment.reception_id:
                _logger.warning(f"[PAYMENT SYNC] Payment {payment.id} has no reception_id - skipping sync")
                continue

            reception = payment.reception_id
            old_state = old_data.get(payment.id, {}).get('state')
            new_state = current_state
            old_amount = old_data.get(payment.id, {}).get('amount', 0)
            new_amount = payment.amount

            # Déterminer quelle action prendre
            should_update = False
            new_value = 0.0
            field_name = None

            # Déterminer le type de paiement et le champ correspondant
            if payment.is_advance_producer:
                field_name = 'avance_producteur'
            elif payment.is_advance_transport:
                field_name = 'transport'
            elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                field_name = 'paiement_emballage'

            if not field_name:
                _logger.warning(f"[PAYMENT SYNC] Payment {payment.id} has no recognized type - skipping")
                continue

            # Cas 1 : Le paiement passe à 'posted'
            if new_state == 'posted' and old_state != 'posted':
                _logger.info(f"[PAYMENT SYNC] Payment {payment.id} transition to posted - updating {field_name} to {payment.amount}")
                should_update = True
                new_value = payment.amount

            # Cas 2 : Le paiement quitte l'état 'posted'
            elif old_state == 'posted' and new_state in ('draft', 'cancel'):
                _logger.info(f"[PAYMENT SYNC] Payment {payment.id} transition from posted to {new_state} - resetting {field_name} to 0")
                should_update = True
                new_value = 0.0

            # Cas 3 : Le montant change alors que le paiement est déjà posted
            elif new_state == 'posted' and old_state == 'posted' and old_amount != new_amount:
                _logger.info(f"[PAYMENT SYNC] Payment {payment.id} amount changed from {old_amount} to {new_amount} - updating {field_name}")
                should_update = True
                new_value = payment.amount

            if should_update and field_name:
                try:
                    # Vérifier d'abord si le champ existe
                    self.env.cr.execute(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'gecafle_reception'
                        AND column_name = %s
                    """, (field_name,))

                    if self.env.cr.fetchone():
                        # Utiliser l'ORM d'Odoo pour la mise à jour (plus sûr et gère le cache)
                        if hasattr(reception, field_name):
                            # Utiliser sudo() pour éviter les problèmes de droits
                            reception.sudo().write({field_name: new_value})
                            _logger.info(f"[PAYMENT SYNC] Successfully updated {field_name} = {new_value} for reception {reception.id}")
                        else:
                            # Si le champ n'existe pas dans le modèle, utiliser SQL comme fallback
                            _logger.info(f"[PAYMENT SYNC] Field not in model, using SQL UPDATE: SET {field_name} = {new_value} WHERE id = {reception.id}")
                            self.env.cr.execute(
                                f'UPDATE gecafle_reception SET {field_name} = %s WHERE id = %s',
                                (new_value, reception.id)
                            )
                            self.env.cr.commit()
                            reception.invalidate_recordset()
                            reception.refresh()
                            _logger.info(f"[PAYMENT SYNC] SQL update successful")
                    else:
                        _logger.error(f"[PAYMENT SYNC] Field {field_name} does not exist in table gecafle_reception!")
                        # Tenter de créer le champ s'il manque
                        _logger.info(f"[PAYMENT SYNC] Attempting to create missing field {field_name}")
                        self.env.cr.execute(f"""
                            ALTER TABLE gecafle_reception
                            ADD COLUMN IF NOT EXISTS {field_name} NUMERIC DEFAULT 0
                        """)
                        self.env.cr.commit()
                        # Réessayer la mise à jour
                        self.env.cr.execute(
                            f'UPDATE gecafle_reception SET {field_name} = %s WHERE id = %s',
                            (new_value, reception.id)
                        )
                        self.env.cr.commit()
                        _logger.info(f"[PAYMENT SYNC] Field created and updated successfully")
                except Exception as e:
                    _logger.error(f"[PAYMENT SYNC] Error updating {field_name}: {e}")
                    import traceback
                    _logger.error(traceback.format_exc())

        return res

    def unlink(self):
        """Réinitialise les montants sur la réception avant de supprimer le paiement"""
        import logging
        _logger = logging.getLogger(__name__)

        for payment in self:
            # Dans Odoo 17, l'état est dans move_id.state
            payment_state = payment.move_id.state if payment.move_id else 'draft'
            if payment.reception_id and payment_state == 'posted':
                reception = payment.reception_id
                field_name = None

                # Déterminer le champ à réinitialiser
                if payment.is_advance_producer:
                    field_name = 'avance_producteur'
                elif payment.is_advance_transport:
                    field_name = 'transport'
                elif hasattr(payment, 'is_payment_emballage') and payment.is_payment_emballage:
                    field_name = 'paiement_emballage'

                if field_name:
                    try:
                        _logger.info(f"[PAYMENT UNLINK] Resetting {field_name} to 0 for reception {reception.id} (payment {payment.id} being deleted)")
                        # Vérifier si le champ existe
                        self.env.cr.execute(f"""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'gecafle_reception'
                            AND column_name = %s
                        """, (field_name,))

                        if self.env.cr.fetchone():
                            self.env.cr.execute(
                                f'UPDATE gecafle_reception SET {field_name} = 0.0 WHERE id = %s',
                                (reception.id,)
                            )
                            self.env.cr.commit()
                            reception.invalidate_recordset([field_name])
                            reception.refresh()
                            _logger.info(f"[PAYMENT UNLINK] Successfully reset {field_name} to 0")
                        else:
                            _logger.error(f"[PAYMENT UNLINK] Field {field_name} does not exist!")
                    except Exception as e:
                        _logger.error(f"[PAYMENT UNLINK] Error resetting {field_name}: {e}")

        return super(AccountPayment, self).unlink()

