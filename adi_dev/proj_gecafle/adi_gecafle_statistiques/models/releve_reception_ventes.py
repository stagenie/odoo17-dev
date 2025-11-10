# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class GecafleReleveReceptionVentes(models.Model):
    _name = 'gecafle.releve.reception.ventes'
    _description = 'Relevé Réceptions et leurs Ventes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'

    name = fields.Char(
        string="Numéro",
        readonly=True,
        copy=False,
        default='Nouveau'
    )

    date_creation = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
        readonly=True
    )

    date_debut = fields.Date(
        string="Date début",
        required=True,
        default=fields.Date.context_today
    )

    date_fin = fields.Date(
        string="Date fin",
        required=True,
        default=fields.Date.context_today
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        help="Si vide, tous les producteurs"
    )

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('confirme', 'Confirmé'),
    ], string="État", default='brouillon', tracking=True)

    line_ids = fields.One2many(
        'gecafle.releve.reception.ventes.line',
        'releve_id',
        string="Lignes du relevé"
    )

    # Totaux
    total_general_ventes = fields.Monetary(
        string="Total Général Ventes",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    total_general_commission = fields.Monetary(
        string="Total Commission",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    total_general_net = fields.Monetary(
        string="Total Net à Payer",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.releve.reception.ventes') or 'RRV/'
        return super().create(vals)

    @api.depends('line_ids.total_ventes', 'line_ids.total_commission')
    def _compute_totals(self):
        for record in self:
            record.total_general_ventes = sum(record.line_ids.mapped('total_ventes'))
            record.total_general_commission = sum(record.line_ids.mapped('total_commission'))
            record.total_general_net = sum(record.line_ids.mapped('net_a_payer'))

    def action_generate_releve(self):
        """Génère le relevé des réceptions et ventes"""
        self.ensure_one()

        # Supprimer les lignes existantes
        self.line_ids.unlink()

        # Domaine de recherche
        domain = [
            ('state', '=', 'confirmee'),
            ('reception_date', '>=', fields.Datetime.to_datetime(self.date_debut)),
            ('reception_date', '<=', fields.Datetime.to_datetime(self.date_fin).replace(hour=23, minute=59, second=59))
        ]

        if self.producteur_id:
            domain.append(('producteur_id', '=', self.producteur_id.id))

        receptions = self.env['gecafle.reception'].search(domain, order='reception_date')

        for reception in receptions:
            # Récupérer les ventes liées
            ventes = self.env['gecafle.details_ventes'].search([
                ('reception_id', '=', reception.id),
                ('vente_id.state', '=', 'valide')
            ])

            if ventes:
                # Créer une ligne pour cette réception
                line_vals = {
                    'releve_id': self.id,
                    'reception_id': reception.id,
                    'date_reception': reception.reception_date,
                    'producteur_id': reception.producteur_id.id,
                    'line_reception_ids': [],
                    'line_vente_ids': []
                }

                # Ajouter les détails de réception
                for rec_line in reception.details_reception_ids:
                    line_vals['line_reception_ids'].append((0, 0, {
                        'produit': rec_line.designation_id.name,
                        'nombre': rec_line.qte_colis_recue,
                        'calibre': rec_line.qualite_id.name if rec_line.qualite_id else '',
                        'emballage': rec_line.type_colis_id.name,
                    }))

                # Ajouter les détails de vente AVEC LE TAUX ET MONTANT DE COMMISSION
                for vente_line in ventes:
                    line_vals['line_vente_ids'].append((0, 0, {
                        'produit': vente_line.produit_id.name,
                        'nombre': vente_line.nombre_colis,
                        'calibre': vente_line.qualite_id.name if vente_line.qualite_id else '',
                        'emballage': vente_line.type_colis_id.name,
                        'poids': vente_line.poids_net,
                        'prix_unitaire': vente_line.prix_unitaire,
                        'prix_total': vente_line.montant_net,
                        # AJOUT DES CHAMPS COMMISSION
                        'taux_commission': vente_line.taux_commission,
                        'montant_commission': vente_line.montant_commission,
                    }))

                self.env['gecafle.releve.reception.ventes.line'].create(line_vals)

        self.state = 'confirme'
        return True

    def action_print_releve(self):
        """Imprime le relevé"""
        self.ensure_one()
        return self.env.ref('adi_gecafle_statistiques.action_report_releve_reception_ventes').report_action(self)

    def action_print_releve_pages(self):
        """Imprime le relevé"""
        self.ensure_one()
        return self.env.ref('adi_gecafle_statistiques.action_report_releve_reception_ventes_pages').report_action(self)


class GecafleReleveReceptionVentesLine(models.Model):
    _name = 'gecafle.releve.reception.ventes.line'
    _description = 'Ligne de Relevé Réception-Ventes'
    _order = 'date_reception'

    releve_id = fields.Many2one(
        'gecafle.releve.reception.ventes',
        string="Relevé",
        required=True,
        ondelete='cascade'
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True
    )

    date_reception = fields.Datetime(string="Date réception")
    producteur_id = fields.Many2one('gecafle.producteur', string="Producteur")

    line_reception_ids = fields.One2many(
        'gecafle.releve.reception.detail',
        'line_id',
        string="Détails réception"
    )

    line_vente_ids = fields.One2many(
        'gecafle.releve.vente.detail',
        'line_id',
        string="Détails ventes"
    )

    total_ventes = fields.Monetary(
        string="Total ventes",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    total_commission = fields.Monetary(
        string="Commission",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    net_a_payer = fields.Monetary(
        string="Net à payer",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='releve_id.currency_id'
    )

    @api.depends('line_vente_ids.prix_total', 'line_vente_ids.montant_commission')
    def _compute_totals(self):
        """MÉTHODE CORRIGÉE : Utilise les vrais montants de commission"""
        for record in self:
            record.total_ventes = sum(record.line_vente_ids.mapped('prix_total'))
            # CORRECTION : Utiliser le montant de commission réel au lieu du 10% fixe
            record.total_commission = sum(record.line_vente_ids.mapped('montant_commission'))
            record.net_a_payer = record.total_ventes - record.total_commission


class GecafleReleveReceptionDetail(models.Model):
    _name = 'gecafle.releve.reception.detail'
    _description = 'Détail Réception dans Relevé'

    line_id = fields.Many2one(
        'gecafle.releve.reception.ventes.line',
        string="Ligne relevé",
        required=True,
        ondelete='cascade'
    )

    produit = fields.Char(string="Produit")
    nombre = fields.Integer(string="Nombre")
    calibre = fields.Char(string="Calibre")
    emballage = fields.Char(string="Emballage")


class GecafleReleveVenteDetail(models.Model):
    _name = 'gecafle.releve.vente.detail'
    _description = 'Détail Vente dans Relevé'

    line_id = fields.Many2one(
        'gecafle.releve.reception.ventes.line',
        string="Ligne relevé",
        required=True,
        ondelete='cascade'
    )

    produit = fields.Char(string="Produit")
    nombre = fields.Integer(string="Nombre")
    calibre = fields.Char(string="Calibre")
    emballage = fields.Char(string="Emballage")
    poids = fields.Float(string="Poids", digits=(16, 2))
    prix_unitaire = fields.Float(string="Prix Unitaire", digits=(16, 2))
    prix_total = fields.Monetary(
        string="Prix Total",
        currency_field='currency_id'
    )

    # AJOUT DES CHAMPS POUR STOCKER LA COMMISSION RÉELLE
    taux_commission = fields.Float(
        string="Taux Commission",
        digits=(5, 2),
        help="Taux de commission appliqué en %"
    )

    montant_commission = fields.Monetary(
        string="Montant Commission",
        currency_field='currency_id',
        help="Montant de commission calculé"
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='line_id.currency_id'
    )
