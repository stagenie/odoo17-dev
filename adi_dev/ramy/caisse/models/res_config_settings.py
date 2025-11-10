# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_type_c= fields.Selection([
        ('mensuel','Mensuelle'),
        ('daily','Journalière'),
        ],string="Cloture de caisse",  default_model="caisse",
        help="Type de cloture de caisse. ", default="mensuel")
    default_precedent_cash = fields.Boolean(string="Caisse précédente obligatoire", default_model="caisse",)
    default_get_balance_end_real = fields.Boolean(string="Réintroduire le Solde Physique (Réel)", default_model="caisse",)
    # default_get_impact_caisse_ecart = fields.Boolean(string="Impact des écarts sur la caisse", default_model="caisse",)
    default_show_confg_initial_balance = fields.Boolean(string="Configuration de la balance initiale", default_model="caisse",)

    @api.onchange('default_show_confg_initial_balance')
    def onchange_field(self):
        caisse = self.env['caisse'].search([])
        for c in caisse:
            c.show_confg_initial_balance = self.default_show_confg_initial_balance
    