# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleReception(models.Model):
    _inherit = 'gecafle.reception'

    # Nouveaux champs pour gérer les retours
    is_return = fields.Boolean(
        string="Est un retour",
        default=False,
        readonly=True,
        help="Indique si cette réception est un retour suite à un avoir"
    )

    reception_origine_id = fields.Many2one(
        'gecafle.reception',
        string="Réception d'origine",
        readonly=True,
        help="Réception d'origine pour les retours"
    )

    avoir_client_id = fields.Many2one(
        'gecafle.avoir.client',
        string="Avoir client lié",
        readonly=True,
        help="Avoir client qui a généré ce retour"
    )

    # Relations pour tracer les retours
    reception_retour_ids = fields.One2many(
        'gecafle.reception',
        'reception_origine_id',
        string="Réceptions de retour",
        readonly=True
    )

    reception_retour_count = fields.Integer(
        string="Nombre de retours",
        compute='_compute_reception_retour_count'
    )

    @api.depends('reception_retour_ids')
    def _compute_reception_retour_count(self):
        for record in self:
            record.reception_retour_count = len(record.reception_retour_ids)

    def action_view_retours(self):
        """Affiche les réceptions de retour liées"""
        self.ensure_one()

        if self.reception_retour_count == 0:
            raise ValidationError(_("Aucun retour n'est lié à cette réception."))

        action = {
            'name': _('Réceptions de retour'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'gecafle.reception',
            'domain': [('id', 'in', self.reception_retour_ids.ids)],
            'context': {'create': False}
        }

        if self.reception_retour_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reception_retour_ids[0].id,
            })

        return action
