from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GecafleDetailsEmballageVente(models.Model):
    _name = 'gecafle.details_emballage_vente'
    _description = 'Détails des Emballages de Vente'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True,
        ondelete='cascade'
    )
    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Emballage",
        required=True
    )
    qte_sortantes = fields.Integer(
        string="Quantité Sortante",
        default=0
    )
    qte_entrantes = fields.Integer(
        string="Quantité Entrante",
        default=0
    )

    @api.constrains('qte_sortantes', 'qte_entrantes')
    def _check_quantities(self):
        """Vérification que les quantités ne sont pas à la fois égales à 0"""
        for record in self:
            if record.qte_sortantes == 0 and record.qte_entrantes == 0:
                raise ValidationError(_(
                    "Les quantités entrantes et sortantes ne peuvent pas être à la fois égales à 0."
                ))
