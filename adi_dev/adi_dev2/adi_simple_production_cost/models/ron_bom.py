# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonBom(models.Model):
    """
    Nomenclature simplifiée pour les produits RON.

    Une seule nomenclature validée par type de produit.
    Les quantités sont définies par carton de produit fini.
    """
    _name = 'ron.bom'
    _description = 'Nomenclature RON'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'product_type, state desc, id desc'

    name = fields.Char(
        string='Nom',
        required=True,
        tracking=True
    )

    product_type = fields.Selection([
        ('solo', 'SOLO'),
        ('classico', 'CLASSICO'),
        ('sandwich_gf', 'Sandwich Grand Format'),
    ], string='Type de Produit', required=True, tracking=True,
       help="Type de produit fini pour cette nomenclature")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validée'),
    ], string='État', default='draft', tracking=True,
       help="Seule une nomenclature validée par type de produit est utilisée en production")

    active = fields.Boolean(
        string='Actif',
        default=True,
        help="Décocher pour archiver la nomenclature"
    )

    line_ids = fields.One2many(
        'ron.bom.line',
        'bom_id',
        string='Composants',
        copy=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    notes = fields.Text(string='Notes')

    # Champs calculés
    component_count = fields.Integer(
        string='Nb Composants',
        compute='_compute_component_count'
    )

    @api.depends('line_ids')
    def _compute_component_count(self):
        for rec in self:
            rec.component_count = len(rec.line_ids)

    def action_validate(self):
        """Valide la nomenclature et passe les autres du même type en brouillon."""
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Impossible de valider une nomenclature sans composants."))

            # Passer les autres nomenclatures validées du même type en brouillon
            other_validated = self.search([
                ('product_type', '=', rec.product_type),
                ('company_id', '=', rec.company_id.id),
                ('state', '=', 'validated'),
                ('id', '!=', rec.id)
            ])
            if other_validated:
                other_validated.write({'state': 'draft'})

            rec.write({'state': 'validated'})

    def action_set_draft(self):
        """Remet la nomenclature en brouillon."""
        self.write({'state': 'draft'})

    @api.model
    def get_validated_bom(self, product_type, company_id=None):
        """Récupère la nomenclature validée pour un type de produit.

        Args:
            product_type: 'solo', 'classico' ou 'sandwich_gf'
            company_id: ID de la société (optionnel, utilise la société courante par défaut)

        Returns:
            ron.bom record ou False si aucune nomenclature validée
        """
        if not company_id:
            company_id = self.env.company.id

        return self.search([
            ('product_type', '=', product_type),
            ('company_id', '=', company_id),
            ('state', '=', 'validated'),
            ('active', '=', True)
        ], limit=1)

    def action_view_components(self):
        """Ouvre la liste des composants."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Composants de %s') % self.name,
            'res_model': 'ron.bom.line',
            'view_mode': 'tree,form',
            'domain': [('bom_id', '=', self.id)],
            'context': {'default_bom_id': self.id},
        }


class RonBomLine(models.Model):
    """
    Ligne de nomenclature (composant).

    Définit la quantité de matière première nécessaire par carton de produit fini.
    """
    _name = 'ron.bom.line'
    _description = 'Ligne de Nomenclature RON'
    _order = 'sequence, id'

    bom_id = fields.Many2one(
        'ron.bom',
        string='Nomenclature',
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
        string='Composant',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
        help="Matière première ou consommable"
    )

    quantity = fields.Float(
        string='Quantité / Carton',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
        help="Quantité de ce composant nécessaire pour produire UN carton"
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unité',
        related='product_id.uom_id',
        readonly=True
    )

    product_type = fields.Selection(
        related='bom_id.product_type',
        string='Type de Produit',
        store=True
    )

    company_id = fields.Many2one(
        related='bom_id.company_id',
        string='Société',
        store=True
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("La quantité doit être supérieure à 0."))
