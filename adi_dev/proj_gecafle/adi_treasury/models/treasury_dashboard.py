# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TreasuryDashboard(models.TransientModel):
    _name = 'treasury.dashboard'
    _description = 'Tableau de bord Trésorerie'

    name = fields.Char(
        string='Nom',
        default='Tableau de Bord Trésorerie',
        readonly=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur',
        default=lambda self: self.env.user,
        readonly=True
    )

    # Filtres de date (gardés pour compatibilité mais cachés)
    date_from = fields.Date(
        string='Date début',
        default=fields.Date.today
    )
    date_to = fields.Date(
        string='Date fin',
        default=fields.Date.today
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    # Totaux globaux
    total_cash_balance = fields.Monetary(
        string='Solde global Caisses',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )
    total_safe_balance = fields.Monetary(
        string='Solde global Coffres',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )

    # Lignes détaillées
    cash_line_ids = fields.One2many(
        'treasury.dashboard.cash.line',
        'dashboard_id',
        string='Caisses',
        compute='_compute_dashboard_data'
    )
    safe_line_ids = fields.One2many(
        'treasury.dashboard.safe.line',
        'dashboard_id',
        string='Coffres',
        compute='_compute_dashboard_data'
    )

    @api.model
    def action_open_dashboard(self):
        """Ouvre le tableau de bord en réutilisant l'enregistrement existant de l'utilisateur"""
        existing = self.search([('user_id', '=', self.env.user.id)], limit=1)

        if existing:
            dashboard = existing
        else:
            dashboard = self.create({
                'user_id': self.env.user.id,
            })

        return {
            'name': _('Tableau de Bord Trésorerie'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'view_id': self.env.ref('adi_treasury.view_treasury_dashboard_form').id,
            'target': 'inline',
        }

    def _compute_dashboard_data(self):
        for record in self:
            # ============ CAISSES ============
            cashes = self.env['treasury.cash'].search([('state', '=', 'open')])
            total_cash_balance = 0.0
            cash_lines = []

            for cash in cashes:
                total_cash_balance += cash.current_balance
                cash_lines.append({
                    'dashboard_id': record.id,
                    'cash_id': cash.id,
                    'name': cash.name,
                    'code': cash.code,
                    'current_balance': cash.current_balance,
                })

            record.total_cash_balance = total_cash_balance
            record.cash_line_ids = self.env['treasury.dashboard.cash.line'].create(cash_lines)

            # ============ COFFRES ============
            safes = self.env['treasury.safe'].search([('state', '=', 'active')])
            total_safe_balance = 0.0
            safe_lines = []

            for safe in safes:
                total_safe_balance += safe.current_balance
                safe_lines.append({
                    'dashboard_id': record.id,
                    'safe_id': safe.id,
                    'name': safe.name,
                    'code': safe.code,
                    'current_balance': safe.current_balance,
                })

            record.total_safe_balance = total_safe_balance
            record.safe_line_ids = self.env['treasury.dashboard.safe.line'].create(safe_lines)

    def action_refresh(self):
        """Rafraîchir le tableau de bord"""
        return {
            'name': _('Tableau de Bord Trésorerie'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('adi_treasury.view_treasury_dashboard_form').id,
            'target': 'inline',
        }


class TreasuryDashboardCashLine(models.TransientModel):
    _name = 'treasury.dashboard.cash.line'
    _description = 'Ligne Caisse Dashboard'

    dashboard_id = fields.Many2one('treasury.dashboard', string='Dashboard')
    cash_id = fields.Many2one('treasury.cash', string='Caisse')
    name = fields.Char(string='Nom')
    code = fields.Char(string='Code')
    current_balance = fields.Monetary(string='Solde actuel', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )


class TreasuryDashboardSafeLine(models.TransientModel):
    _name = 'treasury.dashboard.safe.line'
    _description = 'Ligne Coffre Dashboard'

    dashboard_id = fields.Many2one('treasury.dashboard', string='Dashboard')
    safe_id = fields.Many2one('treasury.safe', string='Coffre')
    name = fields.Char(string='Nom')
    code = fields.Char(string='Code')
    current_balance = fields.Monetary(string='Solde actuel', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
