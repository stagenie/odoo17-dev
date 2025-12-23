# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonPackagingLine(models.Model):
    """
    Ligne de coût d'emballage.

    Représente les coûts d'emballage pour la production du jour :
    - Cartons (lié au nombre de cartons produits)
    - Plastification (film, etc.)
    - Autres matières d'emballage
    """
    _name = 'ron.packaging.line'
    _description = 'Ligne Coût Emballage'
    _order = 'packaging_type, id'

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

    # ================== TYPE D'EMBALLAGE ==================
    packaging_type = fields.Selection([
        ('carton', 'Carton'),
        ('plastic_film', 'Film Plastique / Plastification'),
        ('label', 'Étiquettes'),
        ('other', 'Autre'),
    ], string='Type', required=True, default='plastic_film')

    # ================== PRODUIT ==================
    product_id = fields.Many2one(
        'product.product',
        string='Produit Emballage',
        domain="[('type', 'in', ['product', 'consu'])]",
        help="Produit d'emballage (carton, film plastique, etc.)"
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unité',
        related='product_id.uom_id',
        readonly=True
    )

    # ================== QUANTITÉS ==================
    quantity = fields.Float(
        string='Quantité',
        required=True,
        digits='Product Unit of Measure',
        help="Quantité utilisée"
    )

    # ================== COÛTS ==================
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='daily_production_id.currency_id',
        readonly=True
    )

    unit_cost = fields.Monetary(
        string='Prix Unitaire',
        currency_field='currency_id',
        help="Prix unitaire de l'emballage"
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
        help="Quantité × Prix unitaire"
    )

    # ================== LIEN AVEC PRODUITS FINIS ==================
    # Pour les cartons, on peut lier automatiquement aux quantités produites
    linked_to_production = fields.Boolean(
        string='Lié à la Production',
        default=False,
        help="Si coché, la quantité est calculée depuis les produits finis"
    )

    # ================== NOTES ==================
    notes = fields.Char(string='Notes')

    # ================== MÉTHODES ==================

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Met à jour le prix unitaire depuis le produit."""
        if self.product_id:
            # Utiliser le prix standard (coût) du produit
            self.unit_cost = self.product_id.standard_price

    @api.onchange('packaging_type')
    def _onchange_packaging_type(self):
        """Suggestions selon le type."""
        config = self.env['ron.production.config'].get_config()

        if self.packaging_type == 'carton':
            self.linked_to_production = True
            # Calculer automatiquement la quantité de cartons
            if self.daily_production_id:
                total_cartons = (self.daily_production_id.qty_solo_cartons +
                                self.daily_production_id.qty_classico_cartons)
                self.quantity = total_cartons
        else:
            self.linked_to_production = False

    @api.onchange('linked_to_production', 'daily_production_id')
    def _onchange_linked_production(self):
        """Met à jour la quantité si lié à la production."""
        if self.linked_to_production and self.daily_production_id:
            if self.packaging_type == 'carton':
                self.quantity = (self.daily_production_id.qty_solo_cartons +
                                self.daily_production_id.qty_classico_cartons)

    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifie que la quantité est positive."""
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_("La quantité ne peut pas être négative."))

    @api.constrains('unit_cost')
    def _check_unit_cost(self):
        """Vérifie que le coût est positif."""
        for rec in self:
            if rec.unit_cost < 0:
                raise ValidationError(_("Le prix unitaire ne peut pas être négatif."))
