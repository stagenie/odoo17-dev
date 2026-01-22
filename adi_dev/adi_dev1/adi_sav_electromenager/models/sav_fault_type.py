# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SavFaultType(models.Model):
    _name = 'sav.fault.type'
    _description = 'Type de Panne'
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
    category_ids = fields.Many2many(
        'sav.category',
        'sav_fault_category_rel',
        'fault_id',
        'category_id',
        string='Catégories applicables',
        help='Laisser vide pour appliquer à toutes les catégories',
    )
    return_count = fields.Integer(
        string='Nombre de Retours',
        compute='_compute_return_count',
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Le code de type de panne doit être unique!'),
    ]

    def _compute_return_count(self):
        for rec in self:
            # Compter les retours uniques qui ont des lignes avec ce type de panne
            lines = self.env['sav.return.line'].search([
                ('fault_type_id', '=', rec.id)
            ])
            rec.return_count = len(lines.mapped('return_id'))
