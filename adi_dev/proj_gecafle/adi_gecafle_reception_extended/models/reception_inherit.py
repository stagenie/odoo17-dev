# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleReceptionExtended(models.Model):
    _inherit = 'gecafle.reception'

    # Nouveau champ Transport
    transport = fields.Monetary(
        string="Transport",
        currency_field='currency_id',
        readonly=True,
        help="Ce champ est automatiquement mis à jour quand un paiement de frais de transport validé est lié à cette réception. Pour modifier, utilisez le bouton 'Enregistrer Transport' ou le smart button 'Paiements'."
    )

    # Montant total des emballages achetés
    montant_total_emballage_achete = fields.Monetary(
        string="Total Emballages Achetés",
        compute='_compute_montant_emballage_achete',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('details_emballage_reception_ids.is_achete',
                 'details_emballage_reception_ids.montant_achat')
    def _compute_montant_emballage_achete(self):
        """Calcule le montant total des emballages achetés"""
        for record in self:
            record.montant_total_emballage_achete = sum(
                line.montant_achat
                for line in record.details_emballage_reception_ids
                if line.is_achete
            )

    def action_confirm(self):
        """
        Override action_confirm pour créer aussi le paiement de transport si nécessaire.
        """
        # Appeler la méthode parent
        result = super(GecafleReceptionExtended, self).action_confirm()

        # Créer le paiement de transport pour chaque réception confirmée
        for rec in self:
            if rec.transport > 0:
                rec._create_advance_transport_payment()

        return result



    def action_create_advance_transport_payment(self):
        """
        Ouvre le formulaire d'un paiement de frais de transport existant,
        ou crée un nouveau s'il n'existe pas.
        """
        self.ensure_one()

        # Chercher s'il existe déjà un paiement transport pour cette réception
        existing_payment = self.env['account.payment'].search([
            ('reception_id', '=', self.id),
            ('is_advance_transport', '=', True),
        ], limit=1)

        if existing_payment:
            # Ouvrir le paiement existant
            return {
                'name': _('Enregistrer Frais de Transport'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'res_id': existing_payment.id,
                'target': 'current',
            }

        # Aucun paiement existant, créer un nouveau
        partner = self._get_or_create_transport_partner()

        # Ouvrir le formulaire de création de paiement avec contexte pré-rempli
        return {
            'name': _('Enregistrer Frais de Transport'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'context': {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': partner.id,
                'default_amount': self.transport,
                'default_date': fields.Date.today(),
                'default_ref': _('Transport Réception %s') % self.name,
                'default_reception_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_is_advance_transport': True,  # Marquer comme paiement transport
            },
            'target': 'current',
        }

    def _get_or_create_transport_partner(self):
        """
        Utilise le producteur de la réception comme partenaire pour le transport.
        Cela permet de lier le transport directement au producteur.
        """
        self.ensure_one()

        # Utiliser la méthode parent pour obtenir/créer le partner du producteur
        # (celle-ci retourne le même partner utilisé pour l'avance producteur)
        return self._get_or_create_partner()

    def _create_advance_transport_payment(self):
        """Crée un paiement fournisseur pour les frais de transport (si n'existe pas déjà)"""
        self.ensure_one()

        if self.transport <= 0:
            return None

        # Vérifier si un paiement transport existe déjà pour cette réception
        existing_payment = self.env['account.payment'].search([
            ('reception_id', '=', self.id),
            ('is_advance_transport', '=', True),
        ], limit=1)

        if existing_payment:
            # Paiement existe déjà, ne pas le créer en double
            return existing_payment

        # Obtenir ou créer le partner
        partner = self._get_or_create_transport_partner()

        # Créer le paiement
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',  # Paiement sortant
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': self.transport,
            'date': fields.Date.today(),
            'ref': _('Transport Réception %s') % self.name,
            'reception_id': self.id,  # Lien vers la réception
            'is_advance_transport': True,  # Marquer comme paiement transport
        })

        # Valider automatiquement le paiement
        payment.action_post()

        # Message dans le chatter
        self.message_post(
            body=_("Paiement transport créé : %s DA") % (self.transport,)
        )

        return payment



    def action_print_emballages_fr(self):
        """Lance l'impression du rapport emballages en français"""
        self.ensure_one()

        # Vérifier qu'il y a des emballages
        if not self.details_emballage_reception_ids:
            raise UserError(_("Aucun emballage à imprimer pour cette réception."))

        # Retourner l'action du rapport
        return self.env.ref('adi_gecafle_reception_extended.action_report_emballages_reception_fr').report_action(
            self)

    def action_print_emballages_ar(self):
        """Lance l'impression du rapport emballages en arabe"""
        self.ensure_one()

        # Vérifier qu'il y a des emballages
        if not self.details_emballage_reception_ids:
            raise UserError(_("لا توجد عبوات للطباعة في هذا الاستلام."))

        # Retourner l'action du rapport
        return self.env.ref('adi_gecafle_reception_extended.action_report_emballages_reception_ar').report_action(
            self)

    """ Paiement Emballage Acheté - Non implémenté pour l'instant"""
    # AJOUT : Nouveau champ pour paiement emballage
    paiement_emballage = fields.Monetary(
        string="Paiement Emballage",
        currency_field='currency_id',
        readonly=True,
        default=lambda self: self.montant_total_emballage_achete,
        help="Montant du paiement emballage validé. Par défaut égal au montant total des emballages achetés."
    )

    # Méthode pour créer un paiement emballage
    def action_create_emballage_payment(self):
        """Ouvre le formulaire de paiement emballage"""
        self.ensure_one()

        # Chercher un paiement emballage existant
        existing_payment = self.env['account.payment'].search([
            ('reception_id', '=', self.id),
            ('is_payment_emballage', '=', True),
        ], limit=1)

        if existing_payment:
            return {
                'name': _('Paiement Emballage'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'res_id': existing_payment.id,
                'target': 'current',
            }

        partner = self._get_or_create_partner()

        # Utiliser le montant des emballages achetés comme montant par défaut
        default_amount = self.montant_total_emballage_achete or 0.0

        return {
            'name': _('Enregistrer Paiement Emballage'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'context': {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': partner.id,
                'default_amount': default_amount,
                'default_date': fields.Date.today(),
                'default_ref': _('Paiement Emballages Réception %s') % self.name,
                'default_reception_id': self.id,
                'default_is_payment_emballage': True,
            },
            'target': 'current',
        }

    def action_cancel(self):
        """Surcharge pour gérer l'annulation avec vérification des paiements"""
        for rec in self:
            # Vérifier les paiements existants
            payments = self.env['account.payment'].search([
                ('reception_id', '=', rec.id)
            ])

            if payments:
                posted_payments = payments.filtered(lambda p: p.state == 'posted')

                if posted_payments:
                    payment_details = []
                    for p in posted_payments:
                        type_text = ''
                        if p.is_advance_producer:
                            type_text = 'Avance Producteur'
                        elif p.is_advance_transport:
                            type_text = 'Transport'
                        elif p.is_payment_emballage:
                            type_text = 'Emballage'
                        else:
                            type_text = 'Standard'

                        payment_details.append(f"- {type_text}: {p.amount} {p.currency_id.symbol}")

                    raise UserError(_(
                        "Impossible d'annuler cette réception car elle a %d paiement(s) validé(s).\n"
                        "Veuillez d'abord annuler ces paiements :\n%s"
                    ) % (len(posted_payments), '\n'.join(payment_details)))

                # Supprimer les paiements en brouillon
                draft_payments = payments.filtered(lambda p: p.state == 'draft')
                if draft_payments:
                    draft_payments.unlink()
                    rec.message_post(
                        body=_("%d paiement(s) brouillon supprimé(s)") % len(draft_payments)
                    )

        # Appeler la méthode parent pour l'annulation standard
        return super(GecafleReceptionExtended, self).action_cancel()

