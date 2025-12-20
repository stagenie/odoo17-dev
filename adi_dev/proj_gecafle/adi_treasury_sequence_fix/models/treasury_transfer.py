# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TreasuryTransferSequenceFix(models.Model):
    _inherit = 'treasury.transfer'

    @api.model_create_multi
    def create(self, vals_list):
        """Override pour utiliser sudo() sur ir.sequence"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                # Utiliser sudo() pour accéder à ir.sequence
                sequence = self.env['ir.sequence'].sudo().search([
                    ('code', '=', 'treasury.transfer'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if not sequence:
                    sequence = self.env['ir.sequence'].sudo().create({
                        'name': 'Transfert de trésorerie',
                        'code': 'treasury.transfer',
                        'prefix': 'TR/%(year)s/',
                        'padding': 5,
                        'company_id': self.env.company.id,
                    })
                vals['name'] = sequence.next_by_id()
        # Appeler le grand-parent pour éviter la double génération
        return super(TreasuryTransferSequenceFix, self).create(vals_list)
