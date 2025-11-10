# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleVenteAvoirAutomation(models.Model):
    _inherit = 'gecafle.vente'

    def action_create_avoir_express(self):
        """Ouvre un wizard pour créer un avoir avec automatisation"""
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("Vous ne pouvez créer un avoir que pour une vente validée."))

        # Ouvrir le wizard de création d'avoir
        return {
            'name': _('Création Express d\'Avoir'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client.wizard',
            'target': 'new',
            'context': {
                'default_vente_id': self.id,
                'default_montant_avoir': self.montant_total_a_payer * 0.1,  # Suggérer 10% par défaut
                'default_type_avoir': self.env.company.avoir_default_type or 'non_vendu',
                'default_description': _('Avoir express'),
                'force_automation': True,
            }
        }
