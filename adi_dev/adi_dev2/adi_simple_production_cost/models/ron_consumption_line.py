# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonConsumptionLine(models.Model):
    """
    Ligne de consommation de matière première.

    Représente une matière première consommée pendant la production du jour.
    Le coût est calculé automatiquement à partir du prix AVCO du produit.
    """
    _name = 'ron.consumption.line'
    _description = 'Ligne de Consommation'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Séquence', default=10)

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
    product_id = fields.Many2one(
        'product.product',
        string='Matière Première',
        required=True,
        domain="[('type', '=', 'product')]"
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unité de Mesure',
        related='product_id.uom_id',
        readonly=True
    )

    # ================== QUANTITÉS ==================
    quantity = fields.Float(
        string='Quantité',
        required=True,
        digits='Product Unit of Measure',
        help="Quantité consommée dans l'unité de mesure du produit"
    )

    weight_per_unit = fields.Float(
        string='Poids/Unité (kg)',
        digits='Product Unit of Measure',
        help="Poids d'une unité en kilogrammes (ex: sac de 25kg = 25)"
    )

    weight_kg = fields.Float(
        string='Poids Total (kg)',
        compute='_compute_weight_kg',
        store=True,
        digits='Product Unit of Measure',
        help="Quantité × Poids par unité"
    )

    # ================== COÛTS ==================
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='daily_production_id.currency_id',
        readonly=True
    )

    unit_cost = fields.Monetary(
        string='Coût Unitaire',
        currency_field='currency_id',
        help="Prix AVCO du produit"
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
        help="Quantité × Coût unitaire"
    )

    # ================== STOCK ==================
    stock_available = fields.Float(
        string='Stock Disponible',
        compute='_compute_stock_available',
        digits='Product Unit of Measure'
    )

    # ================== NOTES ==================
    notes = fields.Char(string='Notes')

    # ================== MÉTHODES ==================

    @api.depends('quantity', 'weight_per_unit')
    def _compute_weight_kg(self):
        """Calcule le poids total en kg."""
        for rec in self:
            rec.weight_kg = rec.quantity * rec.weight_per_unit

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_cost

    @api.depends('product_id')
    def _compute_stock_available(self):
        """Récupère le stock disponible."""
        for rec in self:
            if rec.product_id:
                rec.stock_available = rec.product_id.qty_available
            else:
                rec.stock_available = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Met à jour les informations du produit."""
        if self.product_id:
            # Récupérer le prix AVCO (standard_price)
            self.unit_cost = self.product_id.standard_price

            # Récupérer le poids depuis le produit si défini
            if self.product_id.weight > 0:
                self.weight_per_unit = self.product_id.weight
            else:
                # Essayer de déduire le poids du nom (ex: "Farine 25kg")
                name = self.product_id.name.lower()
                if '25kg' in name or '25 kg' in name:
                    self.weight_per_unit = 25.0
                elif '50kg' in name or '50 kg' in name:
                    self.weight_per_unit = 50.0
                elif '10kg' in name or '10 kg' in name:
                    self.weight_per_unit = 10.0
                else:
                    self.weight_per_unit = 1.0

    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifie que la quantité n'est pas négative.

        La quantité peut être 0 lors du chargement du template.
        La validation quantity > 0 se fait lors de la confirmation de la production.
        """
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_("La quantité ne peut pas être négative."))

    @api.constrains('weight_per_unit')
    def _check_weight(self):
        """Vérifie que le poids est positif."""
        for rec in self:
            if rec.weight_per_unit < 0:
                raise ValidationError(_("Le poids par unité ne peut pas être négatif."))
