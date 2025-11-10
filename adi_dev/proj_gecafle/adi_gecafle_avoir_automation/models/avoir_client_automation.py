# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleAvoirClientAutomation(models.Model):
    _inherit = 'gecafle.avoir.client'

    # Nouveau champ pour tracer l'automatisation
    is_automated = fields.Boolean(
        string="Créé automatiquement",
        default=False,
        readonly=True
    )

    @api.model
    def create(self, vals):
        """Override pour automatiser le processus si configuré"""

        # Récupérer la configuration
        config = self.env.company
        auto_validate = config.avoir_auto_validate
        auto_create_note = config.avoir_auto_create_credit_note
        auto_post_note = config.avoir_auto_post_credit_note

        # IMPORTANT : Gérer automatiquement generer_avoirs_producteurs selon le type
        if 'type_avoir' in vals:
            # Pour les avoirs de type consigne, ne JAMAIS générer d'avoirs producteurs
            if vals.get('type_avoir') == 'consigne':
                vals['generer_avoirs_producteurs'] = False
            # Pour les autres types, utiliser la configuration par défaut si non spécifié
            elif 'generer_avoirs_producteurs' not in vals:
                vals['generer_avoirs_producteurs'] = config.avoir_generer_producteurs_defaut

        # Créer l'avoir normalement
        avoir = super().create(vals)

        # Si l'automatisation est activée ET que le montant est valide
        if (auto_validate or self.env.context.get('force_automation')) and avoir.montant_avoir > 0:
            try:
                # Marquer comme automatisé
                avoir.is_automated = True

                # 1. Validation automatique
                if avoir.state == 'brouillon':
                    avoir.with_context(skip_confirmation=True).action_validate()

                # 2. Création automatique de la note de crédit
                if auto_create_note and avoir.state == 'valide':
                    avoir.with_context(skip_confirmation=True)._create_and_post_credit_note(
                        auto_post=auto_post_note
                    )

                # Message de succès
                message = _("✅ Avoir créé et traité automatiquement:\n"
                            "- État: %s\n"
                            "- Note de crédit: %s\n"
                            "- Montant: %s\n"
                            "- Avoirs producteurs: %s") % (
                              avoir.state,
                              avoir.credit_note_id.name if avoir.credit_note_id else "Non créée",
                              avoir.montant_avoir,
                              "Générés" if avoir.generer_avoirs_producteurs and avoir.avoir_producteur_ids else "Non générés"
                          )
                avoir.message_post(body=message)

            except Exception as e:
                # En cas d'erreur, logger mais ne pas bloquer
                avoir.message_post(
                    body=_("⚠️ Automatisation partielle - Erreur: %s") % str(e),
                    message_type='warning'
                )
        elif avoir.montant_avoir == 0:
            avoir.message_post(
                body=_("⚠️ L'avoir a été créé mais n'a pas été automatisé car le montant est à 0.\n"
                       "Veuillez saisir le montant avant de valider."),
                message_type='warning'
            )

        return avoir

    def _create_and_post_credit_note(self, auto_post=True):
        """Crée et valide automatiquement la note de crédit"""
        self.ensure_one()

        if self.credit_note_id:
            return self.credit_note_id

        # Rechercher ou créer le partner
        partner = self._get_or_create_partner()

        # Rechercher le compte comptable
        account = self._get_credit_note_account()

        # Créer la note de crédit
        credit_note_vals = {
            'move_type': 'out_refund',
            'partner_id': partner.id,
            'invoice_date': self.date,
            'ref': self.name,
            'invoice_origin': _("Avoir client %s - Vente %s") % (self.name, self.vente_id.name),
            'narration': _("Type: %s\nMotif: %s\n[Automatisé]") % (
                dict(self._fields['type_avoir'].selection).get(self.type_avoir),
                self.description
            ),
            'invoice_line_ids': [(0, 0, {
                'name': _("Avoir - %s") % self.description,
                'quantity': 1,
                'price_unit': self.montant_avoir,
                'account_id': account.id,
            })],
        }

        credit_note = self.env['account.move'].create(credit_note_vals)
        self.credit_note_id = credit_note.id

        # Validation automatique si configuré
        if auto_post and credit_note.state == 'draft':
            credit_note.action_post()

        self.state = 'comptabilise'

        return credit_note
