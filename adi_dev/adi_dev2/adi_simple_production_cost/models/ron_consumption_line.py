# -*- coding: utf-8 -*-

import re
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
        digits='Product Unit of Measure',
        help="Quantité consommée dans l'unité de mesure du produit"
    )

    weight_per_unit = fields.Float(
        string='Poids/Unité (kg)',
        digits='Product Unit of Measure',
        help="Poids d'une unité en kilogrammes (ex: sac de 25kg = 25)"
    )

    weight_input = fields.Float(
        string='Poids Saisi (kg)',
        digits='Product Unit of Measure',
        help="Saisissez le poids total en kg. La quantité sera calculée automatiquement."
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

    def _extract_weight_from_text(self, text):
        """Extrait le poids en kg depuis un texte.

        Recherche des patterns comme: 20KG, 25 kg, 10K, 50 K, etc.
        Retourne le poids trouvé ou 0 si non trouvé.
        """
        if not text:
            return 0.0

        text = text.upper()
        # Pattern: nombre (entier ou décimal) suivi de K, KG, ou KGS
        # Exemples: 20KG, 25 KG, 10K, 50 K, 1.5KG, 0.5 K
        pattern = r'(\d+(?:[.,]\d+)?)\s*(?:KG|KGS|K)\b'
        match = re.search(pattern, text)
        if match:
            weight_str = match.group(1).replace(',', '.')
            return float(weight_str)
        return 0.0

    def _get_weight_per_unit_for_product(self, product):
        """Détermine le poids par unité pour un produit.

        Ordre de priorité :
        1. Poids défini sur le produit (product.weight)
        2. Extraction depuis le nom du produit (ex: "FARINE 25 KG" → 25)
        3. Extraction depuis l'unité de mesure
        4. Valeur par défaut = 1.0
        """
        if not product:
            return 1.0

        # Priorité 1: Poids défini sur le produit
        if product.weight > 0:
            return product.weight

        # Priorité 2: Extraire depuis le nom du produit
        weight = self._extract_weight_from_text(product.name)

        # Priorité 3: Extraire depuis l'unité de mesure
        if weight == 0 and product.uom_id:
            weight = self._extract_weight_from_text(product.uom_id.name)

        # Priorité 4: Valeur par défaut
        return weight if weight > 0 else 1.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Met à jour les informations du produit."""
        if self.product_id:
            # Récupérer le prix AVCO (standard_price)
            self.unit_cost = self.product_id.standard_price

            # Récupérer le poids par unité
            self.weight_per_unit = self._get_weight_per_unit_for_product(self.product_id)

    @api.onchange('quantity', 'weight_per_unit')
    def _onchange_quantity_compute_weight_input(self):
        """Calcule le poids saisi à partir de la quantité.

        Quand l'utilisateur saisit une quantité, le poids saisi est mis à jour.
        """
        if self.quantity and self.weight_per_unit:
            calculated_weight = self.quantity * self.weight_per_unit
            # Ne mettre à jour que si différent (évite les boucles)
            if abs(self.weight_input - calculated_weight) > 0.001:
                self.weight_input = calculated_weight

    @api.onchange('weight_input')
    def _onchange_weight_input_compute_quantity(self):
        """Calcule la quantité à partir du poids saisi.

        Quand l'utilisateur saisit un poids en kg, la quantité est calculée.
        Ex: Sac de 10kg, poids saisi = 400kg → quantité = 40 sacs
        """
        if self.weight_input and self.weight_per_unit > 0:
            calculated_qty = self.weight_input / self.weight_per_unit
            # Ne mettre à jour que si différent (évite les boucles)
            if abs(self.quantity - calculated_qty) > 0.001:
                self.quantity = calculated_qty

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

    @api.constrains('weight_input')
    def _check_weight_input(self):
        """Vérifie que le poids saisi n'est pas négatif."""
        for rec in self:
            if rec.weight_input < 0:
                raise ValidationError(_("Le poids saisi ne peut pas être négatif."))

    @api.model_create_multi
    def create(self, vals_list):
        """Crée les lignes de consommation en initialisant weight_per_unit si nécessaire.

        Cette méthode garantit que weight_per_unit est toujours défini lors de la création,
        même si l'onchange n'a pas été déclenché ou si la valeur n'a pas été transmise.
        """
        for vals in vals_list:
            if vals.get('product_id') and not vals.get('weight_per_unit'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['weight_per_unit'] = self._get_weight_per_unit_for_product(product)
            # Initialiser unit_cost si non fourni
            if vals.get('product_id') and not vals.get('unit_cost'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['unit_cost'] = product.standard_price
        return super().create(vals_list)

    def write(self, vals):
        """Met à jour les lignes de consommation en réinitialisant weight_per_unit si le produit change.

        Cette méthode garantit que weight_per_unit est mis à jour si le produit change
        et que la nouvelle valeur n'a pas été fournie.
        """
        if vals.get('product_id') and 'weight_per_unit' not in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            vals['weight_per_unit'] = self._get_weight_per_unit_for_product(product)
        if vals.get('product_id') and 'unit_cost' not in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            vals['unit_cost'] = product.standard_price
        return super().write(vals)

    def action_recalculate_weight(self):
        """Recalcule le poids par unité pour les lignes où il est manquant.

        Cette action peut être appelée manuellement ou automatiquement
        pour corriger les lignes qui ont un weight_per_unit à 0 ou NULL.
        """
        for rec in self:
            if not rec.weight_per_unit or rec.weight_per_unit == 0:
                rec.weight_per_unit = rec._get_weight_per_unit_for_product(rec.product_id)

    @api.model
    def _fix_missing_weights(self):
        """Méthode utilitaire pour corriger toutes les lignes avec poids manquant.

        Peut être appelée depuis un script ou la console Odoo :
        self.env['ron.consumption.line']._fix_missing_weights()
        """
        lines_to_fix = self.search([
            '|',
            ('weight_per_unit', '=', False),
            ('weight_per_unit', '=', 0)
        ])
        for line in lines_to_fix:
            line.weight_per_unit = line._get_weight_per_unit_for_product(line.product_id)
        return len(lines_to_fix)
