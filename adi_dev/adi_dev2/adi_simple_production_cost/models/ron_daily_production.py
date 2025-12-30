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

    # ================== TOTAUX EMBALLAGE ==================
    total_packaging_cost = fields.Monetary(
        string='Coût Total Emballage',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id',
        help="Somme des coûts d'emballage (cartons + film ondulé + autres)"
    )

    packaging_carton_cost = fields.Monetary(
        string='Coût Cartons',
        compute='_compute_packaging_totals',
        store=True,
        currency_field='currency_id'
    )

    packaging_film_cost = fields.Monetary(
        string='Coût Film Ondulé',
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
        help="Poids Consommé - Rebuts Récupérables - Pâte Récupérable"
    )

    total_good_cost = fields.Monetary(
        string='Coût Total Production Bonne',
        compute='_compute_final_costs',
        store=True,
        currency_field='currency_id',
        help="Coût matières + Coût emballage"
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
        """Calcule les totaux de rebuts et pâte récupérables."""
        for rec in self:
            # Rebuts récupérables (vendables)
            scrap_rec = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'scrap_recoverable')
            rec.scrap_recoverable_weight = sum(scrap_rec.mapped('weight_kg'))
            rec.scrap_recoverable_cost = sum(scrap_rec.mapped('total_cost'))

            # Pâte récupérable
            paste_rec = rec.scrap_line_ids.filtered(lambda l: l.scrap_type == 'paste_recoverable')
            rec.paste_recoverable_weight = sum(paste_rec.mapped('weight_kg'))
            rec.paste_recoverable_cost = sum(paste_rec.mapped('total_cost'))

            # Totaux globaux (rebuts + pâte récupérables)
            # Ces totaux sont utilisés pour calculer le poids bon
            rec.total_scrap_weight = rec.scrap_recoverable_weight + rec.paste_recoverable_weight
            rec.total_scrap_cost = rec.scrap_recoverable_cost + rec.paste_recoverable_cost

    @api.depends('packaging_line_ids', 'packaging_line_ids.total_cost',
                 'packaging_line_ids.packaging_type')
    def _compute_packaging_totals(self):
        """Calcule les totaux d'emballage."""
        for rec in self:
            # Cartons
            cartons = rec.packaging_line_ids.filtered(lambda l: l.packaging_type == 'carton')
            rec.packaging_carton_cost = sum(cartons.mapped('total_cost'))

            # Film ondulé
            film = rec.packaging_line_ids.filtered(lambda l: l.packaging_type == 'film_ondule')
            rec.packaging_film_cost = sum(film.mapped('total_cost'))

            # Autres (étiquettes + autres)
            others = rec.packaging_line_ids.filtered(
                lambda l: l.packaging_type in ('label', 'other'))
            rec.packaging_other_cost = sum(others.mapped('total_cost'))

            # Total emballage
            rec.total_packaging_cost = (rec.packaging_carton_cost +
                                        rec.packaging_film_cost +
                                        rec.packaging_other_cost)

    @api.depends('total_consumption_cost', 'total_consumption_weight',
                 'scrap_recoverable_weight', 'paste_recoverable_weight',
                 'total_packaging_cost')
    def _compute_final_costs(self):
        """Calcule les coûts finaux.

        NOUVELLE FORMULE SIMPLIFIÉE:
        - Poids Bon = Poids Consommé - Rebuts Récupérables - Pâte Récupérable
        - Coût = Matières + Emballage (rebuts et pâte comptabilisés séparément)
        """
        for rec in self:
            # Poids bon = Consommé - Rebuts récupérables - Pâte récupérable
            rec.good_weight = (rec.total_consumption_weight -
                               rec.scrap_recoverable_weight -
                               rec.paste_recoverable_weight)

            # Coût total production bonne = Coût matières + Coût emballage
            # (Les rebuts et pâte sont comptabilisés séparément, pas déduits)
            rec.total_good_cost = (rec.total_consumption_cost +
                                   rec.total_packaging_cost)

            # Coût par kg de produit bon
            rec.cost_per_kg_good = (rec.total_good_cost / rec.good_weight
                                     if rec.good_weight > 0 else 0)

    @api.depends('finished_product_ids', 'finished_product_ids.quantity',
                 'finished_product_ids.product_type', 'total_good_cost',
                 'good_weight', 'production_type')
    def _compute_finished_totals(self):
        """Calcule les coûts par produit fini.

        Deux modes de calcul:
        - SOLO/CLASSICO: Utilise le ratio de coût configuré
        - Sandwich GF: Calcul direct (coût total / quantité)
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

            if rec.total_good_cost <= 0:
                continue

            # MODE SOLO/CLASSICO - Calcul avec ratio
            if rec.production_type == 'solo_classico':
                ratio = config.cost_ratio_solo_classico or 1.65

                # Formule de répartition avec ratio:
                # S = ratio × C (Coût SOLO = ratio × Coût CLASSICO)
                # Total = qty_solo × S + qty_classico × C
                # Total = C × (qty_solo × ratio + qty_classico)
                # C = Total / (qty_solo × ratio + qty_classico)

                denominator = (qty_solo * ratio + qty_classico)
                if denominator > 0:
                    cost_classico = rec.total_good_cost / denominator
                    cost_solo = cost_classico * ratio

                    rec.cost_classico_per_carton = cost_classico
                    rec.cost_solo_per_carton = cost_solo
                    rec.total_classico_cost = cost_classico * qty_classico
                    rec.total_solo_cost = cost_solo * qty_solo

            # MODE SANDWICH GF - Calcul direct
            elif rec.production_type == 'sandwich_gf':
                if qty_sandwich > 0:
                    cost_sandwich = rec.total_good_cost / qty_sandwich

                    rec.cost_sandwich_per_carton = cost_sandwich
                    rec.total_sandwich_cost = rec.total_good_cost

    # ================== ACTIONS ==================

    def action_load_from_bom(self):
        """Charge les composants depuis les nomenclatures validées.

        Calcule les quantités en fonction du nombre de cartons de chaque produit fini.
        Les lignes de consommation existantes sont supprimées et remplacées.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Vous ne pouvez charger les composants qu'en état brouillon."))

        if not self.finished_product_ids:
            raise UserError(_("Veuillez d'abord saisir les produits finis (nombre de cartons)."))

        # Récupérer les quantités par type de produit
        product_quantities = {}
        for line in self.finished_product_ids:
            if line.product_type not in product_quantities:
                product_quantities[line.product_type] = 0
            product_quantities[line.product_type] += line.quantity

        if not product_quantities:
            raise UserError(_("Aucune quantité de produit fini saisie."))

        # Vérifier que les nomenclatures validées existent pour les types de produits
        BomModel = self.env['ron.bom']
        missing_boms = []
        for product_type in product_quantities.keys():
            bom = BomModel.get_validated_bom(product_type, self.company_id.id)
            if not bom:
                type_label = dict(self.finished_product_ids._fields['product_type'].selection).get(product_type, product_type)
                missing_boms.append(type_label)

        if missing_boms:
            raise UserError(_(
                "Nomenclature validée manquante pour: %s\n"
                "Veuillez créer et valider une nomenclature dans Configuration > Nomenclatures."
            ) % ', '.join(missing_boms))

        # Calculer les consommations totales par produit
        # (agrège les composants de toutes les nomenclatures)
        consumption_dict = {}  # {product_id: total_quantity}

        for product_type, qty_cartons in product_quantities.items():
            bom = BomModel.get_validated_bom(product_type, self.company_id.id)
            for bom_line in bom.line_ids:
                product_id = bom_line.product_id.id
                quantity = bom_line.quantity * qty_cartons
                if product_id in consumption_dict:
                    consumption_dict[product_id] += quantity
                else:
                    consumption_dict[product_id] = quantity

        # Supprimer les lignes de consommation existantes
        self.consumption_line_ids.unlink()

        # Créer les nouvelles lignes de consommation
        ConsumptionLine = self.env['ron.consumption.line']
        for product_id, quantity in consumption_dict.items():
            product = self.env['product.product'].browse(product_id)

            # Récupérer le poids par unité depuis le produit
            weight_per_unit = 1.0
            if product.weight > 0:
                weight_per_unit = product.weight
            else:
                # Essayer de déduire le poids du nom (ex: "Farine 25kg")
                name = product.name.lower()
                if '25kg' in name or '25 kg' in name:
                    weight_per_unit = 25.0
                elif '50kg' in name or '50 kg' in name:
                    weight_per_unit = 50.0
                elif '10kg' in name or '10 kg' in name:
                    weight_per_unit = 10.0

            ConsumptionLine.create({
                'daily_production_id': self.id,
                'product_id': product_id,
                'quantity': quantity,
                'unit_cost': product.standard_price,
                'weight_per_unit': weight_per_unit,
            })

        # Invalider le cache pour forcer le recalcul de tous les champs
        self.invalidate_recordset()
        self.consumption_line_ids.invalidate_recordset()

        # Forcer le recalcul des champs stockés des lignes de consommation
        for line in self.consumption_line_ids:
            line._compute_weight_kg()
            line._compute_total_cost()

        # Forcer le recalcul des totaux
        self._compute_consumption_totals()
        self._compute_final_costs()
        self._compute_finished_totals()

        # Recharger le formulaire pour voir les nouvelles valeurs
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

            # Mise à jour du coût/kg dans les lignes de rebut
            for scrap in rec.scrap_line_ids:
                scrap.cost_per_kg = rec.cost_per_kg

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
        """Vérifie la disponibilité du stock pour toutes les consommations.

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

        missing_products = []

        for line in self.consumption_line_ids:
            if not line.product_id:
                continue

            # Calculer le stock disponible dans l'emplacement source
            # Inclure les emplacements enfants
            child_locations = self.env['stock.location'].search([
                ('id', 'child_of', location.id),
                ('usage', '=', 'internal')
            ])

            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', 'in', child_locations.ids),
            ])
            available_qty = sum(quant.mapped('quantity')) - sum(quant.mapped('reserved_quantity'))

            if available_qty < line.quantity:
                missing_products.append({
                    'product': line.product_id.name,
                    'required': line.quantity,
                    'available': max(0, available_qty),
                    'missing': line.quantity - available_qty,
                    'location': location.complete_name,
                })

        if missing_products:
            location_name = missing_products[0]['location'] if missing_products else ''
            message = _("Stock insuffisant dans '%s' pour les produits suivants:\n\n") % location_name
            for mp in missing_products:
                message += _("- %s: Requis %.2f, Disponible %.2f (Manquant: %.2f)\n") % (
                    mp['product'], mp['required'], mp['available'], mp['missing']
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

            # Générer le BL de consommation si configuré
            if config.auto_create_delivery and not rec.picking_consumption_id:
                rec._create_consumption_picking()

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

        # 1. Valider le BL de consommation
        if self.picking_consumption_id and self.picking_consumption_id.state not in ('done', 'cancel'):
            try:
                # Confirmer le picking
                if self.picking_consumption_id.state == 'draft':
                    self.picking_consumption_id.action_confirm()

                # Assigner les quantités
                if self.picking_consumption_id.state == 'confirmed':
                    self.picking_consumption_id.action_assign()

                # Valider le picking (transfert immédiat)
                if self.picking_consumption_id.state == 'assigned':
                    for move in self.picking_consumption_id.move_ids:
                        move.quantity = move.product_uom_qty
                    self.picking_consumption_id.button_validate()

                _logger.info(f"BL Consommation validé: {self.picking_consumption_id.name}")
            except Exception as e:
                _logger.error(f"Erreur validation BL: {e}")
                raise UserError(_("Erreur lors de la validation du BL de consommation: %s") % str(e))

        # 2. Valider les achats (Demande -> Commande -> Réception)
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
                                    move.quantity = move.product_uom_qty
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
        """Termine la production."""
        for rec in self:
            # Mettre à jour les prix de revient des produits selon le type de production
            config = self.env['ron.production.config'].get_config(rec.company_id.id)

            if rec.production_type == 'solo_classico':
                if config.product_solo_id and rec.cost_solo_per_carton > 0:
                    config.product_solo_id.sudo().standard_price = rec.cost_solo_per_carton

                if config.product_classico_id and rec.cost_classico_per_carton > 0:
                    config.product_classico_id.sudo().standard_price = rec.cost_classico_per_carton

            elif rec.production_type == 'sandwich_gf':
                if config.product_sandwich_id and rec.cost_sandwich_per_carton > 0:
                    config.product_sandwich_id.sudo().standard_price = rec.cost_sandwich_per_carton

            rec.write({'state': 'done'})
            rec.message_post(body=_("Production terminée. Prix de revient mis à jour."))

    def action_reset_draft(self):
        """Remet en brouillon."""
        for rec in self:
            # Permettre de remettre en brouillon même une production terminée
            # (nécessaire pour pouvoir la supprimer)
            rec.write({'state': 'draft'})
            rec.message_post(body=_("Production remise en brouillon."))

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

        # Créer la commande d'achat
        purchase_vals = {
            'partner_id': config.partner_production_id.id,
            'date_order': self.production_date,
            'origin': f"{self.name} - Pâte",
            'picking_type_id': config.warehouse_pf_id.in_type_id.id if config.warehouse_pf_id else False,
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
        """Ouvre le BL de consommation lié à cette production."""
        self.ensure_one()
        if not self.picking_consumption_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('BL Consommation'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_consumption_id.id,
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
