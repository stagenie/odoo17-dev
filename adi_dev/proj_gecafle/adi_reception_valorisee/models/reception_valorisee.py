# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleReceptionValorisee(models.Model):
    _inherit = 'gecafle.reception'

    # Toggle principal pour identifier une réception valorisée
    is_achat_valorise = fields.Boolean(
        string="Achat Valorisé",
        default=False,
        tracking=True,
        help="Cochez pour gérer cette réception comme un achat avec valorisation"
    )

    # Totaux pour les poids
    total_poids_brut = fields.Float(
        string="Total Poids Brut",
        compute='_compute_totaux_valorises',
        store=True,
        digits=(16, 2)
    )

    total_poids_colis = fields.Float(
        string="Total Poids Colis",
        compute='_compute_totaux_valorises',
        store=True,
        digits=(16, 2)
    )

    total_poids_net = fields.Float(
        string="Total Poids Net",
        compute='_compute_totaux_valorises',
        store=True,
        digits=(16, 2)
    )

    # Totaux financiers
    montant_total_brut = fields.Monetary(
        string="Montant Total Brut",
        compute='_compute_totaux_valorises',
        store=True,
        currency_field='currency_id'
    )

    montant_total_emballages = fields.Monetary(
        string="Montant Emballages Achetés",
        compute='_compute_totaux_valorises',
        store=True,
        currency_field='currency_id'
    )

    remise_globale = fields.Monetary(
        string="Remise Globale",
        default=0.0,
        tracking=True,
        help="Remise manuelle pour arrondir ou accorder une remise producteur"
    )

    montant_net_a_payer = fields.Monetary(
        string="Net à Payer",
        compute='_compute_totaux_valorises',
        store=True,
        currency_field='currency_id'
    )

    # Lien vers la facture fournisseur
    invoice_id = fields.Many2one(
        'account.move',
        string="Facture Fournisseur",
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    invoice_count = fields.Integer(
        string="Nombre de factures",
        compute='_compute_invoice_count'
    )

    @api.depends('invoice_id')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 1 if record.invoice_id else 0

    @api.depends(
        'is_achat_valorise',
        'details_reception_ids.poids_brut',
        'details_reception_ids.poids_colis',
        'details_reception_ids.poids_net',
        'details_reception_ids.montant_ligne',
        'details_emballage_reception_ids.is_achete',  # Champ existant
        'details_emballage_reception_ids.montant_achat',  # Champ existant (au lieu de montant_emballage)
        'remise_globale'
    )
    def _compute_totaux_valorises(self):
        """Calcule tous les totaux de la réception valorisée"""
        for record in self:
            if record.is_achat_valorise:
                # Calcul des poids
                record.total_poids_brut = sum(record.details_reception_ids.mapped('poids_brut'))
                record.total_poids_colis = sum(record.details_reception_ids.mapped('poids_colis'))
                record.total_poids_net = sum(record.details_reception_ids.mapped('poids_net'))

                # Calcul des montants
                record.montant_total_brut = sum(record.details_reception_ids.mapped('montant_ligne'))

                # Montant des emballages achetés - UTILISE LE CHAMP EXISTANT
                record.montant_total_emballages = sum(
                    line.montant_achat  # Champ existant du module adi_reception_extended
                    for line in record.details_emballage_reception_ids
                    if line.is_achete  # Champ existant du module adi_reception_extended
                )

                # Net à payer = Total brut - Emballages - Remise
                record.montant_net_a_payer = (
                        record.montant_total_brut -
                        record.montant_total_emballages -
                        record.remise_globale
                )
            else:
                # Réinitialiser si ce n'est pas un achat valorisé
                record.total_poids_brut = 0
                record.total_poids_colis = 0
                record.total_poids_net = 0
                record.montant_total_brut = 0
                record.montant_total_emballages = 0
                record.montant_net_a_payer = 0

    def action_create_supplier_invoice(self):
        """Crée une facture fournisseur à partir de la réception valorisée avec gestion des avances"""
        self.ensure_one()

        if not self.is_achat_valorise:
            raise UserError(_("Cette action n'est disponible que pour les réceptions valorisées."))

        if self.state != 'confirmee':
            raise UserError(_("La réception doit être confirmée avant de créer une facture."))

        if self.invoice_id:
            raise UserError(_("Une facture existe déjà pour cette réception."))

        # Créer ou trouver le partner
        partner = self._get_or_create_partner()

        # Préparer les lignes de facture
        invoice_lines = []

        # Lignes pour les produits
        for line in self.details_reception_ids:
            if line.montant_ligne > 0:
                invoice_lines.append((0, 0, {
                    'name': "%s - %s" % (
                        line.designation_id.name,
                        line.qualite_id.name if line.qualite_id else ''
                    ),
                    'quantity': line.poids_net or line.qte_colis_recue,
                    'price_unit': line.prix_unitaire_achat,
                }))

        # Ligne pour les emballages achetés (en négatif car c'est une déduction)
        if self.montant_total_emballages > 0:
            invoice_lines.append((0, 0, {
                'name': _("Emballages achetés"),
                'quantity': 1,
                'price_unit': -self.montant_total_emballages,
            }))

        # Ligne pour la remise si elle existe
        if self.remise_globale > 0:
            invoice_lines.append((0, 0, {
                'name': _("Remise accordée"),
                'quantity': 1,
                'price_unit': -self.remise_globale,
            }))

        # Créer la narration avec les détails des avances
        narration_parts = [
            _("Facture créée depuis la réception valorisée %s") % self.name,
            _("Net à payer: %s") % self.montant_net_a_payer
        ]

        # Ajouter les informations sur les avances si elles existent
        if self.avance_producteur > 0:
            narration_parts.append(_("Avance producteur: %s") % self.avance_producteur)

        # Vérifier si le champ avance_transport existe
        if hasattr(self, 'avance_transport') and self.avance_transport > 0:
            narration_parts.append(_("Avance transport: %s") % self.avance_transport)

        narration_text = '\n'.join(narration_parts)

        # Créer la facture
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,
            'invoice_origin': _("Réception valorisée %s") % self.name,
            'invoice_line_ids': invoice_lines,
            'narration': narration_text,
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id

        # Message de confirmation avec détails
        message_parts = [
            _("Facture fournisseur créée : %s") % invoice.name,
            _("Montant total: %s") % self.montant_net_a_payer
        ]

        if self.avance_producteur > 0:
            message_parts.append(_("Avance producteur à déduire: %s") % self.avance_producteur)

        if hasattr(self, 'avance_transport') and self.avance_transport > 0:
            message_parts.append(_("Avance transport à déduire: %s") % self.avance_transport)

        self.message_post(body='<br/>'.join(message_parts))

        # Ouvrir la facture
        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }
    def _get_or_create_partner(self):
        """Recherche ou crée un res.partner pour le producteur"""
        self.ensure_one()

        partner = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        return partner

    def action_view_invoice(self):
        """Ouvre la facture liée"""
        self.ensure_one()

        if not self.invoice_id:
            raise UserError(_("Aucune facture n'est liée à cette réception."))

        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    def action_print_bon_valorise(self):
        """Imprime le bon de réception valorisé en français"""
        self.ensure_one()
        return self.env.ref('adi_reception_valorisee.action_report_bon_reception_valorise').report_action(self)

    def action_print_bon_valorise_ar(self):
        """Imprime le bon de réception valorisé en arabe"""
        self.ensure_one()
        return self.env.ref('adi_reception_valorisee.action_report_bon_reception_valorise_ar').report_action(self)

    def action_select_all_emballages(self):
        """Marque tous les emballages comme achetés"""
        self.ensure_one()

        if not self.is_achat_valorise:
            raise UserError(_("Cette action n'est disponible que pour les réceptions valorisées."))

        # Parcourir toutes les lignes d'emballage
        for line in self.details_emballage_reception_ids:
            line.is_achete = True

            # Initialiser la quantité achetée si elle est vide
            if not line.qte_achetee:
                # Par défaut, prendre la quantité sortante (ou entrante si pas de sortante)
                line.qte_achetee = line.qte_sortantes or line.qte_entrantes or 0

            # Initialiser le prix unitaire avec le prix par défaut de l'emballage
            if not line.prix_unitaire_achat and line.emballage_id:
                line.prix_unitaire_achat = line.emballage_id.price_unit or 0

        # Message de confirmation
        self.message_post(
            body=_("✅ Tous les emballages ont été marqués comme achetés"),
            subtype_xmlid='mail.mt_note'
        )

        # Notification utilisateur
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Emballages sélectionnés'),
                'message': _('Tous les emballages ont été marqués comme achetés'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_deselect_all_emballages(self):
        """Démarque tous les emballages achetés"""
        self.ensure_one()

        if not self.is_achat_valorise:
            raise UserError(_("Cette action n'est disponible que pour les réceptions valorisées."))

        # Parcourir toutes les lignes d'emballage
        for line in self.details_emballage_reception_ids:
            line.is_achete = False
            line.qte_achetee = 0
            line.prix_unitaire_achat = 0
            # Le montant_achat sera recalculé automatiquement via le compute

        # Message de confirmation
        self.message_post(
            body=_("❌ Tous les emballages ont été désélectionnés"),
            subtype_xmlid='mail.mt_note'
        )

        # Notification utilisateur
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Emballages désélectionnés'),
                'message': _('Tous les emballages ont été démarqués'),
                'type': 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.onchange('is_achat_valorise')
    def _onchange_is_achat_valorise(self):
        """Applique le comportement par défaut selon le type de réception"""
        if self.is_achat_valorise:
            # Pour les réceptions valorisées : tout acheter par défaut
            for line in self.details_emballage_reception_ids:
                # Ne modifier que si pas déjà défini pour éviter d'écraser les valeurs manuelles
                if not line.is_achete:
                    # Appliquer la logique selon le type d'emballage
                    if line.emballage_id and line.emballage_id.non_returnable:
                        line.is_achete = True
                        if not line.qte_achetee:
                            line.qte_achetee = line.qte_sortantes or line.qte_entrantes or 0
                        if not line.prix_unitaire_achat:
                            line.prix_unitaire_achat = line.emballage_id.price_unit or 0
                    else:
                        # Emballage consigné : non acheté par défaut
                        line.is_achete = False
        else:
            # Pour les réceptions non valorisées : ne rien acheter par défaut
            for line in self.details_emballage_reception_ids:
                line.is_achete = False
                line.qte_achetee = 0
                line.prix_unitaire_achat = 0

    # ========== MÉTHODE OPTIONNELLE POUR APPLIQUER LA LOGIQUE PAR DÉFAUT ==========

    def action_apply_default_emballages(self):
        """Applique la logique par défaut pour les emballages selon leur type"""
        self.ensure_one()

        if not self.is_achat_valorise:
            raise UserError(_("Cette action n'est disponible que pour les réceptions valorisées."))

        count_achete = 0
        count_non_achete = 0

        for line in self.details_emballage_reception_ids:
            if line.emballage_id:
                if line.emballage_id.non_returnable:
                    # Non rendu = Acheté
                    line.is_achete = True
                    if not line.qte_achetee:
                        line.qte_achetee = line.qte_sortantes or line.qte_entrantes or 0
                    if not line.prix_unitaire_achat:
                        line.prix_unitaire_achat = line.emballage_id.price_unit or 0
                    count_achete += 1
                else:
                    # Rendu = Non acheté
                    line.is_achete = False
                    line.qte_achetee = 0
                    line.prix_unitaire_achat = 0
                    count_non_achete += 1

        # Message détaillé
        message = _("🔄 Logique par défaut appliquée :\n")
        message += _("• %d emballage(s) non rendu(s) → Acheté(s)\n") % count_achete
        message += _("• %d emballage(s) consigné(s) → Non acheté(s)") % count_non_achete

        self.message_post(body=message, subtype_xmlid='mail.mt_note')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Logique par défaut appliquée'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }


