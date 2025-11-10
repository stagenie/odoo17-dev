# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PayrollLine(models.Model):
    """Lignes de détail du bulletin de paie"""
    _name = 'payroll.line'
    _description = 'Ligne de paie'
    _order = 'slip_id, sequence'

    """" """
    # Ajouter un champ pour faciliter la saisie manuelle
    line_type = fields.Selection([
        ('earning', 'Gain (+)'),
        ('deduction', 'Retenue (-)')
    ], string='Type', default='earning', required=True,
        help="Sélectionner si cette rubrique est un gain ou une retenue")

    @api.onchange('line_type')
    def _onchange_line_type(self):
        """Met à jour la catégorie selon le type sélectionné"""
        if self.line_type:
            self.category = self.line_type

    @api.model
    def create(self, vals):
        """S'assure que le type et la catégorie sont synchronisés"""
        if 'line_type' in vals and 'category' not in vals:
            vals['category'] = vals['line_type']
        elif 'category' in vals and 'line_type' not in vals:
            vals['line_type'] = vals['category']
        return super(PayrollLine, self).create(vals)


    slip_id = fields.Many2one(
        'payroll.slip',
        string='Bulletin',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Rubrique',
        required=True
    )

    code = fields.Char(
        string='Code',
        required=True
    )

    category = fields.Selection([
        ('earning', 'Gain'),
        ('deduction', 'Retenue')
    ], string='Catégorie', required=True)

    sequence = fields.Integer(
        string='N°',
        default=10
    )

    quantity = fields.Float(
        string='Nbre/Taux',
        default=1.0
    )

    rate = fields.Monetary(
        string='Montant unitaire'
    )

    # Colonnes séparées pour gains et retenues
    amount_earning = fields.Monetary(
        string='Gain',
        compute='_compute_amounts',
        store=True
    )

    amount_deduction = fields.Monetary(
        string='Retenue',
        compute='_compute_amounts',
        store=True
    )

    currency_id = fields.Many2one(
        related='slip_id.currency_id',
        string='Devise'
    )

    # Référence à l'objet source
    reference_id = fields.Char(
        string='Référence',
        help="Référence vers l'objet source (format: model,id)"
    )

    @api.depends('quantity', 'rate', 'category')
    def _compute_amounts(self):
        """Calcule les montants dans la bonne colonne"""
        for record in self:
            amount = abs(record.quantity * record.rate)
            if record.category == 'earning':
                record.amount_earning = amount
                record.amount_deduction = 0.0
            else:
                record.amount_earning = 0.0
                record.amount_deduction = amount
