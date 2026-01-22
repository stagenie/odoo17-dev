# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Champs pour identifier les points de vente SAV
    is_sales_point = fields.Boolean(
        string='Est un Point de Vente',
        default=False,
        help='Cocher si ce partenaire est un point de vente pour le SAV électroménager',
    )
    sales_point_code = fields.Char(
        string='Code Point de Vente',
        help='Code unique du point de vente (Ex: ADRAR, BECHAR, MECHRIA)',
    )
    parent_return_center_id = fields.Many2one(
        'res.partner',
        string='Centre de Retour Rattaché',
        domain="[('is_return_center', '=', True)]",
        help='Centre de retour SAV auquel ce point de vente est rattaché',
    )

    # Champ pour identifier les réparateurs
    is_repairer = fields.Boolean(
        string='Est un Réparateur',
        default=False,
        help='Cocher si ce partenaire est un réparateur pour le SAV',
    )
    is_default_repairer = fields.Boolean(
        string='Réparateur par Défaut',
        default=False,
        help='Cocher pour utiliser ce réparateur par défaut dans les retours SAV',
    )

    # Champ pour identifier les centres de retour
    is_return_center = fields.Boolean(
        string='Est un Centre de Retour',
        default=False,
        help='Cocher si ce partenaire est un centre de retour SAV',
    )
    is_default_return_center = fields.Boolean(
        string='Centre de Retour par Défaut',
        default=False,
        help='Cocher pour utiliser ce centre de retour par défaut dans les retours SAV',
    )

    # Champ pour identifier l'usine
    is_factory = fields.Boolean(
        string='Est une Usine',
        default=False,
        help='Cocher si ce partenaire est l\'usine/fabricant pour le SAV',
    )
    is_default_factory = fields.Boolean(
        string='Usine par Défaut',
        default=False,
        help='Cocher pour utiliser cette usine par défaut dans les retours SAV',
    )

    @api.constrains('is_default_repairer')
    def _check_unique_default_repairer(self):
        for partner in self:
            if partner.is_default_repairer:
                existing = self.search([
                    ('is_default_repairer', '=', True),
                    ('id', '!=', partner.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        f'Il ne peut y avoir qu\'un seul réparateur par défaut. '
                        f'"{existing.name}" est déjà défini comme réparateur par défaut.'
                    )

    @api.constrains('is_default_return_center')
    def _check_unique_default_return_center(self):
        for partner in self:
            if partner.is_default_return_center:
                existing = self.search([
                    ('is_default_return_center', '=', True),
                    ('id', '!=', partner.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        f'Il ne peut y avoir qu\'un seul centre de retour par défaut. '
                        f'"{existing.name}" est déjà défini comme centre de retour par défaut.'
                    )

    @api.constrains('is_default_factory')
    def _check_unique_default_factory(self):
        for partner in self:
            if partner.is_default_factory:
                existing = self.search([
                    ('is_default_factory', '=', True),
                    ('id', '!=', partner.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        f'Il ne peut y avoir qu\'une seule usine par défaut. '
                        f'"{existing.name}" est déjà définie comme usine par défaut.'
                    )

    # Compteurs pour smart buttons
    sav_return_count = fields.Integer(
        string='Nombre de Retours SAV',
        compute='_compute_sav_return_count',
    )

    @api.depends('is_sales_point', 'is_return_center')
    def _compute_sav_return_count(self):
        """Compte le nombre de retours SAV liés à ce partenaire."""
        for partner in self:
            count = 0
            if partner.is_sales_point:
                count = self.env['sav.return'].search_count([
                    ('sales_point_id', '=', partner.id)
                ])
            elif partner.is_return_center:
                count = self.env['sav.return'].search_count([
                    ('return_center_id', '=', partner.id)
                ])
            partner.sav_return_count = count

    def action_view_sav_returns(self):
        """Affiche les retours SAV liés à ce partenaire."""
        self.ensure_one()
        domain = []
        if self.is_sales_point:
            domain = [('sales_point_id', '=', self.id)]
        elif self.is_return_center:
            domain = [('return_center_id', '=', self.id)]
        else:
            domain = ['|', ('sales_point_id', '=', self.id), ('return_center_id', '=', self.id)]

        return {
            'name': 'Retours SAV',
            'type': 'ir.actions.act_window',
            'res_model': 'sav.return',
            'view_mode': 'tree,form,kanban',
            'domain': domain,
            'context': {'default_sales_point_id': self.id if self.is_sales_point else False},
        }
