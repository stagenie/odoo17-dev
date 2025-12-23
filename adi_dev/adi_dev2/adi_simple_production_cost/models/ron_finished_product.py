# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonFinishedProduct(models.Model):
    """
    Ligne de produit fini.

    Représente la quantité de produit fini (SOLO ou CLASSICO) produite.
    Le coût unitaire est calculé automatiquement avec le ratio.
    """
    _name = 'ron.finished.product'
    _description = 'Produit Fini'
    _order = 'product_type, id'

    daily_production_id = fields.Many2one(
        'ron.daily.production',
        string='Production Journalière',
        required=True,
        ondelete='cascade',
        index=True
    )

    production_date = fields.Date(
        string='Date',
        related='daily_production_id.production_date',
        store=True
    )

    # ================== PRODUIT ==================
    product_type = fields.Selection([
        ('solo', 'SOLO'),
        ('classico', 'CLASSICO'),
    ], string='Type de Produit', required=True, default='solo')

    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        compute='_compute_product_id',
        store=True
    )

    # ================== QUANTITÉS ==================
    quantity = fields.Float(
        string='Quantité (Cartons)',
        required=True,
        digits='Product Unit of Measure',
        help="Nombre de cartons produits"
    )

    # Pour SOLO: 48 packs × 4 unités = 192 unités
    # Pour CLASSICO: 24 packs × 13 unités = 312 unités
    units_per_carton = fields.Integer(
        string='Unités/Carton',
        compute='_compute_units_per_carton',
        store=True
    )

    total_units = fields.Float(
        string='Total Unités',
        compute='_compute_total_units',
        store=True
    )

    weight_per_carton = fields.Float(
        string='Poids/Carton (kg)',
        digits='Product Unit of Measure',
        help="Poids d'un carton en kilogrammes"
    )

    total_weight = fields.Float(
        string='Poids Total (kg)',
        compute='_compute_total_weight',
        store=True
    )

    # ================== COÛTS ==================
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='daily_production_id.currency_id',
        readonly=True
    )

    unit_cost = fields.Monetary(
        string='Coût/Carton',
        currency_field='currency_id',
        help="Coût de revient par carton (calculé automatiquement)"
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id'
    )

    # ================== PRIX DE VENTE ==================
    sale_price = fields.Monetary(
        string='Prix de Vente/Carton',
        currency_field='currency_id',
        help="Prix de vente fixé par carton"
    )

    margin = fields.Monetary(
        string='Marge/Carton',
        compute='_compute_margin',
        store=True,
        currency_field='currency_id'
    )

    margin_percent = fields.Float(
        string='Marge (%)',
        compute='_compute_margin',
        store=True
    )

    total_margin = fields.Monetary(
        string='Marge Totale',
        compute='_compute_margin',
        store=True,
        currency_field='currency_id'
    )

    # ================== NOTES ==================
    notes = fields.Char(string='Notes')

    # ================== MÉTHODES ==================

    @api.depends('product_type')
    def _compute_product_id(self):
        """Récupère le produit depuis la configuration."""
        for rec in self:
            config = self.env['ron.production.config'].get_config()
            if rec.product_type == 'solo':
                rec.product_id = config.product_solo_id
            elif rec.product_type == 'classico':
                rec.product_id = config.product_classico_id
            else:
                rec.product_id = False

    @api.depends('product_type')
    def _compute_units_per_carton(self):
        """Définit le nombre d'unités par carton."""
        for rec in self:
            if rec.product_type == 'solo':
                # SOLO: 48 packs × 4 unités = 192 unités
                rec.units_per_carton = 192
            elif rec.product_type == 'classico':
                # CLASSICO: 24 packs × 13 unités = 312 unités
                rec.units_per_carton = 312
            else:
                rec.units_per_carton = 0

    @api.depends('quantity', 'units_per_carton')
    def _compute_total_units(self):
        """Calcule le total d'unités."""
        for rec in self:
            rec.total_units = rec.quantity * rec.units_per_carton

    @api.depends('quantity', 'weight_per_carton')
    def _compute_total_weight(self):
        """Calcule le poids total."""
        for rec in self:
            rec.total_weight = rec.quantity * rec.weight_per_carton

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_cost

    @api.depends('unit_cost', 'sale_price', 'quantity')
    def _compute_margin(self):
        """Calcule la marge."""
        for rec in self:
            if rec.sale_price and rec.unit_cost:
                rec.margin = rec.sale_price - rec.unit_cost
                rec.margin_percent = (rec.margin / rec.sale_price * 100) if rec.sale_price > 0 else 0
                rec.total_margin = rec.margin * rec.quantity
            else:
                rec.margin = 0
                rec.margin_percent = 0
                rec.total_margin = 0

    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Met à jour les informations selon le type."""
        config = self.env['ron.production.config'].get_config()

        if self.product_type == 'solo':
            self.weight_per_carton = config.solo_weight_per_carton
            if config.product_solo_id:
                self.sale_price = config.product_solo_id.list_price
        elif self.product_type == 'classico':
            self.weight_per_carton = config.classico_weight_per_carton
            if config.product_classico_id:
                self.sale_price = config.product_classico_id.list_price

    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifie que la quantité est positive."""
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("La quantité doit être supérieure à 0."))
