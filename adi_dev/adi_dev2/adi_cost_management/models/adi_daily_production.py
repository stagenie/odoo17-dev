# models/adi_daily_production.py
from odoo import models, fields, api
from datetime import datetime, date


class AdiDailyProduction(models.Model):
    _name = 'adi.daily.production'
    _description = 'Production Journalière avec Coûts'
    _rec_name = 'name'
    _order = 'production_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        'Référence',
        required=True,
        default='Nouveau',
        copy=False,
        tracking=True  # Activer le tracking pour le chatter
    )
    production_date = fields.Date(
        'Date de Production',
        required=True,
        default=fields.Date.today
    )

    def action_print_report(self):
        """Lance l'impression du rapport PDF"""
        self.ensure_one()

        # Méthode sûre qui cherche l'action et la lance
        try:
            # Essayer de récupérer l'action
            report_action = self.env.ref('adi_cost_management.action_report_cost_analysis', False)
            if report_action:
                return report_action.report_action(self)
        except:
            pass

        # Alternative : lancer directement le rapport
        return {
            'type': 'ir.actions.report',
            'report_name': 'adi_cost_management.report_cost_analysis_document',
            'report_type': 'qweb-pdf',
            'data': None,
            'docids': self.ids,
            'context': self.env.context,
        }

    # Liens avec les OF
    production_ids = fields.Many2many(
        'mrp.production',
        'adi_daily_production_mrp_rel',
        'daily_id',
        'production_id',
        string='Ordres de Fabrication',
        domain=[('state', '=', 'done')]
    )

    # Produits et quantités
    product_id = fields.Many2one(
        'product.product',
        'Produit Fabriqué',
        required=True,
        tracking=True,  # Ajouter le tracking,
        domain=[('type', '=', 'product')]
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        'Nomenclature',
        compute='_compute_bom',
        store=True
    )

    qty_produced = fields.Float(
        'Quantité Produite',
        compute='_compute_quantities',
        store=True,
        help="Quantité totale produite dans les OF"
    )

    # Coûts de fabrication
    raw_material_cost = fields.Monetary(
        'Coût Matières Premières',
        compute='_compute_production_costs',
        store=True,
        currency_field='currency_id'
    )

    total_production_cost = fields.Monetary(
        'Coût Total de Fabrication',
        compute='_compute_production_costs',
        store=True,
        help="Coût total basé sur la nomenclature"
    )

    # Rebuts liés
    scrap_ids = fields.One2many(
        'adi.scrap.management',
        'daily_production_id',
        'Rebuts du Jour'
    )

    total_scrap_cost = fields.Monetary(
        'Coût Total des Rebuts',
        compute='_compute_scrap_costs',
        store=True
    )

    # Calcul final
    qty_good = fields.Float(
        'Quantité Bonne',
        compute='_compute_final_cost',
        store=True,
        help="Quantité produite - rebuts"
    )

    total_cost_with_scrap = fields.Monetary(
        'Coût Total (Production + Rebuts)',
        compute='_compute_final_cost',
        store=True
    )

    unit_cost_theoretical = fields.Monetary(
        'Coût Unitaire Théorique',
        compute='_compute_final_cost',
        store=True
    )

    unit_cost_real = fields.Monetary(
        'Coût Unitaire Réel',
        compute='_compute_final_cost',
        store=True,
        tracking=True,
        help="Coût unitaire incluant l'impact des rebuts"
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé')
    ], default='draft', string='État',tracking=True)

    def action_create_cost_analysis(self):
        """Créer une analyse de coût depuis cette production"""
        self.ensure_one()

        # Vérifier si une analyse existe déjà
        existing = self.env['adi.cost.analysis'].sudo().search([
            ('daily_production_id', '=', self.id)
        ], limit=1)

        if existing:
            # Ouvrir l'analyse existante
            return {
                'type': 'ir.actions.act_window',
                'name': 'Analyse des Coûts',
                'res_model': 'adi.cost.analysis',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Créer une nouvelle analyse
        analysis = self.env['adi.cost.analysis'].sudo().create({
            'production_date': self.production_date,
            'product_id': self.product_id.id,
            'daily_production_id': self.id,
        })

        # Calculer automatiquement
        analysis.action_calculate()

        # Ouvrir la vue formulaire
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse des Coûts',
            'res_model': 'adi.cost.analysis',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('adi.daily.production') or 'Nouveau'
        return super().create(vals)

    @api.depends('product_id')
    def _compute_bom(self):
        for rec in self:
            bom = self.env['mrp.bom'].search([
                ('product_id', '=', rec.product_id.id)
            ], limit=1)
            rec.bom_id = bom

    @api.depends('production_ids')
    def _compute_quantities(self):
        for rec in self:
            rec.qty_produced = sum(
                production.qty_produced
                for production in rec.production_ids
            )

    @api.depends('production_ids', 'bom_id')
    def _compute_production_costs(self):
        for rec in self:
            total_cost = 0.0

            # Calcul basé sur les consommations réelles des OF
            for production in rec.production_ids:
                # Coût des matières consommées
                for move in production.move_raw_ids.filtered(lambda m: m.state == 'done'):
                    total_cost += move.quantity * move.product_id.standard_price

            rec.raw_material_cost = total_cost
            rec.total_production_cost = total_cost

    @api.depends('scrap_ids')
    def _compute_scrap_costs(self):
        for rec in self:
            rec.total_scrap_cost = sum(scrap.total_cost for scrap in rec.scrap_ids)

    @api.depends('qty_produced', 'scrap_ids', 'total_production_cost', 'total_scrap_cost')
    def _compute_final_cost(self):
        for rec in self:
            # Quantité de rebuts en unités équivalentes
            scrap_qty = sum(
                scrap.qty_kg / scrap.product_weight
                for scrap in rec.scrap_ids
                if scrap.product_weight > 0 and scrap.scrap_type == 'finished'
            )

            rec.qty_good = rec.qty_produced - scrap_qty
            rec.total_cost_with_scrap = rec.total_production_cost + rec.total_scrap_cost

            # Coût unitaire théorique (sans rebuts)
            if rec.qty_produced > 0:
                rec.unit_cost_theoretical = rec.total_production_cost / rec.qty_produced
            else:
                rec.unit_cost_theoretical = 0

            # Coût unitaire réel (avec impact des rebuts)
            if rec.qty_good > 0:
                rec.unit_cost_real = rec.total_production_cost / rec.qty_good
            else:
                rec.unit_cost_real = 0

    def action_calculate_cost(self):
        """Recalcule les coûts"""
        self._compute_production_costs()
        self._compute_scrap_costs()
        self._compute_final_cost()

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_validate(self):
        """Valide et met à jour le prix de revient du produit"""
        self.ensure_one()
        if self.unit_cost_real > 0 and self.product_id:
            self.product_id.sudo().standard_price = self.unit_cost_real

        self.write({'state': 'validated'})
