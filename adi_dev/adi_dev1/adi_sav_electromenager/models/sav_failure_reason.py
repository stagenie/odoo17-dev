# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SavFailureReason(models.Model):
    _name = 'sav.failure.reason'
    _description = 'Motif d\'Échec de Réparation'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )
    description = fields.Text(
        string='Description',
        help='Description détaillée du motif d\'échec',
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
    )
    color = fields.Integer(
        string='Couleur',
    )

    # Statistiques
    usage_count = fields.Integer(
        string='Nombre d\'Utilisations',
        compute='_compute_usage_count',
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Le code de motif d\'échec doit être unique!'),
    ]

    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = self.env['sav.return.line'].search_count([
                ('failure_reason_id', '=', rec.id)
            ])

    def action_view_returns(self):
        """Ouvre la liste des retours utilisant ce motif d'échec"""
        self.ensure_one()
        lines = self.env['sav.return.line'].search([
            ('failure_reason_id', '=', self.id)
        ])
        return_ids = lines.mapped('return_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': f'Retours - {self.name}',
            'res_model': 'sav.return',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', return_ids)],
            'context': {'create': False},
        }
