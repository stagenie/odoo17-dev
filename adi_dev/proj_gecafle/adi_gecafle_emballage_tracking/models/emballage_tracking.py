# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class GecafleEmballageTracking(models.Model):
    _name = 'gecafle.emballage.tracking'
    _description = 'Tracking des Emballages'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'emballage_id'

    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string='Emballage',
        required=True,
        ondelete='restrict'
    )

    # Configuration
    is_tracked = fields.Boolean(
        string='Suivi actif',
        default=True,
        tracking=True
    )

    stock_initial = fields.Integer(
        string='Stock initial',
        default=0,
        tracking=True
    )

    # Stocks calculés
    stock_disponible = fields.Integer(
        string='Stock disponible',
        compute='_compute_stocks',
        store=True
    )

    stock_chez_clients = fields.Integer(
        string='Chez clients',
        compute='_compute_stocks',
        store=True
    )

    stock_chez_producteurs = fields.Integer(
        string='Chez producteurs',
        compute='_compute_stocks',
        store=True
    )

    stock_total = fields.Integer(
        string='Stock total',
        compute='_compute_stocks',
        store=True
    )

    # Mouvements liés
    mouvement_ids = fields.One2many(
        'gecafle.emballage.mouvement',
        'tracking_id',
        string='Mouvements'
    )

    mouvement_count = fields.Integer(
        string='Nombre de mouvements',
        compute='_compute_mouvement_count'
    )

    # Statistiques
    last_movement_date = fields.Datetime(
        string='Dernier mouvement',
        compute='_compute_last_movement'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    @api.depends('mouvement_ids', 'mouvement_ids.quantite', 'mouvement_ids.type_mouvement',
                 'mouvement_ids.is_cancelled')
    def _compute_stocks(self):
        """Calcule les stocks par emplacement"""
        for record in self:
            stock_disponible = record.stock_initial
            stock_clients = 0
            stock_producteurs = 0

            # Filtrer les mouvements non annulés
            active_mouvements = record.mouvement_ids.filtered(lambda m: not m.is_cancelled)

            for mouvement in active_mouvements:
                if mouvement.type_mouvement == 'sortie_vente':
                    stock_disponible -= mouvement.quantite
                    stock_clients += mouvement.quantite
                elif mouvement.type_mouvement in ['retour_client', 'consigne']:  # Ajout de 'consigne'
                    stock_disponible += mouvement.quantite
                    stock_clients -= mouvement.quantite
                elif mouvement.type_mouvement == 'entree_reception':
                    stock_disponible += mouvement.quantite
                    stock_producteurs -= mouvement.quantite
                elif mouvement.type_mouvement == 'sortie_producteur':
                    stock_disponible -= mouvement.quantite
                    stock_producteurs += mouvement.quantite
                elif mouvement.type_mouvement == 'retour_producteur':
                    stock_disponible += mouvement.quantite
                    stock_producteurs -= mouvement.quantite
                elif mouvement.type_mouvement == 'regularisation':
                    if mouvement.sens == 'entree':
                        stock_disponible += mouvement.quantite
                    else:
                        stock_disponible -= mouvement.quantite

            record.stock_disponible = stock_disponible
            record.stock_chez_clients = stock_clients
            record.stock_chez_producteurs = stock_producteurs
            record.stock_total = stock_disponible + stock_clients + stock_producteurs

    @api.depends('mouvement_ids')
    def _compute_mouvement_count(self):
        for record in self:
            record.mouvement_count = len(record.mouvement_ids)

    @api.depends('mouvement_ids.date')
    def _compute_last_movement(self):
        for record in self:
            if record.mouvement_ids:
                record.last_movement_date = max(record.mouvement_ids.mapped('date'))
            else:
                record.last_movement_date = False

    def action_view_mouvements(self):
        """Affiche les mouvements de cet emballage"""
        return {
            'name': _('Mouvements - %s') % self.emballage_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.emballage.mouvement',
            'view_mode': 'list,form',
            'domain': [('tracking_id', '=', self.id)],
            'context': {'default_tracking_id': self.id}
        }

    def action_regulariser(self):
        """Ouvre le wizard de régularisation"""
        return {
            'name': _('Régularisation'),
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.emballage.regularisation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_tracking_id': self.id,
                'default_emballage_id': self.emballage_id.id,
            }
        }
