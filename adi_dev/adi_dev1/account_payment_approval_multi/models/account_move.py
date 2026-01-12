# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    """Réordonne les états pour que 'En Attente de Validation' soit juste avant 'Comptabilisé'"""
    _inherit = "account.move"

    state = fields.Selection(
        selection_add=[
            ('waiting_approval', 'En Attente de Validation'),
            ('posted', 'Comptabilisé'),  # Renomme et positionne waiting_approval juste avant
            ('approved', 'Approuvé'),
            ('rejected', 'Rejeté'),
        ],
        ondelete={
            'waiting_approval': 'set default',
            'approved': 'set default',
            'rejected': 'set default'
        }
    )
