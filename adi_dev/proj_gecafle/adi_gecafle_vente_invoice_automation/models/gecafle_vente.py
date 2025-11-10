# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class GecafleVente(models.Model):
    _inherit = 'gecafle.vente'

    # Champs pour tracer l'automatisation
    invoice_automation_status = fields.Selection([
        ('pending', 'En attente'),
        ('success', 'Succès'),
        ('draft_fallback', 'Créée en brouillon (erreur)'),
        ('failed', 'Échec')
    ], string="Statut automatisation facture", readonly=True, copy=False)

    invoice_automation_error = fields.Text(
        string="Erreur d'automatisation",
        readonly=True,
        copy=False
    )

    invoice_auto_posted = fields.Boolean(
        string="Facture auto-comptabilisée",
        readonly=True,
        copy=False,
        help="Indique si la facture a été automatiquement comptabilisée"
    )

    def action_confirm(self):
        """Surcharge pour gérer l'automatisation des factures"""
        _logger.info("=== DÉBUT action_confirm du module automatisation ===")

        for vente in self:
            if vente.state == 'brouillon':
                _logger.info(f"Traitement de la vente {vente.name}")

                # IMPORTANT : Utiliser le contexte pour permettre les modifications
                vente_with_context = vente.with_context(allow_adjustment=True)

                # 1. Appeler le super qui va créer la facture via le module vente_invoices
                res = super(GecafleVente, vente_with_context).action_confirm()

                # 2. Si une facture a été créée, gérer la comptabilisation automatique
                if vente.invoice_ids:
                    invoice = vente.invoice_ids[0]
                    _logger.info(f"Facture {invoice.name} trouvée pour la vente {vente.name}")

                    # Vérifier si on doit comptabiliser automatiquement
                    if vente.company_id.sudo().auto_post_sales_invoices:
                        if invoice.state == 'draft':
                            _logger.info(f"Tentative de comptabilisation automatique pour {invoice.name}")
                            try:
                                invoice.action_post()

                                # Marquer le succès avec contexte
                                vente_with_context.write({
                                    'invoice_automation_status': 'success',
                                    'invoice_auto_posted': True,
                                    'invoice_automation_error': False
                                })

                                # Logger le succès dans le chatter
                                vente.message_post(
                                    body=_("✅ Facture %s créée et comptabilisée automatiquement.") % invoice.name,
                                    message_type='notification'
                                )

                                _logger.info(f"Facture {invoice.name} comptabilisée avec succès")

                            except (UserError, ValidationError, Exception) as e:
                                error_msg = str(e)
                                _logger.warning(f"⚠️ Erreur lors de la comptabilisation de {invoice.name}: {error_msg}")

                                # Si l'option de retry en brouillon est activée
                                if vente.company_id.sudo().invoice_auto_validation_retry:
                                    # La facture reste en brouillon
                                    vente_with_context.write({
                                        'invoice_automation_status': 'draft_fallback',
                                        'invoice_auto_posted': False,
                                        'invoice_automation_error': error_msg
                                    })

                                    # Logger l'erreur dans le chatter si configuré
                                    if vente.company_id.sudo().invoice_auto_log_errors:
                                        vente.message_post(
                                            body=_(
                                                "⚠️ La facture %s a été créée en brouillon car la comptabilisation "
                                                "automatique a échoué.\n\nErreur: %s\n\n"
                                                "Veuillez vérifier et valider manuellement la facture."
                                            ) % (invoice.name, error_msg),
                                            message_type='warning'
                                        )
                                else:
                                    # Lever l'erreur si pas de fallback
                                    raise
                        elif invoice.state == 'posted':
                            # La facture est déjà comptabilisée (par le module vente_invoices)
                            _logger.info(f"La facture {invoice.name} est déjà comptabilisée")
                            vente_with_context.write({
                                'invoice_automation_status': 'success',
                                'invoice_auto_posted': True,
                                'invoice_automation_error': False
                            })
                    else:
                        # Comptabilisation automatique désactivée
                        _logger.info(
                            f"Comptabilisation automatique désactivée - Facture {invoice.name} laissée en état {invoice.state}")
                        vente_with_context.write({
                            'invoice_automation_status': 'success',
                            'invoice_auto_posted': False,
                            'invoice_automation_error': False
                        })
                else:
                    _logger.warning(f"Aucune facture créée pour la vente {vente.name}")

                return res

        return True

    def _validate_sale_only(self):
        """Cette méthode n'est plus nécessaire car on utilise super()"""
        pass

    def _create_invoice(self):
        """SURCHARGE pour NE PAS appeler action_post() automatiquement"""
        # Vérifier si la facture existe déjà
        if self.invoice_ids:
            _logger.info(f"Une facture existe déjà pour la vente {self.name}")
            return self.invoice_ids[0]

        # Sinon appeler le super
        return super()._create_invoice()

    def _create_and_post_invoice_auto(self):
        """Cette méthode n'est plus nécessaire car on utilise super()"""
        pass

    # Les autres méthodes restent inchangées...
    def _send_invoice_email(self, invoice):
        """Envoie la facture par email au client"""
        try:
            template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)

            if template:
                template.send_mail(invoice.id, force_send=True)

                self.message_post(
                    body=_("📧 Facture %s envoyée par email au client.") % invoice.name,
                    message_type='notification'
                )

                _logger.info(f"Facture {invoice.name} envoyée par email")
            else:
                _logger.warning(f"Template d'email de facture non trouvé pour {invoice.name}")

        except Exception as e:
            _logger.error(f"Erreur lors de l'envoi de l'email pour {invoice.name}: {str(e)}")

            if self.company_id.sudo().invoice_auto_log_errors:
                self.message_post(
                    body=_("⚠️ Erreur lors de l'envoi de l'email: %s") % str(e),
                    message_type='warning'
                )

    def action_retry_invoice_posting(self):
        """Action manuelle pour réessayer de comptabiliser une facture en brouillon"""
        self.ensure_one()

        if not self.invoice_ids:
            raise UserError(_("Aucune facture n'est liée à cette vente."))

        invoice = self.invoice_ids[0]

        if invoice.state != 'draft':
            raise UserError(_("La facture n'est pas en brouillon."))

        try:
            invoice.action_post()

            # Utiliser le contexte pour permettre la modification
            self.with_context(allow_adjustment=True).write({
                'invoice_automation_status': 'success',
                'invoice_auto_posted': True,
                'invoice_automation_error': False
            })

            self.message_post(
                body=_("✅ Facture %s comptabilisée avec succès (réessai manuel).") % invoice.name,
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('La facture a été comptabilisée avec succès.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            error_msg = str(e)

            self.with_context(allow_adjustment=True).write({
                'invoice_automation_error': error_msg
            })

            raise UserError(_(
                "Impossible de comptabiliser la facture.\n\nErreur: %s"
            ) % error_msg)
