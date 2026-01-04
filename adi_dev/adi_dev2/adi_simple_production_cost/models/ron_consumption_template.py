# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonConsumptionTemplate(models.Model):
    """
    Template de consommation pour les matières premières.

    Un seul template actif par société. Définit la liste des matières
    premières utilisées en production (même pâte pour SOLO/CLASSICO/Sandwich).
    Les quantités sont saisies manuellement chaque jour.
    """
    _name = 'ron.consumption.template'
    _description = 'Template de Consommation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Nom',
        required=True,
        default='Template Principal',
        tracking=True
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True,
        help="Un seul template actif par société. "
             "Décocher pour archiver ce template."
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    line_ids = fields.One2many(
        'ron.consumption.template.line',
        'template_id',
        string='Matières Premières',
        copy=True
    )

    notes = fields.Text(string='Notes')

    # Champs calculés
    line_count = fields.Integer(
        string='Nb Matières',
        compute='_compute_line_count'
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.constrains('active', 'company_id')
    def _check_unique_active(self):
        """Vérifie qu'il n'y a qu'un seul template actif par société."""
        for rec in self:
            if rec.active:
                other_active = self.search([
                    ('active', '=', True),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ])
                if other_active:
                    raise ValidationError(_(
                        "Il ne peut y avoir qu'un seul template actif par société.\n"
                        "Template actif existant: %s"
                    ) % other_active[0].name)

    @api.model
    def get_active_template(self, company_id=None):
        """Récupère le template actif pour une société.

        Args:
            company_id: ID de la société (optionnel, utilise la société courante)

        Returns:
            ron.consumption.template record ou False
        """
        if not company_id:
            company_id = self.env.company.id

        return self.search([
            ('active', '=', True),
            ('company_id', '=', company_id)
        ], limit=1)

    def action_view_lines(self):
        """Ouvre la liste des matières premières."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Matières Premières - %s') % self.name,
            'res_model': 'ron.consumption.template.line',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }


class RonConsumptionTemplateLine(models.Model):
    """
    Ligne de template de consommation.

    Définit une matière première avec son poids par unité.
    La quantité sera saisie manuellement lors de chaque production.
    """
    _name = 'ron.consumption.template.line'
    _description = 'Ligne Template Consommation'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'ron.consumption.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10
    )

    product_id = fields.Many2one(
        'product.product',
        string='Matière Première',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
        help="Produit stockable ou consommable"
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unité',
        related='product_id.uom_id',
        readonly=True
    )

    weight_per_unit = fields.Float(
        string='Poids/Unité (kg)',
        digits='Stock Weight',
        default=1.0,
        help="Poids en kg par unité de mesure.\n"
             "Ex: Pour un sac de 25kg, mettre 25.0\n"
             "Modifiable lors de la saisie de production."
    )

    company_id = fields.Many2one(
        related='template_id.company_id',
        string='Société',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-détecte le poids depuis le produit ou son nom."""
        if self.product_id:
            # Essayer de récupérer le poids depuis le produit
            if self.product_id.weight:
                self.weight_per_unit = self.product_id.weight
            else:
                # Essayer de déduire du nom (ex: "Farine 25kg")
                import re
                name = self.product_id.name or ''
                match = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', name, re.IGNORECASE)
                if match:
                    self.weight_per_unit = float(match.group(1).replace(',', '.'))
                else:
                    self.weight_per_unit = 1.0

    @api.constrains('weight_per_unit')
    def _check_weight(self):
        for line in self:
            if line.weight_per_unit < 0:
                raise ValidationError(_("Le poids par unité ne peut pas être négatif."))
