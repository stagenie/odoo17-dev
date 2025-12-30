# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonScrapLine(models.Model):
    """
    Ligne de rebut ou pâte récupérable.

    Types simplifiés:
    - Rebut récupérable: peut être vendu comme produit fini secondaire (multi-produits)
    - Pâte récupérable: sera réutilisée le lendemain (stock AVCO)
    """
    _name = 'ron.scrap.line'
    _description = 'Ligne de Rebut/Pâte'
    _order = 'scrap_type, id'

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

    # ================== TYPE (SIMPLIFIÉ) ==================
    scrap_type = fields.Selection([
        ('scrap_recoverable', 'Rebut Récupérable'),
        ('paste_recoverable', 'Pâte Récupérable'),
    ], string='Type', required=True, default='scrap_recoverable')

    # ================== PRODUIT ==================
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        domain="[('type', '=', 'product')]",
        help="Produit rebut (plusieurs articles possibles) ou pâte récupérable"
    )

    # ================== QUANTITÉS ==================
    weight_kg = fields.Float(
        string='Poids (kg)',
        required=True,
        digits='Product Unit of Measure',
        help="Poids du rebut ou de la pâte en kilogrammes"
    )

    # ================== COÛTS ==================
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='daily_production_id.currency_id',
        readonly=True
    )

    cost_per_kg = fields.Monetary(
        string='Coût/Kg',
        currency_field='currency_id',
        help="Coût par kg (récupéré depuis la production journalière)"
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
        help="Poids × Coût/kg"
    )

    # ================== INFORMATIONS ==================
    reason = fields.Selection([
        ('quality', 'Défaut Qualité'),
        ('machine', 'Problème Machine'),
        ('process', 'Problème Process'),
        ('end_day', 'Fin de Journée'),
        ('other', 'Autre'),
    ], string='Raison', default='quality')

    notes = fields.Text(string='Notes')

    # Champ calculé pour affichage
    type_display = fields.Char(
        string='Type (Affichage)',
        compute='_compute_type_display'
    )

    is_sellable = fields.Boolean(
        string='Vendable',
        compute='_compute_is_sellable',
        store=True
    )

    is_recoverable = fields.Boolean(
        string='Récupérable',
        compute='_compute_is_recoverable',
        store=True
    )

    # ================== MÉTHODES ==================

    @api.model
    def default_get(self, fields_list):
        """Définit les valeurs par défaut, notamment le produit pâte."""
        res = super().default_get(fields_list)

        # Si le type par défaut est pâte récupérable, définir le produit pâte
        if res.get('scrap_type') == 'paste_recoverable':
            config = self.env['ron.production.config'].get_config()
            if config.product_paste_id:
                res['product_id'] = config.product_paste_id.id

        return res

    @api.depends('weight_kg', 'cost_per_kg')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.weight_kg * rec.cost_per_kg

    @api.depends('scrap_type')
    def _compute_type_display(self):
        """Affichage du type."""
        type_labels = {
            'scrap_recoverable': 'Rebut Récupérable',
            'paste_recoverable': 'Pâte Récupérable',
        }
        for rec in self:
            rec.type_display = type_labels.get(rec.scrap_type, '')

    @api.depends('scrap_type')
    def _compute_is_sellable(self):
        """Indique si le rebut est vendable (récupérable)."""
        for rec in self:
            rec.is_sellable = rec.scrap_type == 'scrap_recoverable'

    @api.depends('scrap_type')
    def _compute_is_recoverable(self):
        """Indique si c'est de la pâte récupérable."""
        for rec in self:
            rec.is_recoverable = rec.scrap_type == 'paste_recoverable'

    @api.onchange('scrap_type')
    def _onchange_scrap_type(self):
        """Met à jour le produit selon le type."""
        config = self.env['ron.production.config'].get_config()

        # Pour la pâte récupérable, utiliser le produit configuré
        if self.scrap_type == 'paste_recoverable' and config.product_paste_id:
            self.product_id = config.product_paste_id
        # Pour les rebuts, laisser l'utilisateur choisir librement
        elif self.scrap_type == 'scrap_recoverable':
            # Ne pas forcer un produit - l'utilisateur peut choisir parmi plusieurs
            pass

    @api.onchange('daily_production_id')
    def _onchange_daily_production(self):
        """Récupère le coût/kg depuis la production journalière."""
        if self.daily_production_id:
            self.cost_per_kg = self.daily_production_id.cost_per_kg

    @api.constrains('weight_kg')
    def _check_weight(self):
        """Vérifie que le poids est positif."""
        for rec in self:
            if rec.weight_kg <= 0:
                raise ValidationError(_("Le poids doit être supérieur à 0."))

    def action_update_cost_per_kg(self):
        """Met à jour le coût/kg depuis la production journalière."""
        for rec in self:
            if rec.daily_production_id:
                rec.cost_per_kg = rec.daily_production_id.cost_per_kg
