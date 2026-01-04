# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonPackagingLine(models.Model):
    """
    Ligne de coût d'emballage.

    Représente les coûts d'emballage pour la production du jour :
    - Cartons: Nombre × Prix unitaire
    - Film Ondulé: Poids (kg) × Prix/kg
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
        ('film_ondule', 'Film Ondulé'),
        ('label', 'Étiquettes'),
        ('other', 'Autre'),
    ], string='Type', required=True, default='carton')

    # ================== TYPE DE PRODUCTION (depuis parent) ==================
    parent_production_type = fields.Selection(
        related='daily_production_id.production_type',
        string='Type Production',
        store=True,
        readonly=True
    )

    # ================== AFFECTATION PRODUIT (si séparation activée) ==================
    target_product_type = fields.Selection([
        ('common', 'Commun'),
        ('solo', 'SOLO'),
        ('classico', 'CLASSICO'),
        ('sandwich_gf', 'Sandwich GF'),
    ], string='Affectation', default='common',
       help="Si 'Séparer les Coûts Emballage' est activé dans la configuration:\n"
            "- Commun: Réparti avec le ratio\n"
            "- SOLO/CLASSICO/Sandwich: Affecté directement au produit"
    )

    @api.onchange('parent_production_type')
    def _onchange_parent_production_type(self):
        """Réinitialise l'affectation si le type de production change."""
        if self.parent_production_type == 'sandwich_gf' and self.target_product_type in ('solo', 'classico'):
            self.target_product_type = 'common'
        elif self.parent_production_type == 'solo_classico' and self.target_product_type == 'sandwich_gf':
            self.target_product_type = 'common'

    # ================== PRODUIT ==================
    product_id = fields.Many2one(
        'product.product',
        string='Produit Emballage',
        domain="[('type', 'in', ['product', 'consu'])]",
        help="Produit d'emballage (carton, film ondulé, etc.)"
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unité',
        related='product_id.uom_id',
        readonly=True
    )

    # ================== QUANTITÉS ==================
    # Pour Carton: nombre de pièces
    # Pour Film Ondulé: poids en kg
    quantity = fields.Float(
        string='Quantité / Poids',
        required=True,
        digits='Product Unit of Measure',
        help="Nombre (pour cartons/étiquettes) ou Poids en kg (pour film ondulé)"
    )

    quantity_label = fields.Char(
        string='Libellé Quantité',
        compute='_compute_quantity_label'
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
        help="Prix unitaire (par pièce ou par kg selon le type)"
    )

    unit_cost_label = fields.Char(
        string='Libellé Prix',
        compute='_compute_unit_cost_label'
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
        help="Quantité × Prix unitaire"
    )

    # ================== LIEN AVEC PRODUITS FINIS ==================
    linked_to_production = fields.Boolean(
        string='Lié à la Production',
        default=False,
        help="Si coché, la quantité est calculée depuis les produits finis (pour cartons)"
    )

    # ================== NOTES ==================
    notes = fields.Char(string='Notes')

    # ================== MÉTHODES ==================

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_cost

    @api.depends('packaging_type')
    def _compute_quantity_label(self):
        """Calcule le libellé de la quantité selon le type."""
        for rec in self:
            if rec.packaging_type == 'film_ondule':
                rec.quantity_label = 'Poids (kg)'
            else:
                rec.quantity_label = 'Nombre'

    @api.depends('packaging_type')
    def _compute_unit_cost_label(self):
        """Calcule le libellé du prix selon le type."""
        for rec in self:
            if rec.packaging_type == 'film_ondule':
                rec.unit_cost_label = 'Prix/kg'
            else:
                rec.unit_cost_label = 'Prix/unité'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Met à jour le prix unitaire depuis le produit."""
        if self.product_id:
            # Utiliser le prix standard (coût) du produit
            self.unit_cost = self.product_id.standard_price

    @api.onchange('packaging_type')
    def _onchange_packaging_type(self):
        """Suggestions selon le type."""
        if self.packaging_type == 'carton':
            self.linked_to_production = True
            # Calculer automatiquement la quantité de cartons
            if self.daily_production_id:
                total_cartons = self.daily_production_id.total_cartons_produced
                self.quantity = total_cartons
        else:
            self.linked_to_production = False

    @api.onchange('linked_to_production', 'daily_production_id')
    def _onchange_linked_production(self):
        """Met à jour la quantité si lié à la production."""
        if self.linked_to_production and self.daily_production_id:
            if self.packaging_type == 'carton':
                self.quantity = self.daily_production_id.total_cartons_produced

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

    @api.constrains('target_product_type', 'parent_production_type')
    def _check_target_product_type(self):
        """Vérifie que l'affectation est cohérente avec le type de production."""
        for rec in self:
            if not rec.parent_production_type or rec.target_product_type == 'common':
                continue

            if rec.parent_production_type == 'solo_classico':
                if rec.target_product_type == 'sandwich_gf':
                    raise ValidationError(_(
                        "L'affectation 'Sandwich GF' n'est pas valide pour une production SOLO/CLASSICO.\n"
                        "Veuillez choisir: Commun, SOLO ou CLASSICO."
                    ))
            elif rec.parent_production_type == 'sandwich_gf':
                if rec.target_product_type in ('solo', 'classico'):
                    raise ValidationError(_(
                        "L'affectation '%s' n'est pas valide pour une production Sandwich GF.\n"
                        "Veuillez choisir: Commun ou Sandwich GF."
                    ) % rec.target_product_type.upper())
