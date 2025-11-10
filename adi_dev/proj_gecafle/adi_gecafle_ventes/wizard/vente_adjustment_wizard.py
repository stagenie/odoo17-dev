from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VenteAdjustmentWizard(models.TransientModel):
    _name = 'gecafle.vente.adjustment.wizard'
    _description = 'Assistant de création d\'ajustement'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True,
        readonly=True
    )

    adjustment_type = fields.Selection([
        ('return', 'Retour partiel'),
        ('loss', 'Perte/Casse'),
        ('price', 'Ajustement de prix'),
        ('quality', 'Problème de qualité'),
        ('weight', 'Erreur de pesée'),
        ('mixed', 'Ajustement mixte')
    ], string="Type d'ajustement", required=True, default='mixed')

    reason = fields.Text(
        string="Motif",
        required=True,
        help="Expliquez la raison de cet ajustement"
    )

    def action_create_adjustment(self):
        """Crée l'ajustement avec les informations de base"""
        self.ensure_one()

        # Créer l'ajustement
        adjustment = self.env['gecafle.vente.adjustment'].create({
            'vente_id': self.vente_id.id,
            'adjustment_type': self.adjustment_type,
            'reason': self.reason,
        })

        # Ouvrir l'ajustement créé
        return {
            'name': _('Ajustement de vente'),
            'type': 'ir.actions.act_window',
            'res_model': 'gecafle.vente.adjustment',
            'res_id': adjustment.id,
            'view_mode': 'form',
            'target': 'current',
        }
