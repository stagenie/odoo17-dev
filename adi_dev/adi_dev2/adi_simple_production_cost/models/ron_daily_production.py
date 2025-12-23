# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class RonDailyProduction(models.Model):
    """
    Production Journalière RON.

    Ce modèle gère une journée de production complète incluant:
    - Les consommations de matières premières
    - Les rebuts (vendables et non vendables)
    - La pâte (récupérable et irrécupérable)
    - Les produits finis (SOLO et CLASSICO)
    - Le calcul automatique du coût de revient
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
        ('calculated', 'Calculé'),
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
        string='Rebuts et Pâte'
    )

    # ================== PRODUITS FINIS ==================
    finished_product_ids = fields.One2many(
        'ron.finished.product',
        'daily_production_id',
        string='Produits Finis'
    )

    # ================== COÛTS D'EMBALLAGE ==================
    packaging_line_ids = fields.One2many(
        'ron.packaging.line',
        'daily_production_id',
        string='Coûts Emballage'
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

    # ================== TOTAUX REBUTS ==================
    total_scrap_weight = fields.Float(
        string='Poids Total Rebuts (kg)',
        compute='_compute_scrap_totals',
        store=True,
        digits='Product Unit of Measure'
    )

    total_scrap_cost = fields.Monetary(
        string='Coût Total Rebuts',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # Rebuts vendables
    scrap_sellable_weight = fields.Float(
        string='Poids Rebuts Vendables (kg)',
        compute='_compute_scrap_totals',
        store=True
    )

    scrap_sellable_cost = fields.Monetary(
        string='Coût Rebuts Vendables',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # Rebuts non vendables
    scrap_unsellable_weight = fields.Float(
        string='Poids Rebuts Non Vendables (kg)',
        compute='_compute_scrap_totals',
        store=True
    )

    scrap_unsellable_cost = fields.Monetary(
        string='Coût Rebuts Non Vendables',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== TOTAUX PÂTE ==================
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

    paste_unrecoverable_weight = fields.Float(
        string='Poids Pâte Irrécupérable (kg)',
        compute='_compute_scrap_totals',
        store=True
    )

    paste_unrecoverable_cost = fields.Monetary(
        string='Coût Pâte Irrécupérable',
        compute='_compute_scrap_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== TOTAUX EMBALLAGE ==================
    total_packaging_cost = fields.Monetary(
        string='Coût Total Emballage',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id',
        help="Somme des coûts d'emballage (cartons + plastification)"
    )

    packaging_carton_cost = fields.Monetary(
        string='Coût Cartons',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id'
    )

    packaging_plastic_cost = fields.Monetary(
        string='Coût Plastification',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id'
    )

    packaging_other_cost = fields.Monetary(
        string='Coût Autres Emballages',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id'
    )

    # ================== CALCULS FINAUX ==================
    good_weight = fields.Float(
        string='Poids Bon (kg)',
        compute='_compute_final_costs',
        store=True,
        help="Poids total - Rebuts - Pâte irrécupérable"
    )

    total_good_cost = fields.Monetary(
        string='Coût Total Production Bonne',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id',
        help="Coût matières + Coût emballage - Valeur pâte récupérable"
    )

    cost_per_kg_good = fields.Monetary(
        string='Coût/Kg Produit Bon',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id'
    )

    # ================== PRODUITS FINIS - TOTAUX ==================
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

    # ================== DOCUMENTS LIÉS ==================
    picking_consumption_id = fields.Many2one(
        'stock.picking',
        string='BL Consommation',
        readonly=True,
        copy=False
    )

    purchase_finished_id = fields.Many2one(
        'purchase.order',
        string='Achat Produits Finis',
        readonly=True,
        copy=False
    )

    purchase_scrap_id = fields.Many2one(
        'purchase.order',
        string='Achat Rebuts Vendables',
        readonly=True,
        copy=False
    )

    # ================== NOTES ==================
    notes = fields.Text(string='Notes')

    # ================== MÉTHODES DE CALCUL ==================

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('ron.daily.production') or 'Nouveau'
        return super().create(vals)

    @api.depends('consumption_line_ids', 'consumption_line_ids.total_cost',
                 'consumption_line_ids.weight_kg')
    def _compute_consumption_totals(self):
        """Calcule les totaux de consommation."""
        for rec in self:
            total_cost = sum(rec.consumption_line_ids.mapped('total_cost'))
            total_weight = sum(rec.consumption_line_ids.mapped('weight_kg'))

            rec.total_consumption_cost = total_cost
            rec.total_consumption_weight = total_weight
            rec.cost_per_kg = total_cost / total_weight if total_weight > 0 else 0

    @api.depends('scrap_line_ids', 'scrap_line_ids.weight_kg',
                 'scrap_line_ids.total_cost', 'scrap_line_ids.scrap_type')
    def _compute_scrap_totals(self):
        """Calcule les totaux de rebuts et pâte."""
        for rec in self:
            # Rebuts vendables
            sellable = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'scrap_sellable')
            rec.scrap_sellable_weight = sum(sellable.mapped('weight_kg'))
            rec.scrap_sellable_cost = sum(sellable.mapped('total_cost'))

            # Rebuts non vendables
            unsellable = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'scrap_unsellable')
            rec.scrap_unsellable_weight = sum(unsellable.mapped('weight_kg'))
            rec.scrap_unsellable_cost = sum(unsellable.mapped('total_cost'))

            # Pâte récupérable
            paste_rec = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'paste_recoverable')
            rec.paste_recoverable_weight = sum(paste_rec.mapped('weight_kg'))
            rec.paste_recoverable_cost = sum(paste_rec.mapped('total_cost'))

            # Pâte irrécupérable
            paste_unrec = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'paste_unrecoverable')
            rec.paste_unrecoverable_weight = sum(paste_unrec.mapped('weight_kg'))
            rec.paste_unrecoverable_cost = sum(paste_unrec.mapped('total_cost'))

            # Totaux globaux rebuts (sans pâte récupérable car elle sera réutilisée)
            rec.total_scrap_weight = (rec.scrap_sellable_weight +
                                       rec.scrap_unsellable_weight +
                                       rec.paste_unrecoverable_weight)
            rec.total_scrap_cost = (rec.scrap_sellable_cost +
                                     rec.scrap_unsellable_cost +
                                     rec.paste_unrecoverable_cost)

    @api.depends('packaging_line_ids', 'packaging_line_ids.total_cost',
                 'packaging_line_ids.packaging_type')
    def _compute_packaging_totals(self):
        """Calcule les totaux d'emballage."""
        for rec in self:
            # Cartons
            cartons = rec.packaging_line_ids.filtered(lambda l: l.packaging_type == 'carton')
            rec.packaging_carton_cost = sum(cartons.mapped('total_cost'))

            # Plastification
            plastic = rec.packaging_line_ids.filtered(lambda l: l.packaging_type == 'plastic_film')
            rec.packaging_plastic_cost = sum(plastic.mapped('total_cost'))

            # Autres (étiquettes + autres)
            others = rec.packaging_line_ids.filtered(
                lambda l: l.packaging_type in ('label', 'other'))
            rec.packaging_other_cost = sum(others.mapped('total_cost'))

            # Total emballage
            rec.total_packaging_cost = (rec.packaging_carton_cost +
                                        rec.packaging_plastic_cost +
                                        rec.packaging_other_cost)

    @api.depends('total_consumption_cost', 'total_consumption_weight',
                 'total_scrap_weight', 'paste_recoverable_weight',
                 'paste_recoverable_cost', 'cost_per_kg',
                 'total_packaging_cost')
    def _compute_final_costs(self):
        """Calcule les coûts finaux."""
        for rec in self:
            # Poids bon = Total consommé - Rebuts - Pâte irrécupérable
            # (la pâte récupérable est soustraite car elle sera réutilisée)
            rec.good_weight = (rec.total_consumption_weight -
                               rec.total_scrap_weight -
                               rec.paste_recoverable_weight)

            # Coût total production bonne = Coût matières + Coût emballage - Valeur pâte récup
            # La pâte récupérable garde sa valeur car elle sera réutilisée
            rec.total_good_cost = (rec.total_consumption_cost +
                                   rec.total_packaging_cost -
                                   rec.paste_recoverable_cost)

            # Coût par kg de produit bon
            rec.cost_per_kg_good = (rec.total_good_cost / rec.good_weight
                                     if rec.good_weight > 0 else 0)

    @api.depends('finished_product_ids', 'finished_product_ids.quantity',
                 'finished_product_ids.product_type', 'total_good_cost',
                 'good_weight')
    def _compute_finished_totals(self):
        """Calcule les coûts par produit fini avec le ratio."""
        for rec in self:
            config = self.env['ron.production.config'].get_config(rec.company_id.id)
            ratio = config.cost_ratio_solo_classico or 1.65

            # Récupérer les quantités
            solo_lines = rec.finished_product_ids.filtered(lambda l: l.product_type == 'solo')
            classico_lines = rec.finished_product_ids.filtered(lambda l: l.product_type == 'classico')

            qty_solo = sum(solo_lines.mapped('quantity'))
            qty_classico = sum(classico_lines.mapped('quantity'))

            rec.qty_solo_cartons = qty_solo
            rec.qty_classico_cartons = qty_classico

            # Calcul du coût avec ratio
            # Soit S = coût SOLO, C = coût CLASSICO
            # S = ratio × C
            # Total = qty_solo × S + qty_classico × C
            # Total = qty_solo × ratio × C + qty_classico × C
            # Total = C × (qty_solo × ratio + qty_classico)
            # C = Total / (qty_solo × ratio + qty_classico)

            denominator = (qty_solo * ratio + qty_classico)
            if denominator > 0 and rec.total_good_cost > 0:
                cost_classico = rec.total_good_cost / denominator
                cost_solo = cost_classico * ratio

                rec.cost_classico_per_carton = cost_classico
                rec.cost_solo_per_carton = cost_solo
                rec.total_classico_cost = cost_classico * qty_classico
                rec.total_solo_cost = cost_solo * qty_solo
            else:
                rec.cost_classico_per_carton = 0
                rec.cost_solo_per_carton = 0
                rec.total_classico_cost = 0
                rec.total_solo_cost = 0

            # Mettre à jour les lignes de produits finis
            for line in solo_lines:
                line.unit_cost = rec.cost_solo_per_carton
            for line in classico_lines:
                line.unit_cost = rec.cost_classico_per_carton

    # ================== ACTIONS ==================

    def action_confirm(self):
        """Confirme la production journalière."""
        for rec in self:
            if not rec.consumption_line_ids:
                raise UserError(_("Veuillez ajouter au moins une ligne de consommation."))
            if not rec.finished_product_ids:
                raise UserError(_("Veuillez ajouter au moins un produit fini."))

            rec.write({'state': 'confirmed'})
            rec.message_post(body=_("Production confirmée."))

    def action_calculate(self):
        """Recalcule tous les coûts."""
        for rec in self:
            # Mise à jour du coût/kg dans les lignes de rebut
            for scrap in rec.scrap_line_ids:
                scrap.cost_per_kg = rec.cost_per_kg
                scrap._compute_total_cost()

            # Forcer le recalcul
            rec._compute_consumption_totals()
            rec._compute_scrap_totals()
            rec._compute_final_costs()
            rec._compute_finished_totals()

            rec.write({'state': 'calculated'})
            rec.message_post(
                body=_("""
                <b>Calcul effectué</b><br/>
                - Coût/kg: %(cost_kg)s<br/>
                - Poids bon: %(good_weight)s kg<br/>
                - Coût SOLO/Carton: %(cost_solo)s<br/>
                - Coût CLASSICO/Carton: %(cost_classico)s
                """) % {
                    'cost_kg': rec.cost_per_kg,
                    'good_weight': rec.good_weight,
                    'cost_solo': rec.cost_solo_per_carton,
                    'cost_classico': rec.cost_classico_per_carton,
                }
            )

    def action_validate(self):
        """Valide la production et génère les documents."""
        for rec in self:
            if rec.state != 'calculated':
                raise UserError(_("Veuillez d'abord calculer les coûts."))

            config = self.env['ron.production.config'].get_config(rec.company_id.id)

            # Générer le BL de consommation si configuré
            if config.auto_create_delivery and not rec.picking_consumption_id:
                rec._create_consumption_picking()

            # Générer l'achat de produits finis si configuré
            if config.auto_create_purchase and not rec.purchase_finished_id:
                rec._create_finished_purchase()

            # Générer l'achat de rebuts vendables si nécessaire
            if rec.scrap_sellable_weight > 0 and not rec.purchase_scrap_id:
                rec._create_scrap_purchase()

            rec.write({'state': 'validated'})
            rec.message_post(body=_("Production validée. Documents générés."))

    def action_done(self):
        """Termine la production."""
        for rec in self:
            # Mettre à jour les prix de revient des produits
            config = self.env['ron.production.config'].get_config(rec.company_id.id)

            if config.product_solo_id and rec.cost_solo_per_carton > 0:
                config.product_solo_id.sudo().standard_price = rec.cost_solo_per_carton

            if config.product_classico_id and rec.cost_classico_per_carton > 0:
                config.product_classico_id.sudo().standard_price = rec.cost_classico_per_carton

            rec.write({'state': 'done'})
            rec.message_post(body=_("Production terminée. Prix de revient mis à jour."))

    def action_reset_draft(self):
        """Remet en brouillon."""
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Une production terminée ne peut pas être remise en brouillon."))
            rec.write({'state': 'draft'})

    # ================== GÉNÉRATION DE DOCUMENTS ==================

    def _create_consumption_picking(self):
        """Crée le BL de consommation vers le contact Consommation."""
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_consumption_id:
            raise UserError(_("Veuillez configurer le contact Consommation."))

        if not config.warehouse_mp_id:
            raise UserError(_("Veuillez configurer le dépôt Matière Première."))

        # Récupérer le type de picking (livraison sortante)
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', config.warehouse_mp_id.id),
            ('code', '=', 'outgoing')
        ], limit=1)

        if not picking_type:
            raise UserError(_("Type de picking sortant non trouvé pour le dépôt MP."))

        # Créer le picking
        picking_vals = {
            'partner_id': config.partner_consumption_id.id,
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': config.partner_consumption_id.property_stock_customer.id,
            'origin': self.name,
            'scheduled_date': self.production_date,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Créer les lignes de mouvement
        for line in self.consumption_line_ids:
            self.env['stock.move'].create({
                'name': line.product_id.name,
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })

        self.picking_consumption_id = picking.id
        _logger.info(f"BL Consommation créé: {picking.name}")

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

        # Créer les lignes
        for line in self.finished_product_ids:
            product = False
            if line.product_type == 'solo':
                product = config.product_solo_id
            elif line.product_type == 'classico':
                product = config.product_classico_id

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
        """Crée l'achat de rebuts vendables depuis le fournisseur Production."""
        self.ensure_one()
        config = self.env['ron.production.config'].get_config(self.company_id.id)

        if not config.partner_production_id:
            raise UserError(_("Veuillez configurer le fournisseur Production."))

        if not config.product_scrap_sellable_id:
            raise UserError(_("Veuillez configurer le produit Rebut Vendable."))

        # Créer la commande d'achat
        purchase_vals = {
            'partner_id': config.partner_production_id.id,
            'date_order': self.production_date,
            'origin': f"{self.name} - Rebuts",
            'picking_type_id': config.warehouse_pf_id.in_type_id.id if config.warehouse_pf_id else False,
        }
        purchase = self.env['purchase.order'].create(purchase_vals)

        # Calculer le coût/kg des rebuts
        scrap_cost_per_kg = self.cost_per_kg

        self.env['purchase.order.line'].create({
            'order_id': purchase.id,
            'product_id': config.product_scrap_sellable_id.id,
            'name': f"Rebuts du {self.production_date}",
            'product_qty': self.scrap_sellable_weight,
            'product_uom': config.product_scrap_sellable_id.uom_id.id,
            'price_unit': scrap_cost_per_kg,
            'date_planned': self.production_date,
        })

        self.purchase_scrap_id = purchase.id
        _logger.info(f"Achat Rebuts créé: {purchase.name}")

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
