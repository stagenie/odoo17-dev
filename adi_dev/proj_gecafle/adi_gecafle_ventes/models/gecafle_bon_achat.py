# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GecafleBonAchat(models.Model):
    _name = 'gecafle.bon.achat'
    _description = "Bon d'Achat Producteur"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, name desc"

    name = fields.Char(string="Numéro", readonly=True, copy=False, default='Nouveau')
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('paye', 'Payé'),
        ('annule', 'Annulé'),
    ], string="État", default='brouillon', tracking=True)

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        required=True,
        readonly=True,
        states={'brouillon': [('readonly', False)]}
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Folio N°",
        required=True,
        readonly=True
    )

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif source",
        required=True,
        readonly=True
    )

    note = fields.Text(string="Description")

    line_ids = fields.One2many(
        'gecafle.bon.achat.line',
        'bon_achat_id',
        string="Lignes",

    )

    montant_total = fields.Monetary(
        string="Montant Total",
        compute='_compute_montant_total',
        store=True,
        currency_field='currency_id'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='company_id.currency_id',
        readonly=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.bon.achat') or 'BA/'
        return super(GecafleBonAchat, self).create(vals)

    @api.depends('line_ids.montant')
    def _compute_montant_total(self):
        for record in self:
            record.montant_total = sum(line.montant for line in record.line_ids)

    def action_validate(self):
        """Passe le bon d'achat en état Validé"""
        for record in self:
            if record.state == 'brouillon':
                # Mise à jour de l'état du récapitulatif lié
                if record.recap_id:
                    record.recap_id.state = 'facture'
                record.state = 'valide'

    def action_mark_paid(self):
        """Marque le bon d'achat comme payé"""
        for record in self:
            if record.state == 'valide':
                record.state = 'paye'

    def action_cancel(self):
        """Annule le bon d'achat"""
        for record in self:
            if record.state not in ('paye'):
                # Retour à l'état validé pour le récapitulatif
                if record.recap_id and record.recap_id.state == 'facture':
                    record.recap_id.state = 'valide'
                record.state = 'annule'

    def action_draft(self):
        """Remet le bon d'achat à l'état brouillon"""
        for record in self:
            if record.state == 'annule':
                record.state = 'brouillon'


class GecafleBonAchatLine(models.Model):
    _name = 'gecafle.bon.achat.line'
    _description = "Ligne de Bon d'Achat"

    bon_achat_id = fields.Many2one(
        'gecafle.bon.achat',
        string="Bon d'Achat",
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string="Description",
        required=True
    )

    quantite = fields.Integer(
        string="Quantité",
        default=1
    )

    prix_unitaire = fields.Monetary(
        string="Prix Unitaire",
        required=True,
        currency_field='currency_id'
    )

    montant = fields.Monetary(
        string="Montant",
        compute='_compute_montant',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='bon_achat_id.currency_id',
        readonly=True
    )

    @api.depends('quantite', 'prix_unitaire')
    def _compute_montant(self):
        for record in self:
            record.montant = record.quantite * record.prix_unitaire
