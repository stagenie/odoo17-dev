# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleVenteResetWizard(models.TransientModel):
    _name = 'gecafle.vente.reset.wizard'
    _description = 'Assistant de remise en brouillon'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True,
        readonly=True
    )

    has_invoice = fields.Boolean(
        string="A une facture",
        readonly=True
    )

    has_payments = fields.Boolean(
        string="A des paiements",
        readonly=True
    )

    payment_info = fields.Text(
        string="Informations paiements",
        compute='_compute_payment_info'
    )

    has_treasury_operations = fields.Boolean(
        string="A des paiements relevés en caisse",
        compute='_compute_treasury_status'
    )

    confirmation = fields.Boolean(
        string="Je confirme vouloir remettre cette vente en brouillon",
        required=True,
        default= True
    )

    @api.depends('vente_id', 'vente_id.invoice_id')
    def _compute_payment_info(self):
        for wizard in self:
            info = []
            if wizard.vente_id.invoice_id:
                try:
                    # IMPORTANT : Vérifier que la facture existe encore
                    if wizard.vente_id.invoice_id.exists():
                        payments = wizard.vente_id.invoice_id._get_reconciled_payments()
                        if payments and payments.exists():
                            for payment in payments:
                                if payment.exists():  # Double vérification
                                    status = "Non relevé"
                                    treasury_ops = self.env['treasury.cash.operation'].search([
                                        ('payment_id', '=', payment.id),
                                        ('closing_id.state', '=', 'validated')
                                    ])
                                    if treasury_ops:
                                        status = "✓ Relevé en caisse"

                                    info.append(
                                        f"- {payment.name}: {payment.amount} {payment.currency_id.symbol} [{status}]")
                except Exception as e:
                    _logger.warning(f"Erreur lors de la récupération des paiements : {str(e)}")

            wizard.payment_info = '\n'.join(info) if info else "Aucun paiement"

    @api.depends('vente_id', 'vente_id.invoice_id')
    def _compute_treasury_status(self):
        """Vérifie si des paiements ont été relevés en caisse"""
        for wizard in self:
            has_treasury = False

            if wizard.vente_id.invoice_id and wizard.vente_id.invoice_id.exists():
                try:
                    payments = wizard.vente_id.invoice_id._get_reconciled_payments()
                    if payments and payments.exists():
                        for payment in payments:
                            if payment.exists():
                                treasury_ops = self.env['treasury.cash.operation'].search([
                                    ('payment_id', '=', payment.id),
                                    ('closing_id.state', '=', 'validated')
                                ])
                                if treasury_ops:
                                    has_treasury = True
                                    break
                except Exception as e:
                    _logger.warning(f"Erreur lors de la vérification treasury : {str(e)}")

            wizard.has_treasury_operations = has_treasury

    def action_confirm_reset(self):
        """Exécute la remise en brouillon avec suppression des éléments"""
        self.ensure_one()

        if not self.confirmation:
            raise UserError(_("Veuillez confirmer l'action."))

        if self.vente_id.has_avoirs:
            raise UserError(_(
                "Impossible de continuer : des avoirs sont liés à cette vente.\n"
                "Veuillez d'abord annuler tous les avoirs avant de remettre la vente en brouillon."
            ))

        if self.has_treasury_operations:
            raise UserError(_(
                "Impossible de remettre en brouillon : des paiements ont été relevés en caisse.\n\n"
                "Options disponibles :\n"
                "1. Créer un avoir client pour corriger la vente\n"
                "2. Annuler d'abord les relevés de caisse concernés"
            ))

        _logger.info(f"Début remise en brouillon pour vente {self.vente_id.name}")

        # Logger l'action
        self.vente_id.message_post(
            body=_("🔄 Début de remise en brouillon par %s") % self.env.user.name,
            message_type='notification'
        )

        try:
            # 1. SUPPRESSION DES PAIEMENTS - Méthode améliorée
            if self.vente_id.invoice_id and self.vente_id.invoice_id.exists():
                invoice = self.vente_id.invoice_id

                # Désactiver temporairement les contraintes pour la suppression
                invoice = invoice.with_context(force_delete=True)

                # Méthode 1: Via _get_reconciled_payments
                try:
                    payments_to_delete = []
                    payments = invoice._get_reconciled_payments()

                    if payments and payments.exists():
                        for payment in payments:
                            if not payment.exists():
                                continue

                            # Vérifier treasury
                            treasury_ops = self.env['treasury.cash.operation'].search([
                                ('payment_id', '=', payment.id)
                            ])

                            if not treasury_ops:
                                payments_to_delete.append(payment)

                    # Supprimer tous les paiements en une fois
                    if payments_to_delete:
                        # Annuler d'abord les paiements postés
                        posted_payments = [p for p in payments_to_delete if p.state == 'posted']
                        if posted_payments:
                            for p in posted_payments:
                                try:
                                    p.action_cancel()
                                except:
                                    p.action_draft()  # Fallback

                        # Supprimer tous les paiements
                        payment_names = [p.name for p in payments_to_delete]
                        self.env['account.payment'].browse([p.id for p in payments_to_delete]).unlink()

                        for name in payment_names:
                            self.vente_id.message_post(
                                body=_("❌ Paiement %s supprimé") % name,
                                message_type='notification'
                            )
                            _logger.info(f"Paiement {name} supprimé")

                except Exception as e:
                    _logger.warning(f"Erreur lors de la suppression des paiements (méthode 1): {str(e)}")

                # Méthode 2: Délier les rapprochements
                try:
                    if invoice.line_ids:
                        invoice.line_ids.remove_move_reconcile()
                except Exception as e:
                    _logger.warning(f"Erreur lors de la suppression des rapprochements: {str(e)}")

            # 2. SUPPRESSION DE LA FACTURE
            if self.vente_id.invoice_id and self.vente_id.invoice_id.exists():
                invoice = self.vente_id.invoice_id
                invoice_name = invoice.name

                try:
                    # Annuler si nécessaire
                    if invoice.state == 'posted':
                        invoice.with_context(force_gecafle_update=True).button_cancel()

                    # Passer en brouillon si annulée
                    if invoice.state == 'cancel':
                        invoice.with_context(force_gecafle_update=True).button_draft()

                    # Supprimer avec contexte forcé
                    invoice.with_context(force_gecafle_update=True, force_delete=True).unlink()

                    self.vente_id.message_post(
                        body=_("🗑️ Facture %s supprimée") % invoice_name,
                        message_type='notification'
                    )
                    _logger.info(f"Facture {invoice_name} supprimée avec succès")

                except Exception as e:
                    _logger.error(f"Erreur lors de la suppression de la facture: {str(e)}")
                    # Tentative alternative
                    try:
                        self.vente_id.write({'invoice_id': False})
                        invoice.unlink()
                    except:
                        raise UserError(_(
                            "Impossible de supprimer la facture. "
                            "Veuillez la supprimer manuellement."
                        ))

            # 3. REMISE EN BROUILLON DE LA VENTE
            self.vente_id.with_context(allow_adjustment=True).write({
                'state': 'brouillon',
                'est_imprimee': False,
                'invoice_id': False,
                'invoice_ids': [(5, 0, 0)]
            })

            # 4. LIBÉRATION DES STOCKS
            for line in self.vente_id.detail_vente_ids:
                if hasattr(line, 'detail_reception_id') and line.detail_reception_id:
                    try:
                        if line.detail_reception_id.qte_colis_vendus >= line.nombre_colis:
                            line.detail_reception_id.qte_colis_vendus -= line.nombre_colis
                        else:
                            line.detail_reception_id.qte_colis_vendus = 0
                    except Exception as e:
                        _logger.warning(f"Erreur lors de la libération du stock : {str(e)}")

            # Message final
            self.vente_id.message_post(
                body=_("✅ Vente remise en brouillon avec succès"),
                message_type='comment'
            )

            # IMPORTANT : Fermer le wizard et rester sur la vente
            return {'type': 'ir.actions.act_window_close'}

        except Exception as e:
            self.vente_id.message_post(
                body=_("❌ Erreur lors de la remise en brouillon : %s") % str(e),
                message_type='warning'
            )
            raise UserError(_(
                "Erreur lors de la remise en brouillon:\n%s"
            ) % str(e))
