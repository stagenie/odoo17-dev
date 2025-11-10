# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GecafleEmballageRegularisationWizard(models.TransientModel):
    _name = 'gecafle.emballage.regularisation.wizard'
    _description = 'Assistant de régularisation des emballages'

    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Emballage",
        required=True
    )

    type_regularisation = fields.Selection([
        ('ajustement_stock', 'Ajustement de stock'),
        ('correction_erreur', "Correction d'erreur"),
        ('perte', 'Perte/Casse'),
        ('inventaire', 'Inventaire physique'),
        ('initialisation', 'Initialisation'),
    ], string="Type", required=True, default='ajustement_stock')

    quantite = fields.Integer(
        string="Quantité",
        required=True,
        help="Positif pour ajouter, négatif pour retirer"
    )

    motif = fields.Text(
        string="Motif",
        required=True
    )

    date_regularisation = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True
    )

    # Information sur le stock actuel
    stock_actuel = fields.Integer(
        string="Stock actuel",
        compute='_compute_stock_info',
        readonly=True
    )

    stock_apres = fields.Integer(
        string="Stock après régularisation",
        compute='_compute_stock_info',
        readonly=True
    )

    tracking_id = fields.Many2one(
        'gecafle.emballage.tracking',
        string="Tracking",
        compute='_compute_tracking_id'
    )

    @api.depends('emballage_id')
    def _compute_tracking_id(self):
        for record in self:
            if record.emballage_id:
                tracking = self.env['gecafle.emballage.tracking'].search([
                    ('emballage_id', '=', record.emballage_id.id)
                ], limit=1)
                record.tracking_id = tracking.id if tracking else False
            else:
                record.tracking_id = False

    @api.depends('emballage_id', 'quantite', 'tracking_id')
    def _compute_stock_info(self):
        for record in self:
            if record.tracking_id:
                record.stock_actuel = record.tracking_id.stock_disponible
                record.stock_apres = record.tracking_id.stock_disponible + record.quantite
            else:
                record.stock_actuel = 0
                record.stock_apres = record.quantite

    @api.constrains('quantite')
    def _check_quantite(self):
        for record in self:
            if record.quantite == 0:
                raise ValidationError(_("La quantité ne peut pas être zéro"))

    def action_regulariser(self):
        """Crée un mouvement de régularisation"""
        self.ensure_one()

        # Obtenir ou créer le tracking
        if not self.tracking_id:
            tracking = self.env['gecafle.emballage.tracking'].create({
                'emballage_id': self.emballage_id.id,
                'is_tracked': True
            })
        else:
            tracking = self.tracking_id

        # Créer le mouvement de régularisation
        self.env['gecafle.emballage.mouvement'].create({
            'tracking_id': tracking.id,
            'date': self.date_regularisation,
            'type_mouvement': 'regularisation',
            'quantite': abs(self.quantite),
            'notes': _("Type: %s\nMotif: %s") % (
                dict(self._fields['type_regularisation'].selection).get(self.type_regularisation),
                self.motif
            ),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Régularisation effectuée'),
                'message': _('Stock ajusté de %s pour %s') % (self.quantite, self.emballage_id.name),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
