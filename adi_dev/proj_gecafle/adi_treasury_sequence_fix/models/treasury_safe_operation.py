# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TreasurySafeOperationSequenceFix(models.Model):
    _inherit = 'treasury.safe.operation'

    @api.model_create_multi
    def create(self, vals_list):
        """Override pour utiliser sudo() sur ir.sequence"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                # Générer une référence spéciale pour l'initialisation
                if vals.get('operation_type') == 'initial':
                    vals['name'] = f"INIT/{vals.get('safe_id', '')}/{fields.Date.today()}"
                else:
                    # Utiliser sudo() pour accéder à ir.sequence
                    sequence = self.env['ir.sequence'].sudo().search([
                        ('code', '=', 'treasury.safe.operation'),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    if not sequence:
                        sequence = self.env['ir.sequence'].sudo().create({
                            'name': 'Opération coffre',
                            'code': 'treasury.safe.operation',
                            'prefix': 'OP/%(year)s/',
                            'padding': 5,
                            'company_id': self.env.company.id,
                        })
                    vals['name'] = sequence.next_by_id()
        # Appeler le grand-parent pour éviter la double génération
        return super(TreasurySafeOperationSequenceFix, self).create(vals_list)
