# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductionTransferDashboard(models.TransientModel):
    _name = 'production.transfer.dashboard'
    _description = 'Tableau de bord des transferts de production'

    # KPIs
    transfers_today = fields.Integer(
        string='Transferts aujourd\'hui',
        compute='_compute_kpis'
    )
    transfers_pending = fields.Integer(
        string='En attente',
        compute='_compute_kpis'
    )
    transfers_completed = fields.Integer(
        string='Complétés (7j)',
        compute='_compute_kpis'
    )
    products_shortage = fields.Integer(
        string='Produits en rupture',
        compute='_compute_kpis'
    )

    # Statistiques
    transfer_stats = fields.One2many(
        'production.transfer.stats',
        compute='_compute_stats'
    )
    warehouse_stats = fields.One2many(
        'production.warehouse.stats',
        compute='_compute_stats'
    )

    # Listes
    stock_alerts = fields.One2many(
        'production.stock.alert',
        compute='_compute_alerts'
    )
    recent_transfers = fields.One2many(
        'stock.picking',
        compute='_compute_recent_transfers'
    )

    @api.depends_context('uid')
    def _compute_kpis(self):
        for record in self:
            today = fields.Date.today()
            week_ago = today - timedelta(days=7)

            # Domaine de base pour les transferts de production
            base_domain = [
                ('picking_type_id.code', '=', 'internal'),
                ('origin', 'ilike', 'BOM/')
            ]

            # Transferts aujourd'hui
            record.transfers_today = self.env['stock.picking'].search_count(
                base_domain + [('scheduled_date', '>=', today), ('scheduled_date', '<', today + timedelta(days=1))]
            )

            # En attente
            record.transfers_pending = self.env['stock.picking'].search_count(
                base_domain + [('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])]
            )

            # Complétés cette semaine
            record.transfers_completed = self.env['stock.picking'].search_count(
                base_domain + [
                    ('state', '=', 'done'),
                    ('date_done', '>=', week_ago)
                ]
            )

            # Produits en rupture
            company = self.env.company
            if company.production_warehouse_id:
                location = company.production_warehouse_id.lot_stock_id
                products = self.env['product.product'].search([
                    ('type', '=', 'product'),
                    ('bom_line_ids', '!=', False)
                ])

                shortage_count = 0
                for product in products:
                    qty = product.with_context(location=location.id).qty_available
                    if qty <= 0:
                        shortage_count += 1

                record.products_shortage = shortage_count
            else:
                record.products_shortage = 0

    def _compute_stats(self):
        for record in self:
            # Stats temporaires - à implémenter avec de vrais modèles
            record.transfer_stats = []
            record.warehouse_stats = []

    def _compute_alerts(self):
        for record in self:
            # Alertes temporaires - à implémenter avec de vrais modèles
            record.stock_alerts = []

    def _compute_recent_transfers(self):
        for record in self:
            record.recent_transfers = self.env['stock.picking'].search([
                ('picking_type_id.code', '=', 'internal'),
                ('origin', 'ilike', 'BOM/')
            ], limit=10, order='create_date desc')

    def action_create_transfer(self):
        """Ouvre l'assistant de création de transfert"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_all_transfers(self):
        """Affiche tous les transferts"""
        return self.env.ref('adi_production_warehouse_transfer.action_production_transfers').read()[0]

    def action_refresh(self):
        """Actualise le tableau de bord"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'production.transfer.dashboard',
            'view_mode': 'form',
            'target': 'inline',
        }


class ProductionStockAlert(models.TransientModel):
    """Modèle temporaire pour les alertes stock"""
    _name = 'production.stock.alert'
    _description = 'Alerte stock production'

    product_id = fields.Many2one('product.product', string='Produit')
    warehouse_id = fields.Many2one('stock.warehouse', string='Entrepôt')
    qty_available = fields.Float(string='Quantité disponible')
    qty_needed = fields.Float(string='Quantité requise')


class ProductionTransferStats(models.TransientModel):
    """Statistiques mensuelles des transferts"""
    _name = 'production.transfer.stats'
    _description = 'Statistiques transferts'

    month = fields.Char(string='Mois')
    count = fields.Integer(string='Nombre')


class ProductionWarehouseStats(models.TransientModel):
    """Statistiques par entrepôt"""
    _name = 'production.warehouse.stats'
    _description = 'Statistiques entrepôt'

    warehouse_id = fields.Many2one('stock.warehouse', string='Entrepôt')
    transfer_count = fields.Integer(string='Nombre de transferts')
