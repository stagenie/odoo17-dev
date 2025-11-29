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


