from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GecafleEmballageProducteur(models.Model):
    _name = 'gecafle.emballage.producteur'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Ajoutez cet héritage
    _description = 'Opérations d’emballage Producteur'

    name = fields.Char(
        string='Numéro d’Emballage Producteur',
        required=True,
        default='00000001'
    )
    date_heure_operation = fields.Datetime(
        string="Date/Heure Opération",
        default=fields.Datetime.now,
        required=True
    )
    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        required=True,
        ondelete='restrict'
    )
    observation = fields.Text(string="Observation")
    prod_emb_operations_ids = fields.One2many(
        'gecafle.emballage.producteur.details_operations',
        'emballage_producteur_id',
        string="Détails des Opérations d'Emballage"
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception source",
        readonly=True,
        ondelete='set null'
    )

    @api.model
    def create(self, vals):
        if not vals.get('num_seq_emballage_producteur') or vals.get('num_seq_emballage_producteur') == '00000001':
            company = self.env.company
            # Utilisation d'une fonction de compteur similaire à celle de réception
            new_seq = company.sudo().increment_counter('emballage_producteur_counter')
            vals['name'] = new_seq
        return super(GecafleEmballageProducteur, self).create(vals)



class GecafleEmballageProducteurDetailsOperations(models.Model):
    _name = 'gecafle.emballage.producteur.details_operations'
    _description = 'Détails des Opérations d’Emballage du Producteur'

    emballage_producteur_id = fields.Many2one(
        'gecafle.emballage.producteur',
        string="Opération Emballage Producteur",
        required=True,
        ondelete='cascade'
    )
    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Type de Colis",
        required=True,
        ondelete='restrict'
    )
    quantite_entrante = fields.Integer(
        string="Quantité Entrante",
        required=True
    )
    quantite_sortante = fields.Integer(
        string="Quantité Sortante",
        required=True
    )
    remarque = fields.Text(string="Remarque")


    @api.constrains('quantite_entrante', 'quantite_sortante')
    def _check_quantite_non_nulle(self):
        for rec in self:
            if rec.quantite_entrante == 0 and rec.quantite_sortante == 0:
                raise ValidationError("La quantité entrante et la quantité sortante ne peuvent être toutes deux égales à 0.")
