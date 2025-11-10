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

    @api.depends('state', 'has_recap_lines', 'invoice_id', 'has_avoirs')
    def _compute_can_reset(self):
        """Détermine si la vente peut être remise en brouillon"""
        for vente in self:
            vente.can_reset_to_draft = (
                    vente.state == 'valide' and
                    not vente.has_recap_lines and
                    not vente.has_avoirs  # AJOUT : Bloquer si avoirs existent
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

            if self.has_recap_lines:
                raise UserError(_(
                    "Cette vente a des lignes dans une récapitulation producteur.\n"
                    "Impossible de la remettre en brouillon."
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


