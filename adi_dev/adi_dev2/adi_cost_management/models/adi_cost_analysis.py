# -*- coding: utf-8 -*-
# Part of ADI Cost Management Module
# Copyright (C) 2024 ADICOPS (<https://adicops-dz.com>)

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AdiCostAnalysis(models.Model):
    """
    Modèle d'analyse des coûts de production avec impact des rebuts.
    Version utilisant des champs calculés au lieu d'une vue SQL
    pour éviter les problèmes de dépendance lors de l'installation.
    """
    _name = 'adi.cost.analysis'
    _description = 'Analyse des Coûts de Revient'
    _rec_name = 'display_name'
    _order = 'production_date desc, product_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ================== CHAMPS D'IDENTIFICATION ==================

    display_name = fields.Char(
        'Nom',
        compute='_compute_display_name',
        store=True
    )

    name = fields.Char(
        'Référence',
        required=True,
        default='Nouveau',
        copy=False,
        readonly=True,
        index=True
    )

    production_date = fields.Date(
        'Date de Production',
        required=True,
        default=fields.Date.today,
        tracking=True,
        index=True
    )

    # ================== RELATIONS ==================

    daily_production_id = fields.Many2one(
        'adi.daily.production',
        'Production Journalière',
        ondelete='cascade',
        index=True,
        help="Production journalière associée"
    )

    product_id = fields.Many2one(
        'product.product',
        'Produit',
        required=True,
        domain="[('type', '=', 'product')]",
        tracking=True,
        index=True
    )

    product_category_id = fields.Many2one(
        'product.category',
        'Catégorie Produit',
        related='product_id.categ_id',
        store=True,
        readonly=True
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        'Nomenclature',
        compute='_compute_bom',
        store=True
    )

    production_ids = fields.Many2many(
        'mrp.production',
        'adi_cost_analysis_mrp_rel',
        'analysis_id',
        'production_id',
        string='Ordres de Fabrication',
        compute='_compute_production_data',
        store=True
    )

    # ================== QUANTITÉS ==================

    qty_produced = fields.Float(
        'Quantité Produite',
        compute='_compute_quantities',
        store=True,
        tracking=True,
        help="Quantité totale produite dans les OF"
    )

    qty_scrapped = fields.Float(
        'Quantité Rebutée',
        compute='_compute_quantities',
        store=True,
        help="Quantité totale de rebuts (équivalent unités)"
    )

    qty_good = fields.Float(
        'Quantité Bonne',
        compute='_compute_quantities',
        store=True,
        help="Quantité vendable = Production - Rebuts"
    )

    scrap_rate = fields.Float(
        'Taux de Rebut (%)',
        compute='_compute_rates',
        store=True,
        help="Pourcentage de rebuts sur la production totale"
    )

    efficiency_rate = fields.Float(
        'Taux d\'Efficacité (%)',
        compute='_compute_rates',
        store=True,
        help="100% - Taux de rebut"
    )

    # ================== COÛTS ==================

    production_cost = fields.Monetary(
        'Coût de Production',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        tracking=True,
        help="Coût total des matières premières consommées"
    )

    scrap_cost = fields.Monetary(
        'Coût des Rebuts',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        help="Valeur totale des rebuts"
    )

    total_cost = fields.Monetary(
        'Coût Total',
        compute='_compute_costs',
        store=True,
        currency_field='currency_id',
        help="Coût de production + Coût des rebuts"
    )

    # ================== PRIX UNITAIRES ==================

    unit_cost_theoretical = fields.Monetary(
        'Coût Unitaire Théorique',
        compute='_compute_unit_costs',
        store=True,
        currency_field='currency_id',
        help="Coût unitaire sans tenir compte des rebuts"
    )

    unit_cost_real = fields.Monetary(
        'Coût Unitaire Réel',
        compute='_compute_unit_costs',
        store=True,
        currency_field='currency_id',
        tracking=True,
        help="Coût unitaire incluant l'impact des rebuts"
    )

    cost_difference = fields.Monetary(
        'Écart de Coût',
        compute='_compute_unit_costs',
        store=True,
        currency_field='currency_id'
    )

    cost_increase = fields.Float(
        'Augmentation du Coût (%)',
        compute='_compute_unit_costs',
        store=True,
        help="Pourcentage d'augmentation dû aux rebuts"
    )

    # ================== MÉTRIQUES PÉRIODIQUES ==================

    production_month = fields.Char(
        'Mois',
        compute='_compute_period_fields',
        store=True
    )

    production_week = fields.Char(
        'Semaine',
        compute='_compute_period_fields',
        store=True
    )

    production_quarter = fields.Char(
        'Trimestre',
        compute='_compute_period_fields',
        store=True
    )

    production_year = fields.Integer(
        'Année',
        compute='_compute_period_fields',
        store=True
    )

    # ================== WORKFLOW ==================

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('calculated', 'Calculé'),
        ('validated', 'Validé'),
        ('cancelled', 'Annulé')
    ],
        'État',
        default='draft',
        tracking=True,
        required=True
    )

    # ================== AUTRES CHAMPS ==================

    currency_id = fields.Many2one(
        'res.currency',
        'Devise',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        'Société',
        default=lambda self: self.env.company,
        required=True
    )

    notes = fields.Text(
        'Notes',
        help="Notes additionnelles sur l'analyse"
    )

    # ================== MÉTHODES DE CALCUL ==================

    @api.model
    def create(self, vals):
        """Génération automatique de la référence"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('adi.cost.analysis') or f"ANALYSE/{fields.Date.today()}"
        return super().create(vals)

    @api.depends('product_id', 'production_date')
    def _compute_display_name(self):
        """Calcule le nom d'affichage"""
        for record in self:
            if record.product_id and record.production_date:
                record.display_name = f"{record.product_id.name} - {record.production_date}"
            else:
                record.display_name = record.name or "Analyse Coût"

    @api.depends('product_id')
    def _compute_bom(self):
        """Récupère la nomenclature du produit"""
        for record in self:
            bom = self.env['mrp.bom'].search([
                ('product_id', '=', record.product_id.id),
                '|',
                ('company_id', '=', record.company_id.id),
                ('company_id', '=', False)
            ], limit=1)
            record.bom_id = bom

    @api.depends('product_id', 'production_date')
    def _compute_production_data(self):
        """Récupère les OF du jour pour le produit"""
        for record in self:
            if record.product_id and record.production_date:
                # Recherche des OF terminés du jour
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('state', '=', 'done'),
                    ('date_finished', '>=', datetime.combine(record.production_date, datetime.min.time())),
                    ('date_finished', '<=', datetime.combine(record.production_date, datetime.max.time()))
                ]

                productions = self.env['mrp.production'].search(domain)
                record.production_ids = [(6, 0, productions.ids)]
            else:
                record.production_ids = [(5, 0, 0)]

    @api.depends('daily_production_id', 'production_ids')
    def _compute_quantities(self):
        """Calcule les quantités produites et rebutées"""
        for record in self:
            if record.daily_production_id:
                # Utiliser les données de la production journalière
                record.qty_produced = record.daily_production_id.qty_produced
                record.qty_good = record.daily_production_id.qty_good

                # Calcul des rebuts
                scrap_qty = sum(
                    scrap.qty_units
                    for scrap in record.daily_production_id.scrap_ids
                    if scrap.scrap_type == 'finished'
                )
                record.qty_scrapped = scrap_qty

            elif record.production_ids:
                # Calculer depuis les OF
                record.qty_produced = sum(prod.qty_produced for prod in record.production_ids)

                # Recherche des rebuts liés
                scrap_qty = 0
                for production in record.production_ids:
                    scraps = self.env['stock.scrap'].search([
                        ('production_id', '=', production.id),
                        ('state', '=', 'done')
                    ])
                    scrap_qty += sum(scraps.mapped('scrap_qty'))

                record.qty_scrapped = scrap_qty
                record.qty_good = record.qty_produced - scrap_qty
            else:
                record.qty_produced = 0
                record.qty_scrapped = 0
                record.qty_good = 0

    @api.depends('qty_produced', 'qty_scrapped')
    def _compute_rates(self):
        """Calcule les taux de rebut et d'efficacité"""
        for record in self:
            if record.qty_produced > 0:
                record.scrap_rate = (record.qty_scrapped / record.qty_produced) * 100
                record.efficiency_rate = ((record.qty_produced - record.qty_scrapped) / record.qty_produced) * 100
            else:
                record.scrap_rate = 0
                record.efficiency_rate = 0

    @api.depends('daily_production_id', 'production_ids', 'bom_id')
    def _compute_costs(self):
        """Calcule les coûts de production et de rebuts"""
        for record in self:
            if record.daily_production_id:
                # Utiliser les coûts de la production journalière
                record.production_cost = record.daily_production_id.total_production_cost
                record.scrap_cost = record.daily_production_id.total_scrap_cost
                record.total_cost = record.daily_production_id.total_cost_with_scrap

            elif record.production_ids:
                # Calculer depuis les OF
                production_cost = 0
                for production in record.production_ids:
                    # Coût des matières consommées
                    for move in production.move_raw_ids.filtered(lambda m: m.state == 'done'):
                        production_cost += move.quantity * move.product_id.standard_price

                record.production_cost = production_cost

                # Coût des rebuts (approximation)
                record.scrap_cost = record.qty_scrapped * record.product_id.standard_price
                record.total_cost = record.production_cost + record.scrap_cost

            elif record.bom_id and record.qty_produced > 0:
                # Estimation basée sur la nomenclature
                bom_cost = 0
                for line in record.bom_id.bom_line_ids:
                    bom_cost += line.product_qty * line.product_id.standard_price

                record.production_cost = bom_cost * record.qty_produced
                record.scrap_cost = record.qty_scrapped * record.product_id.standard_price
                record.total_cost = record.production_cost + record.scrap_cost
            else:
                record.production_cost = 0
                record.scrap_cost = 0
                record.total_cost = 0

    @api.depends('production_cost', 'qty_produced', 'qty_good', 'total_cost')
    def _compute_unit_costs(self):
        """Calcule les coûts unitaires"""
        for record in self:
            # Coût unitaire théorique (sans rebuts)
            if record.qty_produced > 0:
                record.unit_cost_theoretical = record.production_cost / record.qty_produced
            else:
                record.unit_cost_theoretical = 0

            # Coût unitaire réel (avec impact des rebuts)
            if record.qty_good > 0:
                record.unit_cost_real = record.production_cost / record.qty_good
            else:
                record.unit_cost_real = 0

            # Calcul de l'écart et du pourcentage d'augmentation
            record.cost_difference = record.unit_cost_real - record.unit_cost_theoretical

            if record.unit_cost_theoretical > 0:
                record.cost_increase = ((
                                                    record.unit_cost_real - record.unit_cost_theoretical) / record.unit_cost_theoretical)
            else:
                record.cost_increase = 0

    @api.depends('production_date')
    def _compute_period_fields(self):
        """Calcule les périodes pour les regroupements"""
        for record in self:
            if record.production_date:
                date = record.production_date
                record.production_month = date.strftime('%Y-%m')
                record.production_week = f"{date.year}-S{date.isocalendar()[1]:02d}"
                quarter = (date.month - 1) // 3 + 1
                record.production_quarter = f"{date.year}-T{quarter}"
                record.production_year = date.year
            else:
                record.production_month = False
                record.production_week = False
                record.production_quarter = False
                record.production_year = False

    # ================== MÉTHODES D'ACTION ==================

    def action_calculate(self):
        """Recalcule tous les coûts"""
        for record in self:
            # Forcer le recalcul
            record._compute_production_data()
            record._compute_quantities()
            record._compute_rates()
            record._compute_costs()
            record._compute_unit_costs()

            record.state = 'calculated'

            # Message de confirmation
            record.message_post(
                body=f"""
                <b>Analyse calculée</b><br/>
                • Quantité produite: {record.qty_produced:.2f}<br/>
                • Quantité bonne: {record.qty_good:.2f}<br/>
                • Taux de rebut: {record.scrap_rate:.1f}%<br/>
                • Coût unitaire réel: {record.unit_cost_real:.2f} {record.currency_id.symbol}
                """
            )

        return True

    def action_validate(self):
        """Valide l'analyse et met à jour le prix de revient du produit"""
        for record in self:
            if record.state != 'calculated':
                raise UserError(_("Seules les analyses calculées peuvent être validées."))

            # Mise à jour du prix de revient si souhaité
            if record.unit_cost_real > 0:
                old_price = record.product_id.standard_price
                record.product_id.sudo().standard_price = record.unit_cost_real

                record.message_post(
                    body=f"""
                    <b>Analyse validée - Prix de revient mis à jour</b><br/>
                    • Ancien prix: {old_price:.2f} {record.currency_id.symbol}<br/>
                    • Nouveau prix: {record.unit_cost_real:.2f} {record.currency_id.symbol}<br/>
                    • Variation: {((record.unit_cost_real - old_price) / old_price * 100):.1f}%
                    """
                )

            record.state = 'validated'

        return True

    def action_cancel(self):
        """Annule l'analyse"""
        for record in self:
            if record.state == 'validated':
                raise UserError(_("Une analyse validée ne peut pas être annulée."))
            record.state = 'cancelled'
        return True

    def action_reset_draft(self):
        """Remet l'analyse en brouillon"""
        for record in self:
            if record.state == 'validated':
                raise UserError(_("Une analyse validée ne peut pas être remise en brouillon."))
            record.state = 'draft'
        return True

    def action_view_details(self):
        """Ouvre la vue détaillée de la production journalière"""
        self.ensure_one()
        if self.daily_production_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Production Journalière',
                'res_model': 'adi.daily.production',
                'res_id': self.daily_production_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True

    def action_view_productions(self):
        """Ouvre la liste des OF associés"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordres de Fabrication',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.production_ids.ids)],
            'context': self.env.context,
        }

    # ================== MÉTHODES UTILITAIRES ==================

    @api.model
    def get_cost_evolution(self, product_id=None, date_from=None, date_to=None):
        """
        Méthode API pour récupérer l'évolution des coûts
        Utilisée pour les graphiques et tableaux de bord
        """
        domain = [('state', 'in', ['calculated', 'validated'])]

        if product_id:
            domain.append(('product_id', '=', product_id))
        if date_from:
            domain.append(('production_date', '>=', date_from))
        if date_to:
            domain.append(('production_date', '<=', date_to))

        records = self.search(domain, order='production_date asc')

        data = []
        for record in records:
            data.append({
                'date': record.production_date.strftime('%Y-%m-%d'),
                'product': record.product_id.name,
                'qty_produced': record.qty_produced,
                'qty_good': record.qty_good,
                'scrap_rate': record.scrap_rate,
                'unit_cost_theoretical': record.unit_cost_theoretical,
                'unit_cost_real': record.unit_cost_real,
                'cost_increase': record.cost_increase,
                'efficiency_rate': record.efficiency_rate
            })

        return data

    @api.model
    def create_from_daily_production(self, daily_production_id):
        """
        Crée une analyse depuis une production journalière
        """
        daily_prod = self.env['adi.daily.production'].browse(daily_production_id)
        if not daily_prod.exists():
            raise ValidationError(_("Production journalière introuvable."))

        # Vérifier si une analyse existe déjà
        existing = self.search([
            ('daily_production_id', '=', daily_production_id)
        ], limit=1)

        if existing:
            return existing

        # Créer une nouvelle analyse
        vals = {
            'production_date': daily_prod.production_date,
            'product_id': daily_prod.product_id.id,
            'daily_production_id': daily_production_id,
            'company_id': daily_prod.company_id.id if daily_prod.company_id else self.env.company.id,
        }

        analysis = self.create(vals)
        analysis.action_calculate()

        return analysis

    @api.model
    def get_dashboard_data(self):
        """
        Retourne les données pour le tableau de bord
        """
        # Données du mois en cours
        today = fields.Date.today()
        month_start = today.replace(day=1)

        current_month_data = self.search([
            ('production_date', '>=', month_start),
            ('production_date', '<=', today),
            ('state', 'in', ['calculated', 'validated'])
        ])

        # Calculs des métriques
        total_production = sum(current_month_data.mapped('qty_produced'))
        total_good = sum(current_month_data.mapped('qty_good'))
        total_scrap = sum(current_month_data.mapped('qty_scrapped'))
        avg_scrap_rate = sum(current_month_data.mapped('scrap_rate')) / len(
            current_month_data) if current_month_data else 0

        # Top 5 produits avec le plus de rebuts
        product_scrap_data = {}
        for record in current_month_data:
            if record.product_id.id not in product_scrap_data:
                product_scrap_data[record.product_id.id] = {
                    'name': record.product_id.name,
                    'scrap_qty': 0,
                    'scrap_cost': 0
                }
            product_scrap_data[record.product_id.id]['scrap_qty'] += record.qty_scrapped
            product_scrap_data[record.product_id.id]['scrap_cost'] += record.scrap_cost

        top_scrap_products = sorted(
            product_scrap_data.values(),
            key=lambda x: x['scrap_cost'],
            reverse=True
        )[:5]

        return {
            'period': f"{today.strftime('%B %Y')}",
            'total_production': total_production,
            'total_good': total_good,
            'total_scrap': total_scrap,
            'avg_scrap_rate': avg_scrap_rate,
            'efficiency_rate': (total_good / total_production * 100) if total_production else 0,
            'top_scrap_products': top_scrap_products,
            'currency': self.env.company.currency_id.symbol
        }

    @api.model
    def cron_create_daily_analysis(self):
        """
        Méthode pour création automatique des analyses (cron)
        """
        yesterday = fields.Date.today() - timedelta(days=1)

        # Recherche des productions journalières sans analyse
        daily_productions = self.env['adi.daily.production'].search([
            ('production_date', '=', yesterday),
            ('state', 'in', ['confirmed', 'validated'])
        ])

        for daily_prod in daily_productions:
            # Vérifier si une analyse existe déjà
            existing = self.search([
                ('daily_production_id', '=', daily_prod.id)
            ], limit=1)

            if not existing:
                self.create_from_daily_production(daily_prod.id)
                _logger.info(f"Analyse créée automatiquement pour {daily_prod.name}")
