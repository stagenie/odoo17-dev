# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TreasuryCashOperationSequenceFix(models.Model):
    _inherit = 'treasury.cash.operation'

    @api.model_create_multi
    def create(self, vals_list):
        """Override pour utiliser sudo() sur ir.sequence"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                # Utiliser sudo() pour accéder à ir.sequence
                sequence = self.env['ir.sequence'].sudo().search([
                    ('code', '=', 'treasury.cash.operation'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if not sequence:
                    sequence = self.env['ir.sequence'].sudo().create({
                        'name': 'Opération de caisse',
                        'code': 'treasury.cash.operation',
                        'prefix': 'OPC/%(year)s/',
                        'padding': 5,
                        'company_id': self.env.company.id,
                    })
                vals['name'] = sequence.next_by_id()
        # Appeler le grand-parent pour éviter la double génération
        return super(TreasuryCashOperationSequenceFix, self).create(vals_list)
