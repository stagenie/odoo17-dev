from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GecafleEmballageClient(models.Model):
    _name = 'gecafle.emballage.client'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Ajoutez cet héritage
    _description = 'Opérations d’emballage '

    name = fields.Char(
        string='Numéro d’Emballage Client',
        required=True,
        default='00000001'
    )
    date_heure_operation = fields.Datetime(
        string="Date/Heure Opération",
        default=fields.Datetime.now,
        required=True
    )
    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente source",
        readonly=True,
        ondelete='set null'
    )
    client_id = fields.Many2one(
        'gecafle.client',
        string="Client",
        required=True,
        ondelete='restrict'
    )
    observation = fields.Text(string="Observation")
    client_emb_operations_ids = fields.One2many(
        'gecafle.emballage.client.details_operations',
        'emballage_client_id',
        string="Détails des Opérations d'Emballage"
    )

    @api.model
    def create(self, vals):
        if not vals.get('num_seq_emballage_client') or vals.get('num_seq_emballage_client') == '00000001':
            company = self.env.company
            # Utilisation d'une fonction de compteur similaire à celle de réception
            new_seq = company.sudo().increment_counter('emballage_client_counter')
            vals['name'] = new_seq
        return super(GecafleEmballageClient, self).create(vals)



class GecafleEmballageClientDetailsOperations(models.Model):
    _name = 'gecafle.emballage.client.details_operations'
    _description = 'Détails des Opérations d’Emballage du client'

    emballage_client_id = fields.Many2one(
        'gecafle.emballage.client',
        string="Opération Emballage Client",
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
