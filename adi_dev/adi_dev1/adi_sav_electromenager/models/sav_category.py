# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SavCategory(models.Model):
    _name = 'sav.category'
    _description = 'Catégorie Electroménager'
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
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
    )
    color = fields.Integer(
        string='Couleur',
    )
    return_count = fields.Integer(
        string='Nombre de Retours',
        compute='_compute_return_count',
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Le code de catégorie doit être unique!'),
    ]

    def _compute_return_count(self):
        for rec in self:
            rec.return_count = self.env['sav.return'].search_count([
                ('category_id', '=', rec.id)
            ])

    def action_view_returns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Retours - {self.name}',
            'res_model': 'sav.return',
            'view_mode': 'tree,form,kanban,pivot,graph',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
