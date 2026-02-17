# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class RonDailyProduction(models.Model):
    """
    Production Journalière RON.

    Ce modèle gère une journée de production complète incluant:
    - Les consommations de matières premières
    - Les rebuts récupérables (vendables)
    - La pâte récupérable (stock AVCO)
    - Les produits finis (SOLO/CLASSICO ou Sandwich Grand Format)
    - Le calcul automatique du coût de revient

    Deux modes de production:
    - solo_classico: SOLO + CLASSICO avec ratio de coût
    - sandwich_gf: Sandwich Grand Format seul (sans ratio)
    """
    _name = 'ron.daily.production'
    _description = 'Production Journalière RON'
    _rec_name = 'name'
    _order = 'production_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ================== IDENTIFICATION ==================
    name = fields.Char(
        string='Référence',
        required=True,
        default='Nouveau',
        copy=False,
        readonly=True,
        tracking=True
    )

    production_date = fields.Date(
        string='Date de Production',
        required=True,
        default=fields.Date.today,
        tracking=True,
        index=True
    )

    # ================== TYPE DE PRODUCTION ==================
    production_type = fields.Selection([
        ('solo_classico', 'SOLO / CLASSICO'),
        ('sandwich_gf', 'Sandwich Grand Format'),
    ], string='Type de Production', required=True, default='solo_classico',
       tracking=True,
       help="SOLO/CLASSICO: Produits avec ratio de coût\nSandwich GF: Produit seul sans ratio")

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='company_id.currency_id',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé'),
        ('done', 'Terminé')
    ], string='État', default='draft', tracking=True)

    # ================== LIGNES DE CONSOMMATION ==================
    consumption_line_ids = fields.One2many(
        'ron.consumption.line',
        'daily_production_id',
        string='Consommations du Jour'
    )

    # ================== REBUTS ET PÂTE ==================
    scrap_line_ids = fields.One2many(
        'ron.scrap.line',
        'daily_production_id',
        string='Rebuts Récupérables',
        domain=[('scrap_type', '=', 'scrap_recoverable')]
    )

    paste_line_ids = fields.One2many(
        'ron.scrap.line',
        'daily_production_id',
        string='Pâte Récupérable',
        domain=[('scrap_type', '=', 'paste_recoverable')]
    )

    # ================== PRODUITS FINIS ==================
    finished_product_ids = fields.One2many(
        'ron.finished.product',
        'daily_production_id',
        string='Produits Finis'
    )

    # ================== COÛTS D'EMBALLAGE - SOLO/CLASSICO ==================
    # Emballage SOLO
    emballage_solo_qty = fields.Float(
        string='Qté Emb. SOLO',
        help="Quantité d'emballages SOLO consommés"
    )
    emballage_solo_unit_cost = fields.Monetary(
        string='Prix Unit. Emb. SOLO',
        currency_field='currency_id',
        help="Prix unitaire de l'emballage SOLO"
    )
    emballage_solo_cost = fields.Monetary(
        string='Coût Emb. SOLO',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    # Emballage CLASSICO
    emballage_classico_qty = fields.Float(
        string='Qté Emb. CLASSICO',
        help="Quantité d'emballages CLASSICO consommés"
    )
    emballage_classico_unit_cost = fields.Monetary(
        string='Prix Unit. Emb. CLASSICO',
        currency_field='currency_id',
        help="Prix unitaire de l'emballage CLASSICO"
    )
    emballage_classico_cost = fields.Monetary(
        string='Coût Emb. CLASSICO',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    # Film SOLO
    film_solo_qty = fields.Float(
        string='Qté Film SOLO (kg)',
        help="Quantité de film SOLO consommé en kg"
    )
    film_solo_unit_cost = fields.Monetary(
        string='Prix/kg Film SOLO',
        currency_field='currency_id',
        help="Prix au kg du film SOLO"
    )
    film_solo_cost = fields.Monetary(
        string='Coût Film SOLO',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    # Film CLASSICO
    film_classico_qty = fields.Float(
        string='Qté Film CLASSICO (kg)',
        help="Quantité de film CLASSICO consommé en kg"
    )
    film_classico_unit_cost = fields.Monetary(
        string='Prix/kg Film CLASSICO',
        currency_field='currency_id',
        help="Prix au kg du film CLASSICO"
    )
    film_classico_cost = fields.Monetary(
        string='Coût Film CLASSICO',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    # ================== COÛTS D'EMBALLAGE - SANDWICH GF ==================
    emballage_sandwich_qty = fields.Float(
        string='Qté Emb. Sandwich',
        help="Quantité d'emballages Sandwich GF consommés"
    )
    emballage_sandwich_unit_cost = fields.Monetary(
        string='Prix Unit. Emb. Sandwich',
        currency_field='currency_id',
        help="Prix unitaire de l'emballage Sandwich GF"
    )
    emballage_sandwich_cost = fields.Monetary(
        string='Coût Emb. Sandwich',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    film_sandwich_qty = fields.Float(
        string='Qté Film Sandwich (kg)',
        help="Quantité de film Sandwich GF consommé en kg"
    )
    film_sandwich_unit_cost = fields.Monetary(
        string='Prix/kg Film Sandwich',
        currency_field='currency_id',
        help="Prix au kg du film Sandwich GF"
    )
    film_sandwich_cost = fields.Monetary(
        string='Coût Film Sandwich',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id'
    )

    # ================== TOTAUX EMBALLAGE ==================
    total_emballage_cost = fields.Monetary(
        string='Total Emballages',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id',
        help="Total des coûts d'emballages (cartons)"
    )

    total_film_cost = fields.Monetary(
        string='Total Films',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id',
        help="Total des coûts de films"
    )

    # ================== TOTAUX CONSOMMATION ==================
    total_consumption_cost = fields.Monetary(
        string='Coût Total Consommation',
        compute='_compute_consumption_totals',
        store=True,
        currency_field='currency_id',
        help="Somme des coûts de toutes les consommations"
    )

    total_consumption_weight = fields.Float(
        string='Poids Total Consommation (kg)',
        compute='_compute_consumption_totals',
        store=True,
        digits='Product Unit of Measure',
        help="Somme des poids de toutes les consommations"
    )

    cost_per_kg = fields.Monetary(
        string='Coût par Kg',
        compute='_compute_consumption_totals',
        store=True,
        currency_field='currency_id',
        help="Coût total consommation / Poids total consommation"
    )

    # ================== TOTAUX REBUTS RÉCUPÉRABLES ==================
    scrap_recoverable_weight = fields.Float(
        string='Poids Rebuts Récupérables (kg)',
        compute='_compute_scrap_totals',
        store=True,
        digits='Product Unit of Measure'
    )

    scrap_recoverable_cost = fields.Monetary(
        string='Coût Rebuts Récupérables',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== TOTAUX PÂTE RÉCUPÉRABLE ==================
    paste_recoverable_weight = fields.Float(
        string='Poids Pâte Récupérable (kg)',
        compute='_compute_scrap_totals',
        store=True
    )

    paste_recoverable_cost = fields.Monetary(
        string='Coût Pâte Récupérable',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== TOTAL PERTES (pour déduction poids bon) ==================
    total_scrap_weight = fields.Float(
        string='Poids Total Pertes (kg)',
        compute='_compute_scrap_totals',
        store=True,
        digits='Product Unit of Measure',
        help="Rebuts récupérables + Pâte récupérable"
    )

    total_scrap_cost = fields.Monetary(
        string='Coût Total Pertes',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    total_packaging_cost = fields.Monetary(
        string='Coût Total Emballage',
        compute='_compute_packaging_costs',
        store=True,
        currency_field='currency_id',
        help="Somme des coûts d'emballage + films"
    )

    # ================== CALCULS FINAUX ==================
    good_weight = fields.Float(
        string='Poids Bon (kg)',
        compute='_compute_final_costs',
        store=True,
        help="Poids Consommé - Rebuts Récupérables - Pâte Récupérable"
    )

    good_material_cost = fields.Monetary(
        string='Coût Matières (Poids Bon)',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id',
        help="Coût des matières premières basé uniquement sur le poids bon (excluant rebuts et pâte)"
    )

    total_good_cost = fields.Monetary(
        string='Coût Total Production Bonne',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id',
        help="Coût matières (poids bon) + Coût emballage"
    )

    cost_per_kg_good = fields.Monetary(
        string='Coût/Kg Produit Bon',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id'
    )

    # ================== PRODUITS FINIS - TOTAUX ==================
    # Total cartons produits (tous types confondus)
    total_cartons_produced = fields.Float(
        string='Total Cartons Produits',
        compute='_compute_finished_totals',
        store=True
    )

    # SOLO/CLASSICO
    qty_solo_cartons = fields.Float(
        string='Quantité SOLO (Cartons)',
        compute='_compute_finished_totals',
        store=True
    )

    qty_classico_cartons = fields.Float(
        string='Quantité CLASSICO (Cartons)',
        compute='_compute_finished_totals',
        store=True
    )

    cost_solo_per_carton = fields.Monetary(
        string='Coût SOLO par Carton',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    cost_classico_per_carton = fields.Monetary(
        string='Coût CLASSICO par Carton',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    total_solo_cost = fields.Monetary(
        string='Coût Total SOLO',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    total_classico_cost = fields.Monetary(
        string='Coût Total CLASSICO',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    # Sandwich Grand Format
    qty_sandwich_cartons = fields.Float(
        string='Quantité Sandwich GF (Cartons)',
        compute='_compute_finished_totals',
        store=True
    )

    cost_sandwich_per_carton = fields.Monetary(
        string='Coût Sandwich GF par Carton',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    total_sandwich_cost = fields.Monetary(
        string='Coût Total Sandwich GF',
        compute='_compute_finished_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== DOCUMENTS LIÉS ==================
    picking_consumption_id = fields.Many2one(
        'stock.picking',
        string='BL Consommation MP',
        readonly=True,
        copy=False,
        help="Bon de Livraison pour la consommation des matières premières"
    )

    picking_packaging_id = fields.Many2one(
        'stock.picking',
        string='BL Consommation Emballage',
        readonly=True,
        copy=False,
        help="Bon de Livraison pour la consommation des emballages (cartons, film, etc.)"
    )

    purchase_finished_id = fields.Many2one(
        'purchase.order',
        string='Achat Produits Finis',
        readonly=True,
        copy=False
    )

    purchase_scrap_id = fields.Many2one(
        'purchase.order',
        string='Achat Rebuts Récupérables',
        readonly=True,
        copy=False
    )

    purchase_paste_id = fields.Many2one(
        'purchase.order',
        string='Achat Pâte Récupérable',
        readonly=True,
        copy=False,
        help="Achat pour entrée en stock de la pâte récupérable (valorisation AVCO)"
    )

    # ================== NOTES ==================
    notes = fields.Text(string='Notes')

    # ================== MÉTHODES DE CALCUL ==================

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('ron.daily.production') or 'Nouveau'

        # Pré-remplir les coûts unitaires des emballages si non fournis
        company_id = vals.get('company_id', self.env.company.id)
        config = self.env['ron.production.config'].get_config(company_id)
        production_type = vals.get('production_type', 'solo_classico')

        if production_type == 'solo_classico':
            if 'emballage_solo_unit_cost' not in vals and config.product_emballage_solo_id:
                vals['emballage_solo_unit_cost'] = config.product_emballage_solo_id.standard_price
            if 'emballage_classico_unit_cost' not in vals and config.product_emballage_classico_id:
                vals['emballage_classico_unit_cost'] = config.product_emballage_classico_id.standard_price
            if 'film_solo_unit_cost' not in vals and config.product_film_solo_id:
                vals['film_solo_unit_cost'] = config.product_film_solo_id.standard_price
            if 'film_classico_unit_cost' not in vals and config.product_film_classico_id:
                vals['film_classico_unit_cost'] = config.product_film_classico_id.standard_price
        elif production_type == 'sandwich_gf':
            if 'emballage_sandwich_unit_cost' not in vals and config.product_emballage_sandwich_id:
                vals['emballage_sandwich_unit_cost'] = config.product_emballage_sandwich_id.standard_price
            if 'film_sandwich_unit_cost' not in vals and config.product_film_sandwich_id:
                vals['film_sandwich_unit_cost'] = config.product_film_sandwich_id.standard_price

        return super().create(vals)

    @api.onchange('production_type', 'company_id')
    def _onchange_production_type_load_packaging_costs(self):
        """Charge automatiquement les coûts unitaires des emballages depuis la configuration."""
        if not self.company_id:
            return

        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if self.production_type == 'solo_classico':
            # Charger les prix des emballages SOLO/CLASSICO
            if config.product_emballage_solo_id:
                self.emballage_solo_unit_cost = config.product_emballage_solo_id.standard_price
            if config.product_emballage_classico_id:
                self.emballage_classico_unit_cost = config.product_emballage_classico_id.standard_price
            if config.product_film_solo_id:
                self.film_solo_unit_cost = config.product_film_solo_id.standard_price
            if config.product_film_classico_id:
                self.film_classico_unit_cost = config.product_film_classico_id.standard_price
        elif self.production_type == 'sandwich_gf':
            # Charger les prix des emballages Sandwich
            if config.product_emballage_sandwich_id:
                self.emballage_sandwich_unit_cost = config.product_emballage_sandwich_id.standard_price
            if config.product_film_sandwich_id:
                self.film_sandwich_unit_cost = config.product_film_sandwich_id.standard_price

    @api.depends('consumption_line_ids', 'consumption_line_ids.total_cost',
                 'consumption_line_ids.weight_kg')
    def _compute_consumption_totals(self):
        """Calcule les totaux de consommation et propage le coût/kg aux rebuts et pâte."""
        for rec in self:
            total_cost = sum(rec.consumption_line_ids.mapped('total_cost'))
            total_weight = sum(rec.consumption_line_ids.mapped('weight_kg'))

            rec.total_consumption_cost = total_cost
            rec.total_consumption_weight = total_weight
            new_cost_per_kg = total_cost / total_weight if total_weight > 0 else 0
            rec.cost_per_kg = new_cost_per_kg

            # Propager le coût/kg aux lignes de rebuts et pâte
            if new_cost_per_kg > 0:
                for scrap_line in rec.scrap_line_ids:
                    scrap_line.cost_per_kg = new_cost_per_kg
                for paste_line in rec.paste_line_ids:
                    paste_line.cost_per_kg = new_cost_per_kg

    @api.depends('scrap_line_ids', 'scrap_line_ids.weight_kg', 'scrap_line_ids.total_cost',
                 'paste_line_ids', 'paste_line_ids.weight_kg', 'paste_line_ids.total_cost')
    def _compute_scrap_totals(self):
        """Calcule les totaux de rebuts et pâte récupérables."""
        for rec in self:
            # Rebuts récupérables (vendables) - depuis scrap_line_ids
            rec.scrap_recoverable_weight = sum(rec.scrap_line_ids.mapped('weight_kg'))
            rec.scrap_recoverable_cost = sum(rec.scrap_line_ids.mapped('total_cost'))

            # Pâte récupérable - depuis paste_line_ids
            rec.paste_recoverable_weight = sum(rec.paste_line_ids.mapped('weight_kg'))
            rec.paste_recoverable_cost = sum(rec.paste_line_ids.mapped('total_cost'))

            # Totaux globaux (rebuts + pâte récupérables)
            # Ces totaux sont utilisés pour calculer le poids bon
            rec.total_scrap_weight = rec.scrap_recoverable_weight + rec.paste_recoverable_weight
            rec.total_scrap_cost = rec.scrap_recoverable_cost + rec.paste_recoverable_cost

    @api.depends(
        'emballage_solo_qty', 'emballage_solo_unit_cost',
        'emballage_classico_qty', 'emballage_classico_unit_cost',
        'film_solo_qty', 'film_solo_unit_cost',
        'film_classico_qty', 'film_classico_unit_cost',
        'emballage_sandwich_qty', 'emballage_sandwich_unit_cost',
        'film_sandwich_qty', 'film_sandwich_unit_cost',
    )
    def _compute_packaging_costs(self):
        """Calcule les coûts d'emballage par type."""
        for rec in self:
            # Coûts individuels SOLO/CLASSICO
            rec.emballage_solo_cost = rec.emballage_solo_qty * rec.emballage_solo_unit_cost
            rec.emballage_classico_cost = rec.emballage_classico_qty * rec.emballage_classico_unit_cost
            rec.film_solo_cost = rec.film_solo_qty * rec.film_solo_unit_cost
            rec.film_classico_cost = rec.film_classico_qty * rec.film_classico_unit_cost

            # Coûts individuels SANDWICH
            rec.emballage_sandwich_cost = rec.emballage_sandwich_qty * rec.emballage_sandwich_unit_cost
            rec.film_sandwich_cost = rec.film_sandwich_qty * rec.film_sandwich_unit_cost

            # Totaux par catégorie
            rec.total_emballage_cost = (rec.emballage_solo_cost +
                                        rec.emballage_classico_cost +
                                        rec.emballage_sandwich_cost)
            rec.total_film_cost = (rec.film_solo_cost +
                                   rec.film_classico_cost +
                                   rec.film_sandwich_cost)

            # Total général
            rec.total_packaging_cost = rec.total_emballage_cost + rec.total_film_cost

    @api.depends('total_consumption_cost', 'total_consumption_weight',
                 'scrap_recoverable_weight', 'paste_recoverable_weight',
                 'total_packaging_cost', 'cost_per_kg')
    def _compute_final_costs(self):
        """Calcule les coûts finaux.

        FORMULE (basée sur le poids bon uniquement):
        - Poids Bon = Poids Consommé - Rebuts Récupérables - Pâte Récupérable
        - Coût Matières (Poids Bon) = Coût/kg × Poids Bon
        - Coût Total = Coût Matières (Poids Bon) + Emballage

        Les rebuts et pâte récupérable sont exclus du coût de production.
        """
        for rec in self:
            # Poids bon = Consommé - Rebuts récupérables - Pâte récupérable
            rec.good_weight = (rec.total_consumption_weight -
                               rec.scrap_recoverable_weight -
                               rec.paste_recoverable_weight)

            # Coût matières basé uniquement sur le poids bon
            # (exclut les rebuts et pâte récupérable du coût)
            rec.good_material_cost = rec.cost_per_kg * rec.good_weight

            # Coût total production bonne = Coût matières (poids bon) + Coût emballage
            rec.total_good_cost = (rec.good_material_cost +
                                   rec.total_packaging_cost)

            # Coût par kg de produit bon
            rec.cost_per_kg_good = (rec.total_good_cost / rec.good_weight
                                     if rec.good_weight > 0 else 0)

    @api.depends('finished_product_ids', 'finished_product_ids.quantity',
                 'finished_product_ids.product_type', 'good_material_cost',
                 'good_weight', 'production_type',
                 'emballage_solo_cost', 'film_solo_cost',
                 'emballage_classico_cost', 'film_classico_cost',
                 'emballage_sandwich_cost', 'film_sandwich_cost')
    def _compute_finished_totals(self):
        """Calcule les coûts par produit fini.

        Deux modes de calcul:
        - SOLO/CLASSICO: Matières (poids bon) réparties au ratio + Emballages affectés directement
          FORMULE: Coût CLASSICO = Coût SOLO × ratio (1.65 par défaut)
          Le CLASSICO est plus cher car il contient plus de produit.
        - Sandwich GF: Calcul direct (coût total / quantité)

        Les emballages sont affectés DIRECTEMENT par type (pas de ratio sur les emballages).
        NOTE: Le coût matières utilisé est basé sur le poids bon uniquement (sans rebuts ni pâte).
        """
        for rec in self:
            config = self.env['ron.production.config'].get_config(rec.company_id.id)

            # Récupérer les quantités par type
            solo_lines = rec.finished_product_ids.filtered(lambda l: l.product_type == 'solo')
            classico_lines = rec.finished_product_ids.filtered(lambda l: l.product_type == 'classico')
            sandwich_lines = rec.finished_product_ids.filtered(lambda l: l.product_type == 'sandwich_gf')

            qty_solo = sum(solo_lines.mapped('quantity'))
            qty_classico = sum(classico_lines.mapped('quantity'))
            qty_sandwich = sum(sandwich_lines.mapped('quantity'))

            rec.qty_solo_cartons = qty_solo
            rec.qty_classico_cartons = qty_classico
            rec.qty_sandwich_cartons = qty_sandwich

            # Total cartons (tous types)
            rec.total_cartons_produced = qty_solo + qty_classico + qty_sandwich

            # Initialisation des coûts
            rec.cost_solo_per_carton = 0
            rec.cost_classico_per_carton = 0
            rec.cost_sandwich_per_carton = 0
            rec.total_solo_cost = 0
            rec.total_classico_cost = 0
            rec.total_sandwich_cost = 0

            if rec.good_material_cost <= 0:
                continue

            # MODE SOLO/CLASSICO
            if rec.production_type == 'solo_classico':
                ratio = config.cost_ratio_solo_classico or 1.65

                # Coûts emballage par type (affectation DIRECTE)
                pkg_solo = rec.emballage_solo_cost + rec.film_solo_cost
                pkg_classico = rec.emballage_classico_cost + rec.film_classico_cost

                # Répartition des MATIÈRES PREMIÈRES (poids bon) au ratio uniquement
                # FORMULE: C = ratio × S (Coût CLASSICO = ratio × Coût SOLO)
                # Le CLASSICO est plus cher car il a plus de produit
                # Total MP (poids bon) = S × qty_solo + C × qty_classico
                # Total MP (poids bon) = S × qty_solo + (ratio × S) × qty_classico
                # Total MP (poids bon) = S × (qty_solo + ratio × qty_classico)
                # S = Total MP (poids bon) / (qty_solo + ratio × qty_classico)

                cost_matieres = rec.good_material_cost
                denominator = (qty_solo + qty_classico * ratio)

                if denominator > 0:
                    # Coût matières par carton (avec ratio)
                    mp_solo_per_carton = cost_matieres / denominator
                    mp_classico_per_carton = mp_solo_per_carton * ratio

                    # Coût emballage par carton (affectation DIRECTE - pas de ratio)
                    pkg_solo_per_carton = pkg_solo / qty_solo if qty_solo > 0 else 0
                    pkg_classico_per_carton = pkg_classico / qty_classico if qty_classico > 0 else 0

                    # Coût TOTAL par carton = Matières + Emballage
                    cost_solo_final = mp_solo_per_carton + pkg_solo_per_carton
                    cost_classico_final = mp_classico_per_carton + pkg_classico_per_carton

                    rec.cost_solo_per_carton = cost_solo_final
                    rec.cost_classico_per_carton = cost_classico_final
                    rec.total_solo_cost = cost_solo_final * qty_solo
                    rec.total_classico_cost = cost_classico_final * qty_classico

            # MODE SANDWICH GF - Calcul direct (sans ratio)
            elif rec.production_type == 'sandwich_gf':
                if qty_sandwich > 0:
                    # Coût emballage Sandwich
                    pkg_sandwich = rec.emballage_sandwich_cost + rec.film_sandwich_cost

                    # Coût total = Matières (poids bon) + Emballages
                    total_cost = rec.good_material_cost + pkg_sandwich
                    cost_sandwich = total_cost / qty_sandwich

                    rec.cost_sandwich_per_carton = cost_sandwich
                    rec.total_sandwich_cost = total_cost

    # ================== ACTIONS ==================

    def action_load_from_template(self):
        """Charge la liste des matières premières depuis le template actif.

        Crée les lignes de consommation avec quantité = 0 (à saisir manuellement).
        Le poids par unité et le coût unitaire sont pré-remplis.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Vous ne pouvez charger le template qu'en état brouillon."))

        # Récupérer le template actif
        TemplateModel = self.env['ron.consumption.template']
        template = TemplateModel.get_active_template(self.company_id.id)

        if not template:
            raise UserError(_(
                "Aucun template de consommation actif trouvé.\n"
                "Veuillez créer et activer un template dans Configuration > Template Consommation."
            ))

        if not template.line_ids:
            raise UserError(_(
                "Le template '%s' ne contient aucune matière première.\n"
                "Veuillez ajouter des matières premières au template."
            ) % template.name)

        # Supprimer les lignes de consommation existantes
        self.consumption_line_ids.unlink()

        # Créer les nouvelles lignes de consommation depuis le template
        ConsumptionLine = self.env['ron.consumption.line']
        for tpl_line in template.line_ids:
            product = tpl_line.product_id

            ConsumptionLine.create({
                'daily_production_id': self.id,
                'product_id': product.id,
                'quantity': 0,  # À saisir manuellement
                'unit_cost': product.standard_price,
                'weight_per_unit': tpl_line.weight_per_unit,
            })

        # Message de confirmation
        self.message_post(
            body=_("Template '%s' chargé avec %d matières premières. "
                   "Veuillez saisir les quantités consommées.") % (
                template.name, len(template.line_ids)
            )
        )

        # Recharger le formulaire
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ron.daily.production',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm(self):
        """Confirme la production journalière et calcule les coûts."""
        for rec in self:
            if not rec.consumption_line_ids:
                raise UserError(_("Veuillez ajouter au moins une ligne de consommation."))
            if not rec.finished_product_ids:
                raise UserError(_("Veuillez ajouter au moins un produit fini."))

            # Vérifier que toutes les quantités de consommation sont > 0
            zero_qty_lines = rec.consumption_line_ids.filtered(lambda l: l.quantity <= 0)
            if zero_qty_lines:
                products = ', '.join(zero_qty_lines.mapped('product_id.name'))
                raise UserError(_(
                    "Les quantités de consommation doivent être supérieures à 0.\n"
                    "Produits avec quantité nulle ou non saisie: %s"
                ) % products)

            # Mise à jour du coût/kg dans les lignes de rebut et pâte
            for scrap in rec.scrap_line_ids:
                scrap.cost_per_kg = rec.cost_per_kg
            for paste in rec.paste_line_ids:
                paste.cost_per_kg = rec.cost_per_kg

            rec.write({'state': 'confirmed'})

            # Message avec les coûts calculés
            if rec.production_type == 'solo_classico':
                rec.message_post(
                    body=_("""
                    <b>Production confirmée (SOLO/CLASSICO)</b><br/>
                    - Coût/kg matière: %(cost_kg).2f<br/>
                    - Poids bon: %(good_weight).2f kg<br/>
                    - Coût SOLO/Carton: %(cost_solo).2f<br/>
                    - Coût CLASSICO/Carton: %(cost_classico).2f
                    """) % {
                        'cost_kg': rec.cost_per_kg,
                        'good_weight': rec.good_weight,
                        'cost_solo': rec.cost_solo_per_carton,
                        'cost_classico': rec.cost_classico_per_carton,
                    }
                )
            else:  # sandwich_gf
                rec.message_post(
                    body=_("""
                    <b>Production confirmée (Sandwich Grand Format)</b><br/>
                    - Coût/kg matière: %(cost_kg).2f<br/>
                    - Poids bon: %(good_weight).2f kg<br/>
                    - Coût Sandwich/Carton: %(cost_sandwich).2f
                    """) % {
                        'cost_kg': rec.cost_per_kg,
                        'good_weight': rec.good_weight,
                        'cost_sandwich': rec.cost_sandwich_per_carton,
                    }
                )

    def _check_stock_availability(self):
        """Vérifie la disponibilité du stock pour les consommations et emballages.

        Utilise l'emplacement de Production s'il est configuré,
        sinon utilise l'emplacement source du dépôt Matière Première.
        """
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        # Priorité 1: Utiliser l'emplacement de Production s'il est configuré
        if config.location_production_id:
            location = config.location_production_id
        else:
            # Priorité 2: Utiliser le dépôt Matière Première
            if not config.warehouse_mp_id:
                raise UserError(_("Veuillez configurer l'emplacement Production ou le dépôt Matière Première."))

            # Récupérer le type de picking sortant pour déterminer l'emplacement source
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', config.warehouse_mp_id.id),
                ('code', '=', 'outgoing')
            ], limit=1)

            if not picking_type:
                raise UserError(_("Type de picking sortant non trouvé pour le dépôt MP."))

            # Utiliser l'emplacement source du type de picking
            location = picking_type.default_location_src_id
            if not location:
                location = config.warehouse_mp_id.lot_stock_id

        # Récupérer les emplacements enfants une seule fois
        child_locations = self.env['stock.location'].search([
            ('id', 'child_of', location.id),
            ('usage', '=', 'internal')
        ])

        missing_mp = []  # Matières premières manquantes
        missing_emb = []  # Emballages manquants

        # ========== Vérifier les Matières Premières ==========
        for line in self.consumption_line_ids:
            if not line.product_id:
                continue

            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', 'in', child_locations.ids),
            ])
            available_qty = sum(quant.mapped('quantity')) - sum(quant.mapped('reserved_quantity'))

            if available_qty < line.quantity:
                missing_mp.append({
                    'product': line.product_id.name,
                    'required': line.quantity,
                    'available': max(0, available_qty),
                    'missing': line.quantity - available_qty,
                })

        # ========== Vérifier les Emballages ==========
        # Liste des emballages à vérifier selon le type de production
        emballages_to_check = []

        if self.production_type == 'solo_classico':
            if config.product_emballage_solo_id and self.emballage_solo_qty > 0:
                emballages_to_check.append((config.product_emballage_solo_id, self.emballage_solo_qty))
            if config.product_emballage_classico_id and self.emballage_classico_qty > 0:
                emballages_to_check.append((config.product_emballage_classico_id, self.emballage_classico_qty))
            if config.product_film_solo_id and self.film_solo_qty > 0:
                emballages_to_check.append((config.product_film_solo_id, self.film_solo_qty))
            if config.product_film_classico_id and self.film_classico_qty > 0:
                emballages_to_check.append((config.product_film_classico_id, self.film_classico_qty))
        elif self.production_type == 'sandwich_gf':
            if config.product_emballage_sandwich_id and self.emballage_sandwich_qty > 0:
                emballages_to_check.append((config.product_emballage_sandwich_id, self.emballage_sandwich_qty))
            if config.product_film_sandwich_id and self.film_sandwich_qty > 0:
                emballages_to_check.append((config.product_film_sandwich_id, self.film_sandwich_qty))

        for product, qty in emballages_to_check:
            quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', 'in', child_locations.ids),
            ])
            available_qty = sum(quant.mapped('quantity')) - sum(quant.mapped('reserved_quantity'))

            if available_qty < qty:
                missing_emb.append({
                    'product': product.name,
                    'required': qty,
                    'available': max(0, available_qty),
                    'missing': qty - available_qty,
                })

        # ========== Générer le message d'erreur ==========
        if missing_mp or missing_emb:
            message = _("Stock insuffisant dans '%s':\n") % location.complete_name

            if missing_mp:
                message += _("\n📦 MATIÈRES PREMIÈRES:\n")
                for mp in missing_mp:
                    message += _("  - %s: Requis %.2f, Disponible %.2f (Manquant: %.2f)\n") % (
                        mp['product'], mp['required'], mp['available'], mp['missing']
                    )

            if missing_emb:
                message += _("\n📋 EMBALLAGES:\n")
                for emb in missing_emb:
                    message += _("  - %s: Requis %.2f, Disponible %.2f (Manquant: %.2f)\n") % (
                        emb['product'], emb['required'], emb['available'], emb['missing']
                    )

            raise UserError(message)

        return True

    def action_validate(self):
        """Valide la production et génère les documents."""
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Veuillez d'abord confirmer la production."))

            config = self.env['ron.production.config'].get_config(rec.company_id.id)

            # Vérifier la disponibilité du stock AVANT de créer les documents
            rec._check_stock_availability()

            # Générer le BL de consommation MP si configuré
            if config.auto_create_delivery and not rec.picking_consumption_id:
                rec._create_consumption_picking()

            # Générer le BL de consommation Emballage si configuré
            if config.auto_create_delivery and not rec.picking_packaging_id:
                rec._create_packaging_picking()

            # Générer l'achat de produits finis si configuré
            if config.auto_create_purchase and not rec.purchase_finished_id:
                rec._create_finished_purchase()

            # Générer l'achat de rebuts récupérables si nécessaire
            if rec.scrap_recoverable_weight > 0 and not rec.purchase_scrap_id:
                rec._create_scrap_purchase()

            # Générer l'achat de pâte récupérable (stock AVCO)
            if rec.paste_recoverable_weight > 0 and not rec.purchase_paste_id:
                rec._create_paste_purchase()

            # Validation automatique des opérations si configuré
            if config.auto_validate_operations:
                rec._auto_validate_operations(config)

            rec.write({'state': 'validated'})
            rec.message_post(body=_("Production validée. Documents générés."))

    def _auto_validate_operations(self, config):
        """Valide automatiquement les BL et les achats si configuré."""
        self.ensure_one()

        # 1. Valider le BL de consommation MP
        if self.picking_consumption_id and self.picking_consumption_id.state not in ('done', 'cancel'):
            try:
                if self.picking_consumption_id.state == 'draft':
                    self.picking_consumption_id.action_confirm()
                if self.picking_consumption_id.state == 'confirmed':
                    self.picking_consumption_id.action_assign()
                if self.picking_consumption_id.state == 'assigned':
                    for move in self.picking_consumption_id.move_ids:
                        # Arrondir la quantité selon les règles de l'UoM
                        uom = move.product_uom
                        qty_rounded = float_round(move.product_uom_qty, precision_rounding=uom.rounding)
                        move.quantity = qty_rounded
                    self.picking_consumption_id.button_validate()
                _logger.info(f"BL Consommation MP validé: {self.picking_consumption_id.name}")
            except Exception as e:
                _logger.error(f"Erreur validation BL Consommation MP: {e}")
                raise UserError(_("Erreur lors de la validation du BL de consommation MP: %s") % str(e))

        # 2. Valider le BL de consommation Emballage
        if self.picking_packaging_id and self.picking_packaging_id.state not in ('done', 'cancel'):
            try:
                if self.picking_packaging_id.state == 'draft':
                    self.picking_packaging_id.action_confirm()
                if self.picking_packaging_id.state == 'confirmed':
                    self.picking_packaging_id.action_assign()
                if self.picking_packaging_id.state == 'assigned':
                    for move in self.picking_packaging_id.move_ids:
                        # Arrondir la quantité selon les règles de l'UoM
                        uom = move.product_uom
                        qty_rounded = float_round(move.product_uom_qty, precision_rounding=uom.rounding)
                        move.quantity = qty_rounded
                    self.picking_packaging_id.button_validate()
                _logger.info(f"BL Consommation Emballage validé: {self.picking_packaging_id.name}")
            except Exception as e:
                _logger.error(f"Erreur validation BL Emballage: {e}")
                raise UserError(_("Erreur lors de la validation du BL d'emballage: %s") % str(e))

        # 3. Valider les achats (Demande -> Commande -> Réception)
        purchases = [
            self.purchase_finished_id,
            self.purchase_scrap_id,
            self.purchase_paste_id,
        ]

        for purchase in purchases:
            if purchase and purchase.state in ('draft', 'sent'):
                try:
                    # Confirmer l'achat (Demande -> Commande)
                    purchase.button_confirm()

                    # Valider la réception
                    for picking in purchase.picking_ids:
                        if picking.state not in ('done', 'cancel'):
                            if picking.state == 'draft':
                                picking.action_confirm()
                            if picking.state == 'confirmed':
                                picking.action_assign()
                            if picking.state == 'assigned':
                                for move in picking.move_ids:
                                    # Arrondir la quantité selon les règles de l'UoM
                                    uom = move.product_uom
                                    qty_rounded = float_round(move.product_uom_qty, precision_rounding=uom.rounding)
                                    move.quantity = qty_rounded
                                picking.button_validate()

                    _logger.info(f"Achat validé: {purchase.name}")

                    # Créer la facture fournisseur si configuré
                    if config.auto_create_supplier_invoice:
                        self._create_supplier_invoice(purchase)

                except Exception as e:
                    _logger.error(f"Erreur validation achat {purchase.name}: {e}")
                    raise UserError(_("Erreur lors de la validation de l'achat %s: %s") % (purchase.name, str(e)))

    def _create_supplier_invoice(self, purchase):
        """Crée une facture fournisseur pour un achat."""
        if purchase.invoice_status != 'invoiced':
            try:
                purchase.action_create_invoice()
                _logger.info(f"Facture fournisseur créée pour: {purchase.name}")
            except Exception as e:
                _logger.warning(f"Impossible de créer la facture pour {purchase.name}: {e}")

    def action_done(self):
        """Termine la production.

        Note: Le standard_price (PMP/AVCO) des produits finis est géré
        automatiquement par Odoo lors de la réception des achats (stock.move).
        Il ne faut PAS l'écraser manuellement ici car cela court-circuiterait
        le calcul du prix moyen pondéré.
        """
        for rec in self:
            rec.write({'state': 'done'})
            rec.message_post(body=_("Production terminée."))

    def action_reset_draft(self):
        """Remet en brouillon."""
        for rec in self:
            # Permettre de remettre en brouillon même une production terminée
            # (nécessaire pour pouvoir la supprimer)
            rec.write({'state': 'draft'})
            rec.message_post(body=_("Production remise en brouillon."))

    def action_recalculate_weights(self):
        """Recalcule les poids manquants dans les lignes de consommation.

        Cette action corrige les lignes où le weight_per_unit est à 0 ou NULL
        en extrayant le poids depuis le nom du produit (ex: "FARINE 25 KG" → 25).
        Met également à jour le coût/kg des rebuts et pâte.
        """
        for rec in self:
            lines_fixed = 0
            for line in rec.consumption_line_ids:
                if not line.weight_per_unit or line.weight_per_unit == 0:
                    new_weight = line._get_weight_per_unit_for_product(line.product_id)
                    if new_weight > 0:
                        line.weight_per_unit = new_weight
                        lines_fixed += 1

            # Propager le coût/kg aux rebuts et pâte
            if rec.cost_per_kg > 0:
                rec.scrap_line_ids.write({'cost_per_kg': rec.cost_per_kg})
                rec.paste_line_ids.write({'cost_per_kg': rec.cost_per_kg})

            if lines_fixed > 0:
                rec.message_post(
                    body=_("Poids recalculés pour %d ligne(s) de consommation.\n"
                           "Nouveau poids total: %.2f kg\n"
                           "Nouveau coût/kg: %.2f\n"
                           "Coût/kg propagé aux rebuts et pâte.") % (
                        lines_fixed,
                        rec.total_consumption_weight,
                        rec.cost_per_kg
                    )
                )
            else:
                rec.message_post(body=_("Aucune ligne à corriger - tous les poids sont déjà définis.\n"
                                        "Coût/kg propagé aux rebuts et pâte."))

        return True

    def action_recalculate_costs(self):
        """Recalcule tous les coûts de production.

        Force le recalcul de tous les champs computed dans le bon ordre:
        1. Totaux de consommation (coût/kg)
        2. Totaux des rebuts et pâte
        3. Coûts d'emballage
        4. Coûts finaux (poids bon, coût matières poids bon)
        5. Coûts par produit fini (SOLO/CLASSICO/Sandwich)

        Utile après une mise à jour du module ou en cas de désynchronisation.
        """
        for rec in self:
            # Sauvegarder les anciennes valeurs pour le message
            old_total = rec.total_good_cost
            old_solo = rec.cost_solo_per_carton
            old_classico = rec.cost_classico_per_carton
            old_sandwich = rec.cost_sandwich_per_carton

            # Invalider le cache pour forcer le recalcul
            rec.invalidate_recordset()

            # Forcer le recalcul dans l'ordre des dépendances
            rec._compute_consumption_totals()
            rec._compute_scrap_totals()
            rec._compute_packaging_costs()
            rec._compute_final_costs()
            rec._compute_finished_totals()

            # Message avec les changements
            if rec.production_type == 'solo_classico':
                rec.message_post(
                    body=_("""
                    <b>Coûts recalculés</b><br/>
                    <table>
                        <tr><th>Champ</th><th>Avant</th><th>Après</th></tr>
                        <tr><td>Coût Total</td><td>%(old_total).2f</td><td>%(new_total).2f</td></tr>
                        <tr><td>Coût SOLO/Carton</td><td>%(old_solo).2f</td><td>%(new_solo).2f</td></tr>
                        <tr><td>Coût CLASSICO/Carton</td><td>%(old_classico).2f</td><td>%(new_classico).2f</td></tr>
                    </table>
                    """) % {
                        'old_total': old_total,
                        'new_total': rec.total_good_cost,
                        'old_solo': old_solo,
                        'new_solo': rec.cost_solo_per_carton,
                        'old_classico': old_classico,
                        'new_classico': rec.cost_classico_per_carton,
                    }
                )
            else:  # sandwich_gf
                rec.message_post(
                    body=_("""
                    <b>Coûts recalculés</b><br/>
                    <table>
                        <tr><th>Champ</th><th>Avant</th><th>Après</th></tr>
                        <tr><td>Coût Total</td><td>%(old_total).2f</td><td>%(new_total).2f</td></tr>
                        <tr><td>Coût Sandwich/Carton</td><td>%(old_sandwich).2f</td><td>%(new_sandwich).2f</td></tr>
                    </table>
                    """) % {
                        'old_total': old_total,
                        'new_total': rec.total_good_cost,
                        'old_sandwich': old_sandwich,
                        'new_sandwich': rec.cost_sandwich_per_carton,
                    }
                )

        return True

    def unlink(self):
        """Empêche la suppression des productions terminées."""
        for rec in self:
            if rec.state == 'done':
                raise UserError(_(
                    "Impossible de supprimer la production '%s' car elle est terminée.\n"
                    "Veuillez d'abord la remettre en brouillon."
                ) % rec.name)
        return super().unlink()

    # ================== GÉNÉRATION DE DOCUMENTS ==================

    def _create_consumption_picking(self):
        """Crée le BL de consommation vers le contact Consommation.

        Utilise l'emplacement de Production s'il est configuré,
        sinon utilise l'emplacement source du dépôt Matière Première.
        """
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_consumption_id:
            raise UserError(_("Veuillez configurer le contact Consommation."))

        # Déterminer l'emplacement source et le type de picking
        if config.location_production_id:
            # Utiliser l'emplacement de Production configuré
            location_src = config.location_production_id
            # Trouver le type de picking pour l'entrepôt de cet emplacement
            warehouse = config.location_production_id.warehouse_id or config.warehouse_mp_id
            if not warehouse:
                raise UserError(_("Veuillez configurer le dépôt associé à l'emplacement Production."))
        else:
            # Utiliser le dépôt Matière Première
            if not config.warehouse_mp_id:
                raise UserError(_("Veuillez configurer l'emplacement Production ou le dépôt Matière Première."))
            warehouse = config.warehouse_mp_id
            location_src = None  # Sera défini par le type de picking

        # Récupérer le type de picking (livraison sortante)
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)

        if not picking_type:
            raise UserError(_("Type de picking sortant non trouvé pour le dépôt."))

        # Si pas d'emplacement source défini, utiliser celui du type de picking
        if not location_src:
            location_src = picking_type.default_location_src_id

        # Créer le picking
        picking_vals = {
            'partner_id': config.partner_consumption_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': config.partner_consumption_id.property_stock_customer.id,
            'origin': self.name,
            'scheduled_date': self.production_date,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Créer les lignes de mouvement
        for line in self.consumption_line_ids:
            # Arrondir la quantité selon les règles de l'UoM du produit
            uom = line.product_id.uom_id
            qty_rounded = float_round(line.quantity, precision_rounding=uom.rounding)

            self.env['stock.move'].create({
                'name': line.product_id.name,
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty_rounded,
                'product_uom': uom.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })

        self.picking_consumption_id = picking.id
        _logger.info(f"BL Consommation MP créé: {picking.name}")

    def _create_packaging_picking(self):
        """Crée le BL de consommation des emballages vers le contact Consommation.

        Génère un BL séparé pour les emballages (cartons, films) en utilisant
        les produits configurés dans ron.production.config.
        """
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        # Construire la liste des emballages à consommer selon le type de production
        emballages_to_consume = []

        if self.production_type == 'solo_classico':
            if config.product_emballage_solo_id and self.emballage_solo_qty > 0:
                emballages_to_consume.append((config.product_emballage_solo_id, self.emballage_solo_qty))
            if config.product_emballage_classico_id and self.emballage_classico_qty > 0:
                emballages_to_consume.append((config.product_emballage_classico_id, self.emballage_classico_qty))
            if config.product_film_solo_id and self.film_solo_qty > 0:
                emballages_to_consume.append((config.product_film_solo_id, self.film_solo_qty))
            if config.product_film_classico_id and self.film_classico_qty > 0:
                emballages_to_consume.append((config.product_film_classico_id, self.film_classico_qty))
        elif self.production_type == 'sandwich_gf':
            if config.product_emballage_sandwich_id and self.emballage_sandwich_qty > 0:
                emballages_to_consume.append((config.product_emballage_sandwich_id, self.emballage_sandwich_qty))
            if config.product_film_sandwich_id and self.film_sandwich_qty > 0:
                emballages_to_consume.append((config.product_film_sandwich_id, self.film_sandwich_qty))

        if not emballages_to_consume:
            _logger.info("Pas d'emballage à consommer - BL Emballage non créé")
            return

        if not config.partner_consumption_id:
            raise UserError(_("Veuillez configurer le contact Consommation."))

        # Déterminer l'emplacement source (même logique que pour les MP)
        if config.location_production_id:
            location_src = config.location_production_id
            warehouse = config.location_production_id.warehouse_id or config.warehouse_mp_id
            if not warehouse:
                raise UserError(_("Veuillez configurer le dépôt associé à l'emplacement Production."))
        else:
            if not config.warehouse_mp_id:
                raise UserError(_("Veuillez configurer l'emplacement Production ou le dépôt Matière Première."))
            warehouse = config.warehouse_mp_id
            location_src = None

        # Récupérer le type de picking (livraison sortante)
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)

        if not picking_type:
            raise UserError(_("Type de picking sortant non trouvé pour le dépôt."))

        if not location_src:
            location_src = picking_type.default_location_src_id

        # Créer le picking
        picking_vals = {
            'partner_id': config.partner_consumption_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': config.partner_consumption_id.property_stock_customer.id,
            'origin': f"{self.name} - Emballage",
            'scheduled_date': self.production_date,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Créer les lignes de mouvement pour chaque emballage
        for product, qty in emballages_to_consume:
            # Arrondir la quantité selon les règles de l'UoM du produit
            uom = product.uom_id
            qty_rounded = float_round(qty, precision_rounding=uom.rounding)

            self.env['stock.move'].create({
                'name': f"[Emballage] {product.name}",
                'picking_id': picking.id,
                'product_id': product.id,
                'product_uom_qty': qty_rounded,
                'product_uom': uom.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })

        self.picking_packaging_id = picking.id
        _logger.info(f"BL Consommation Emballage créé: {picking.name}")

    def _create_finished_purchase(self):
        """Crée l'achat de produits finis depuis le fournisseur Production."""
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_production_id:
            raise UserError(_("Veuillez configurer le fournisseur Production."))

        # Créer la commande d'achat
        purchase_vals = {
            'partner_id': config.partner_production_id.id,
            'date_order': self.production_date,
            'origin': self.name,
            'picking_type_id': config.warehouse_pf_id.in_type_id.id if config.warehouse_pf_id else False,
        }
        purchase = self.env['purchase.order'].create(purchase_vals)

        # Créer les lignes selon le type de produit
        for line in self.finished_product_ids:
            product = False
            if line.product_type == 'solo':
                product = config.product_solo_id
            elif line.product_type == 'classico':
                product = config.product_classico_id
            elif line.product_type == 'sandwich_gf':
                product = config.product_sandwich_id

            if product:
                self.env['purchase.order.line'].create({
                    'order_id': purchase.id,
                    'product_id': product.id,
                    'name': product.name,
                    'product_qty': line.quantity,
                    'product_uom': product.uom_id.id,
                    'price_unit': line.unit_cost,
                    'date_planned': self.production_date,
                })

        self.purchase_finished_id = purchase.id
        _logger.info(f"Achat Produits Finis créé: {purchase.name}")

    def _create_scrap_purchase(self):
        """Crée l'achat de rebuts récupérables depuis le fournisseur Production.

        Supporte plusieurs produits rebuts (multi-lignes).
        """
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_production_id:
            raise UserError(_("Veuillez configurer le fournisseur Production."))

        # Filtrer les lignes de rebuts récupérables avec produit
        scrap_lines = self.scrap_line_ids.filtered(
            lambda l: l.scrap_type == 'scrap_recoverable' and l.product_id
        )

        if not scrap_lines:
            return  # Pas de rebuts avec produit défini

        # Créer la commande d'achat
        purchase_vals = {
            'partner_id': config.partner_production_id.id,
            'date_order': self.production_date,
            'origin': f"{self.name} - Rebuts",
            'picking_type_id': config.warehouse_pf_id.in_type_id.id if config.warehouse_pf_id else False,
        }
        purchase = self.env['purchase.order'].create(purchase_vals)

        # Créer une ligne par produit rebut
        for scrap_line in scrap_lines:
            self.env['purchase.order.line'].create({
                'order_id': purchase.id,
                'product_id': scrap_line.product_id.id,
                'name': f"Rebut {scrap_line.product_id.name} du {self.production_date}",
                'product_qty': scrap_line.weight_kg,
                'product_uom': scrap_line.product_id.uom_id.id,
                'price_unit': scrap_line.cost_per_kg,
                'date_planned': self.production_date,
            })

        self.purchase_scrap_id = purchase.id
        _logger.info(f"Achat Rebuts créé: {purchase.name}")

    def _create_paste_purchase(self):
        """Crée l'achat de pâte récupérable pour entrée en stock (valorisation AVCO)."""
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_production_id:
            raise UserError(_("Veuillez configurer le fournisseur Production."))

        if not config.product_paste_id:
            raise UserError(_("Veuillez configurer le produit Pâte Récupérable."))

        # Créer la commande d'achat - Dépôt Production (DPR)
        purchase_vals = {
            'partner_id': config.partner_production_id.id,
            'date_order': self.production_date,
            'origin': f"{self.name} - Pâte",
            'picking_type_id': config.warehouse_production_id.in_type_id.id if config.warehouse_production_id else False,
        }
        purchase = self.env['purchase.order'].create(purchase_vals)

        # Ligne pour la pâte récupérable
        self.env['purchase.order.line'].create({
            'order_id': purchase.id,
            'product_id': config.product_paste_id.id,
            'name': f"Pâte récupérable du {self.production_date}",
            'product_qty': self.paste_recoverable_weight,
            'product_uom': config.product_paste_id.uom_id.id,
            'price_unit': self.cost_per_kg,  # Valorisation au coût/kg du jour
            'date_planned': self.production_date,
        })

        self.purchase_paste_id = purchase.id
        _logger.info(f"Achat Pâte Récupérable créé: {purchase.name}")

    # ================== CONTRAINTES ==================

    @api.constrains('production_date')
    def _check_unique_date(self):
        """Une seule production par jour."""
        for rec in self:
            existing = self.search([
                ('production_date', '=', rec.production_date),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id)
            ])
            if existing:
                raise ValidationError(_(
                    "Une production existe déjà pour la date %s (Réf: %s)."
                ) % (rec.production_date, existing.name))

    # ================== ACTIONS SMART BUTTONS ==================

    def action_view_consumption_picking(self):
        """Ouvre le BL de consommation MP lié à cette production."""
        self.ensure_one()
        if not self.picking_consumption_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('BL Consommation MP'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_consumption_id.id,
            'target': 'current',
        }

    def action_view_packaging_picking(self):
        """Ouvre le BL de consommation emballage lié à cette production."""
        self.ensure_one()
        if not self.picking_packaging_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('BL Consommation Emballage'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_packaging_id.id,
            'target': 'current',
        }

    def action_view_finished_purchase(self):
        """Ouvre l'achat de produits finis lié à cette production."""
        self.ensure_one()
        if not self.purchase_finished_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('Achat Produits Finis'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_finished_id.id,
            'target': 'current',
        }

    def action_view_scrap_purchase(self):
        """Ouvre l'achat de rebuts récupérables lié à cette production."""
        self.ensure_one()
        if not self.purchase_scrap_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('Achat Rebuts'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_scrap_id.id,
            'target': 'current',
        }

    def action_view_paste_purchase(self):
        """Ouvre l'achat de pâte récupérable lié à cette production."""
        self.ensure_one()
        if not self.purchase_paste_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('Achat Pâte Récupérable'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_paste_id.id,
            'target': 'current',
        }

    # ================== ACTION IMPRIMER ==================

    def action_print_production_report(self):
        """Imprime la fiche de production journalière."""
        return self.env.ref(
            'adi_simple_production_cost.action_report_daily_production'
        ).report_action(self)
