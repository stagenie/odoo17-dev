# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonScrapLine(models.Model):
    """
    Ligne de rebut ou pâte.

    Types:
    - Rebut vendable: peut être vendu comme produit fini secondaire
    - Rebut non vendable: perte sèche
    - Pâte récupérable: sera réutilisée le lendemain
    - Pâte irrécupérable: perte
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

    # ================== TYPE ==================
    scrap_type = fields.Selection([
        ('scrap_sellable', 'Rebut Vendable'),
        ('scrap_unsellable', 'Rebut Non Vendable'),
        ('paste_recoverable', 'Pâte Récupérable'),
        ('paste_unrecoverable', 'Pâte Irrécupérable'),
    ], string='Type', required=True, default='scrap_sellable')

    # ================== PRODUIT OPTIONNEL ==================
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        domain="[('type', '=', 'product')]",
        help="Produit associé (optionnel, utilisé pour le stock des rebuts vendables)"
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

    @api.depends('weight_kg', 'cost_per_kg')
    def _compute_total_cost(self):
        """Calcule le coût total."""
        for rec in self:
            rec.total_cost = rec.weight_kg * rec.cost_per_kg

    @api.depends('scrap_type')
    def _compute_type_display(self):
        """Affichage du type."""
        type_labels = {
            'scrap_sellable': 'Rebut Vendable',
            'scrap_unsellable': 'Rebut Non Vendable',
            'paste_recoverable': 'Pâte Récupérable',
            'paste_unrecoverable': 'Pâte Irrécupérable',
        }
        for rec in self:
            rec.type_display = type_labels.get(rec.scrap_type, '')

    @api.depends('scrap_type')
    def _compute_is_sellable(self):
        """Indique si le rebut est vendable."""
        for rec in self:
            rec.is_sellable = rec.scrap_type == 'scrap_sellable'

    @api.depends('scrap_type')
    def _compute_is_recoverable(self):
        """Indique si la pâte est récupérable."""
        for rec in self:
            rec.is_recoverable = rec.scrap_type == 'paste_recoverable'

    @api.onchange('scrap_type')
    def _onchange_scrap_type(self):
        """Met à jour le produit selon le type."""
        config = self.env['ron.production.config'].get_config()

        if self.scrap_type == 'scrap_sellable' and config.product_scrap_sellable_id:
            self.product_id = config.product_scrap_sellable_id
        elif self.scrap_type == 'scrap_unsellable' and config.product_scrap_unsellable_id:
            self.product_id = config.product_scrap_unsellable_id
        elif self.scrap_type == 'paste_recoverable' and config.product_paste_recoverable_id:
            self.product_id = config.product_paste_recoverable_id
        elif self.scrap_type == 'paste_unrecoverable' and config.product_paste_unrecoverable_id:
            self.product_id = config.product_paste_unrecoverable_id

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
