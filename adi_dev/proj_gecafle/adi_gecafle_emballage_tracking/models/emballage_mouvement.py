# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleEmballageMouvement(models.Model):
    _name = 'gecafle.emballage.mouvement'
    _description = 'Mouvement d\'Emballage'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default='Nouveau'
    )

    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    tracking_id = fields.Many2one(
        'gecafle.emballage.tracking',
        string='Tracking',
        required=True,
        ondelete='restrict'
    )

    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string='Emballage',
        related='tracking_id.emballage_id',
        store=True,
        readonly=True
    )
    consigne_retour_id = fields.Many2one(
        'gecafle.consigne.retour',
        string='Retour Consigne',
        ondelete='cascade'
    )

    type_mouvement = fields.Selection([
        ('sortie_vente', 'Sortie Vente'),
        ('retour_client', 'Retour Client'),
        ('entree_reception', 'Entrée Réception'),
        ('sortie_producteur', 'Sortie Producteur'),
        ('retour_producteur', 'Retour Producteur'),
        ('regularisation', 'Régularisation'),
        ('consigne', 'Retour Consigne'),
    ], string='Type', required=True, tracking=True)

    sens = fields.Selection([
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
    ], string='Sens', compute='_compute_sens', store=True)

    quantite = fields.Integer(
        string='Quantité',
        required=True,
        default=1
    )

    # Références aux documents sources
    vente_id = fields.Many2one(
        'gecafle.vente',
        string='Vente',
        ondelete='cascade'
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string='Réception',
        ondelete='cascade'
    )

    client_id = fields.Many2one(
        'gecafle.client',
        string='Client'
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string='Producteur'
    )

    reference = fields.Char(
        string='Document source',
        compute='_compute_reference',
        store=True
    )

    notes = fields.Text(string='Notes')

    # Champs pour l'annulation
    is_cancelled = fields.Boolean(
        string='Annulé',
        default=False,
        tracking=True
    )

    cancel_reason = fields.Text(string='Motif d\'annulation')

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.emballage.mouvement') or 'EMB/'
        return super().create(vals)

    @api.depends('type_mouvement')
    def _compute_sens(self):
        for record in self:
            if record.type_mouvement in ['sortie_vente', 'sortie_producteur']:
                record.sens = 'sortie'
            elif record.type_mouvement in ['retour_client', 'entree_reception', 'retour_producteur', 'consigne']:
                record.sens = 'entree'
            else:
                record.sens = False

    @api.depends('vente_id', 'reception_id', 'consigne_retour_id')
    def _compute_reference(self):
        for record in self:
            if record.vente_id:
                record.reference = _('Vente %s') % record.vente_id.name
            elif record.reception_id:
                record.reference = _('Réception %s') % record.reception_id.name
            elif record.consigne_retour_id:
                record.reference = _('Retour Consigne %s') % record.consigne_retour_id.name
            else:
                record.reference = False
    @api.constrains('quantite')
    def _check_quantite(self):
        for record in self:
            if record.quantite <= 0:
                raise ValidationError(_("La quantité doit être positive"))

    def action_cancel(self):
        """Annule le mouvement et crée un mouvement inverse"""
        for record in self:
            if record.is_cancelled:
                raise ValidationError(_("Ce mouvement est déjà annulé"))

            # Créer le mouvement inverse
            inverse_vals = {
                'tracking_id': record.tracking_id.id,
                'date': fields.Datetime.now(),
                'quantite': record.quantite,
                'notes': _('Annulation de %s') % record.name,
            }

            # Inverser le type de mouvement
            if record.type_mouvement == 'sortie_vente':
                inverse_vals['type_mouvement'] = 'retour_client'
                inverse_vals['client_id'] = record.client_id.id
            elif record.type_mouvement == 'retour_client':
                inverse_vals['type_mouvement'] = 'sortie_vente'
                inverse_vals['client_id'] = record.client_id.id
            elif record.type_mouvement == 'entree_reception':
                inverse_vals['type_mouvement'] = 'sortie_producteur'
                inverse_vals['producteur_id'] = record.producteur_id.id
            elif record.type_mouvement == 'sortie_producteur':
                inverse_vals['type_mouvement'] = 'entree_reception'
                inverse_vals['producteur_id'] = record.producteur_id.id
            else:
                # Pour la régularisation, inverser le sens
                inverse_vals['type_mouvement'] = 'regularisation'
                if record.sens == 'entree':
                    inverse_vals['sens'] = 'sortie'
                else:
                    inverse_vals['sens'] = 'entree'

            self.create(inverse_vals)
            record.is_cancelled = True
