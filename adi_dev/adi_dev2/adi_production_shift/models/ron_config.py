# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class RonProductionConfigShift(models.Model):
    _inherit = 'ron.production.config'

    # -------------------------------------------------------------------------
    # Configuration du système de shift
    # -------------------------------------------------------------------------
    shift_system = fields.Selection([
        ('no_shift', '8 heures (pas de shift)'),
        ('two_shifts', '2 Shifts (Jour/Nuit)'),
        ('three_shifts', '3 Shifts (Matin/Après-midi/Nuit)'),
    ], string="Système de Shift", default='no_shift', required=True,
       help="Définit le nombre de productions autorisées par jour:\n"
            "- 8 heures : 1 production par jour (comportement par défaut)\n"
            "- 2 Shifts : 2 productions par jour (Jour et Nuit)\n"
            "- 3 Shifts : 3 productions par jour (Matin, Après-midi et Nuit)")
