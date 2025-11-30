# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class GecafleVenteControl(models.Model):
    _inherit = 'gecafle.vente'

    # Champs pour tracer l'automatisation
    is_automated = fields.Boolean(
        string="Créé automatiquement",
        default=False,
        readonly=True
    )

    # ============================================
    # Champs pour les bordereaux (récapitulatifs) des réceptions
    # ============================================
    reception_recap_ids = fields.Many2many(
        'gecafle.reception.recap',
        string="Bordereaux des réceptions",
        compute='_compute_reception_recap_ids',
        store=False
    )

    reception_recap_count = fields.Integer(
        string="Nombre de bordereaux",
        compute='_compute_reception_recap_ids',
        store=False
    )

    # Réceptions uniques utilisées dans cette vente
    vente_reception_ids = fields.Many2many(
        'gecafle.reception',
        string="Réceptions utilisées",
        compute='_compute_vente_reception_ids',
        store=False
    )

    vente_reception_count = fields.Integer(
        string="Nombre de réceptions",
        compute='_compute_vente_reception_ids',
        store=False
    )

    @api.depends('detail_vente_ids.reception_id')
    def _compute_vente_reception_ids(self):
        """Calcule les réceptions uniques utilisées dans cette vente"""
        for vente in self:
            reception_ids = vente.detail_vente_ids.mapped('reception_id')
            vente.vente_reception_ids = reception_ids
            vente.vente_reception_count = len(reception_ids)

    @api.depends('detail_vente_ids.reception_id')
    def _compute_reception_recap_ids(self):
        """Calcule les bordereaux (récapitulatifs) liés aux réceptions de cette vente"""
        for vente in self:
            # Récupérer toutes les réceptions uniques de cette vente
            reception_ids = vente.detail_vente_ids.mapped('reception_id.id')

            if reception_ids:
                # Chercher les récapitulatifs liés à ces réceptions
                recaps = self.env['gecafle.reception.recap'].search([
                    ('reception_id', 'in', reception_ids)
                ])
                vente.reception_recap_ids = recaps
                vente.reception_recap_count = len(recaps)
            else:
                vente.reception_recap_ids = False
                vente.reception_recap_count = 0

    def action_view_reception_recaps(self):
        """Ouvre la liste des bordereaux des réceptions liées à cette vente"""
        self.ensure_one()

        recaps = self.reception_recap_ids

        if not recaps:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Aucun bordereau trouvé pour les réceptions de cette vente.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        action = {
            'name': _('Bordereaux des réceptions'),
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.reception.recap',
            'context': {'create': False},
        }

        if len(recaps) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = recaps.id
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', recaps.ids)]

        return action

    def action_view_vente_receptions(self):
        """Ouvre la liste des réceptions utilisées dans cette vente"""
        self.ensure_one()

        receptions = self.vente_reception_ids

        if not receptions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Aucune réception liée à cette vente.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        action = {
            'name': _('Réceptions de cette vente'),
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.reception',
            'context': {'create': False},
        }

        if len(receptions) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = receptions.id
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', receptions.ids)]

        return action

    can_reset_to_draft = fields.Boolean(
        string="Peut être remis en brouillon",
        compute='_compute_can_reset'
    )

    has_recap_lines = fields.Boolean(
        string="A des lignes dans récap",
        compute='_compute_has_recap_lines',
        store=True
    )

    # NOUVEAU : Champ pour vérifier les avoirs
    has_avoirs = fields.Boolean(
        string="A des avoirs",
        compute='_compute_has_avoirs',
        store=True
    )

    avoir_count = fields.Integer(
        string="Nombre d'avoirs",
        compute='_compute_has_avoirs',
        store=True
    )

    avoir_total_amount = fields.Monetary(
        string="Montant total des avoirs",
        compute='_compute_has_avoirs',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('avoir_ids')
    def _compute_has_avoirs(self):
        """Vérifie si la vente a des avoirs"""
        for vente in self:
            # Rechercher les avoirs liés à cette vente
            avoirs = self.env['gecafle.avoir.client'].search([
                ('vente_id', '=', vente.id),
                ('state', '!=', 'annule')  # Ignorer les avoirs annulés
            ])

            vente.has_avoirs = bool(avoirs)
            vente.avoir_count = len(avoirs)
            vente.avoir_total_amount = sum(avoirs.mapped('montant_avoir'))

    @api.depends('detail_vente_ids')
    def _compute_has_recap_lines(self):
        """Vérifie si des lignes de vente sont dans une récap producteur"""
        for vente in self:
            # CORRECTION : Recherche basée sur les ventes liées aux lignes
            has_lines = False

            # Méthode 1 : Chercher via les récaps existants
            recaps = self.env['gecafle.reception.recap'].search([
                ('sale_line_ids.vente_id', '=', vente.id),
                ('state', '!=', 'annule')
            ])

            if recaps:
                has_lines = True

            vente.has_recap_lines = has_lines

    @api.depends('state', 'has_recap_lines', 'invoice_id', 'has_avoirs', 'reception_recap_count')
    def _compute_can_reset(self):
        """Détermine si la vente peut être remise en brouillon"""
        for vente in self:
            vente.can_reset_to_draft = (
                    vente.state == 'valide' and
                    not vente.has_recap_lines and
                    not vente.has_avoirs and
                    vente.reception_recap_count == 0  # Bloquer si bordereaux existent
            )

    def action_reset_to_draft_advanced(self):
        """Action avancée pour remettre en brouillon avec wizard"""
        self.ensure_one()

        if not self.can_reset_to_draft:
            # NOUVEAU : Vérification des avoirs
            if self.has_avoirs:
                avoir_details = []
                avoirs = self.env['gecafle.avoir.client'].search([
                    ('vente_id', '=', self.id),
                    ('state', '!=', 'annule')
                ])

                for avoir in avoirs:
                    avoir_details.append(
                        f"- {avoir.name} : {avoir.montant_avoir} {self.currency_id.symbol} ({avoir.state})")

                raise UserError(_(
                    "Impossible de remettre en brouillon cette vente.\n\n"
                    "Des avoirs ont été créés pour cette vente :\n"
                    "%s\n"
                    "Nombre d'avoirs : %s\n"
                    "Montant total : %s %s\n\n"
                    "Options disponibles :\n"
                    "1. Annuler d'abord tous les avoirs\n"
                    "2. Créer un avoir compensatoire\n"
                    "3. Créer une nouvelle vente corrective"
                ) % (
                                    '\n'.join(avoir_details),
                                    self.avoir_count,
                                    self.avoir_total_amount,
                                    self.currency_id.symbol
                                ))

            # Vérification des bordereaux (récaps) liés aux réceptions
            if self.has_recap_lines or self.reception_recap_count > 0:
                # Récupérer les détails des bordereaux
                recap_details = []
                recaps = self.reception_recap_ids

                for recap in recaps:
                    status_paiement = dict(recap._fields['payment_state'].selection).get(recap.payment_state, recap.payment_state)
                    recap_details.append(
                        f"  - {recap.name} | Producteur: {recap.producteur_id.name} | "
                        f"Net: {recap.net_a_payer:.2f} {self.currency_id.symbol} | "
                        f"État: {recap.state} | Paiement: {status_paiement}"
                    )

                raise UserError(_(
                    "Impossible de remettre en brouillon cette vente.\n\n"
                    "Cette vente est liée à %d bordereau(x) producteur:\n"
                    "%s\n\n"
                    "Options disponibles:\n"
                    "─────────────────────────────────────────────────\n"
                    "1. Créer un avoir client (bouton 'Créer un avoir')\n\n"
                    "2. Supprimer manuellement les bordereaux concernés:\n"
                    "   → Cliquer sur le bouton 'Bordereaux' en haut du formulaire\n"
                    "   → Pour chaque bordereau:\n"
                    "      • Supprimer les paiements/avances liés\n"
                    "      • Supprimer la facture fournisseur si existante\n"
                    "      • Puis supprimer le bordereau\n"
                    "   → Revenir sur cette vente et réessayer"
                ) % (
                    self.reception_recap_count,
                    '\n'.join(recap_details) if recap_details else '  (aucun détail disponible)'
                ))
            else:
                raise UserError(_("Cette vente ne peut pas être remise en brouillon."))

        # Ouvrir le wizard
        return {
            'name': _('Remise en brouillon de la vente'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.vente.reset.wizard',
            'target': 'new',
            'context': {
                'default_vente_id': self.id,
                'default_has_invoice': bool(self.invoice_id),
                'default_has_payments': bool(
                    self.invoice_id and
                    self.invoice_id.payment_state != 'not_paid'
                ),
            }
        }

    # ============================================
    # Modification directe du prix sur ventes facturées
    # ============================================

    can_edit_price = fields.Boolean(
        string="Peut modifier le prix",
        compute='_compute_can_edit_price',
        help="Indique si le prix des lignes peut être modifié directement"
    )

    has_vendor_invoice_on_recap = fields.Boolean(
        string="A une facture fournisseur sur récap",
        compute='_compute_can_edit_price',
    )

    @api.depends('state', 'invoice_id', 'invoice_id.payment_state', 'reception_recap_ids.invoice_id')
    def _compute_can_edit_price(self):
        """
        Détermine si le prix peut être modifié directement.

        Conditions pour autoriser :
        1. Vente validée avec facture
        2. Facture sans paiement (payment_state == 'not_paid')
        3. Pas de facture fournisseur sur les récaps liées
        """
        for vente in self:
            can_edit = False
            has_vendor_invoice = False

            if vente.state == 'valide' and vente.invoice_id:
                # Vérifier si facture non payée
                if vente.invoice_id.payment_state == 'not_paid':
                    can_edit = True

                    # Vérifier les récaps liées
                    recaps = self.env['gecafle.reception.recap'].search([
                        ('sale_line_ids.vente_id', '=', vente.id)
                    ])

                    for recap in recaps:
                        if recap.invoice_id:
                            can_edit = False
                            has_vendor_invoice = True
                            break

            elif vente.state == 'brouillon':
                # Toujours éditable en brouillon
                can_edit = True

            vente.can_edit_price = can_edit
            vente.has_vendor_invoice_on_recap = has_vendor_invoice

    def write(self, vals):
        """
        Surcharge pour autoriser la modification du prix sur les ventes facturées sans paiement.

        Autorise la modification si :
        - Le contexte 'allow_price_edit' ou 'allow_adjustment' est présent
        - OU les seuls champs modifiés sont 'detail_vente_ids' avec uniquement des modifications de prix
          ET les conditions sont remplies (facture non payée, pas de facture fournisseur sur récap)
        """
        # Si le contexte autorise déjà, on passe
        if self.env.context.get('allow_price_edit') or self.env.context.get('allow_adjustment'):
            return super(GecafleVenteControl, self.with_context(allow_adjustment=True)).write(vals)

        # Vérifier si c'est une modification de prix autorisée via les lignes de vente
        if 'detail_vente_ids' in vals and len(vals) == 1:
            # Vérifier si toutes les modifications sont uniquement sur prix_unitaire
            if self._is_only_price_modification(vals['detail_vente_ids']):
                # Vérifier les conditions pour chaque vente
                for record in self:
                    can_edit, message = record._can_edit_price_on_lines()
                    if not can_edit:
                        raise UserError(message)

                # Extraire les IDs des lignes modifiées et leurs anciens prix AVANT le write
                lines_to_update = {}
                for command in vals['detail_vente_ids']:
                    if command[0] == 1 and 'prix_unitaire' in command[2]:
                        line_id = command[1]
                        line = self.env['gecafle.details_ventes'].browse(line_id)
                        lines_to_update[line_id] = {
                            'old_price': line.prix_unitaire,
                            'new_price': command[2]['prix_unitaire'],
                            'line': line,
                        }

                # Toutes les conditions sont remplies, autoriser la modification
                result = super(GecafleVenteControl, self.with_context(allow_adjustment=True)).write(vals)

                # Après le write, mettre à jour la facture et la récap
                for line_id, data in lines_to_update.items():
                    line = data['line']
                    # Recharger la ligne pour avoir les valeurs recalculées
                    line.invalidate_recordset()

                    # Mettre à jour la facture
                    self._update_invoice_line_for_price_change(line)

                    # Mettre à jour la récap
                    self._update_recap_for_price_change(line)

                    # Logger la modification
                    self._log_price_modification(line, data['old_price'], data['new_price'])

                return result

        return super(GecafleVenteControl, self).write(vals)

    def _update_invoice_line_for_price_change(self, detail_line):
        """Met à jour la ligne de facture correspondante après modification du prix."""
        if not self.invoice_id:
            return

        invoice = self.invoice_id
        was_posted = invoice.state == 'posted'

        # Trouver la ligne de facture correspondante
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda l: l.gecafle_detail_vente_id.id == detail_line.id
        )

        if not invoice_line:
            _logger.warning(f"Ligne de facture non trouvée pour detail_vente {detail_line.id}")
            return

        try:
            # Passer la facture en brouillon si postée
            # Utiliser force_gecafle_update pour bypasser la protection
            if was_posted:
                invoice.with_context(force_gecafle_update=True).button_draft()

            # Mettre à jour la ligne de facture
            invoice_line.with_context(check_move_validity=False).write({
                'price_unit': detail_line.prix_unitaire,
                'prix_unitaire': detail_line.prix_unitaire,
                'montant_net': detail_line.montant_net,
                'montant_commission': detail_line.montant_commission,
            })

            # Revalider la facture si elle était postée
            if was_posted:
                invoice.with_context(force_gecafle_update=True).action_post()

            _logger.info(f"Facture {invoice.name} mise à jour - prix={detail_line.prix_unitaire}")

        except Exception as e:
            _logger.error(f"Erreur mise à jour facture: {str(e)}")
            raise UserError(_("Erreur lors de la mise à jour de la facture:\n%s") % str(e))

    def _update_recap_for_price_change(self, detail_line):
        """Met à jour les récaps producteur après modification du prix."""
        # Chercher les récaps liées à cette réception
        recaps = self.env['gecafle.reception.recap'].search([
            ('reception_id', '=', detail_line.reception_id.id),
            ('state', 'in', ['brouillon', 'valide'])
        ])

        for recap in recaps:
            # Mettre à jour les lignes de vente dans la récap
            sale_lines = recap.sale_line_ids.filtered(
                lambda l: l.vente_id.id == self.id and
                          l.produit_id.id == detail_line.produit_id.id and
                          l.qualite_id.id == (detail_line.qualite_id.id if detail_line.qualite_id else False)
            )

            for sale_line in sale_lines:
                sale_line.write({
                    'prix_unitaire': detail_line.prix_unitaire,
                    'montant_net': detail_line.montant_net,
                    'montant_commission': detail_line.montant_commission,
                })

            # Regénérer les lignes récapitulatives
            recap.generate_recap_lines()

            _logger.info(f"Récap {recap.name} mise à jour - totaux recalculés")

            # Message dans le chatter de la récap
            recap.message_post(
                body=_(
                    "📝 Mise à jour automatique suite à modification de prix\n"
                    "Vente: %s\nProduit: %s\nNouveau prix: %.2f"
                ) % (self.name, detail_line.produit_id.name, detail_line.prix_unitaire),
                message_type='notification'
            )

    def _log_price_modification(self, detail_line, old_price, new_price):
        """Enregistre la modification de prix dans le chatter."""
        self.message_post(
            body=_(
                "💰 <b>Modification de prix</b>\n"
                "<ul>"
                "<li>Produit: %s</li>"
                "<li>Qualité: %s</li>"
                "<li>Ancien prix: %.2f</li>"
                "<li>Nouveau prix: %.2f</li>"
                "<li>Nouveau montant net: %.2f</li>"
                "</ul>"
                "Facture et récap mises à jour automatiquement."
            ) % (
                detail_line.produit_id.name,
                detail_line.qualite_id.name if detail_line.qualite_id else '-',
                old_price,
                new_price,
                detail_line.montant_net
            ),
            message_type='comment'
        )

    def _is_only_price_modification(self, commands):
        """
        Vérifie si les commandes One2many ne modifient que le prix_unitaire.

        Format des commandes :
        - (0, 0, vals) : créer
        - (1, id, vals) : modifier
        - (2, id) : supprimer
        - (4, id) : lier
        - (5,) : supprimer tous les liens
        - (6, 0, ids) : remplacer
        """
        allowed_fields = {'prix_unitaire'}

        for command in commands:
            if command[0] == 1:  # Modification d'une ligne existante
                modified_fields = set(command[2].keys()) if len(command) > 2 and command[2] else set()
                # Vérifier que seuls les champs autorisés sont modifiés
                if not modified_fields.issubset(allowed_fields):
                    return False
            elif command[0] in (0, 2, 5, 6):  # Création, suppression, remplacement
                # Ces opérations ne sont pas autorisées
                return False
            # command[0] == 4 (lier) est OK car ça ne modifie rien

        return True

    def _can_edit_price_on_lines(self):
        """
        Vérifie si la modification du prix est autorisée sur cette vente.

        Conditions :
        1. Vente validée avec facture
        2. Facture non payée
        3. Pas de facture fournisseur sur les récaps liées
        """
        self.ensure_one()

        # Si pas validée ou pas de facture, on laisse passer (sera géré ailleurs)
        if self.state != 'valide':
            return True, "OK"

        if not self.invoice_id:
            return True, "OK"

        # Vérifier si facture a des paiements
        if self.invoice_id.payment_state != 'not_paid':
            return False, _(
                "Impossible de modifier le prix : la facture %s a des paiements.\n"
                "État de paiement : %s"
            ) % (self.invoice_id.name, self.invoice_id.payment_state)

        # Vérifier les récaps liées
        recaps = self.env['gecafle.reception.recap'].search([
            ('sale_line_ids.vente_id', '=', self.id)
        ])

        for recap in recaps:
            if recap.invoice_id:
                return False, _(
                    "Impossible de modifier le prix : le bordereau %s a une facture fournisseur (%s).\n"
                    "Vous devez d'abord supprimer la facture fournisseur et ses paiements."
                ) % (recap.name, recap.invoice_id.name)

        return True, "OK"

