# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    reception_valorisee_id = fields.Many2one(
        'gecafle.reception',
        string="Réception Valorisée Source",
        readonly=True,
        domain=[('is_achat_valorise', '=', True)]
    )

    def action_view_reception_source(self):
        """Ouvre la réception valorisée source"""
        self.ensure_one()
        if not self.reception_valorisee_id:
            return False

        return {
            'name': _('Réception Valorisée'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.reception',
            'res_id': self.reception_valorisee_id.id,
            'target': 'current',
        }
