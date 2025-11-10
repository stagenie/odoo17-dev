from odoo import models, fields, api, _


class GecafleRegion(models.Model):
    _name = 'gecafle.region'
    _description = 'Région'

    name = fields.Char(string="Nom de la Région", Translate=True, required=True)
    code = fields.Char(string="Code de la Région", required=True)
    #description = fields.Text(string="Description de la Région")

class GecafleClient(models.Model):
    _name = 'gecafle.client'
    _description = 'Client'

    _sql_constraints = [
        ('unique_client_name', 'unique(name)', _("Le nom du client doit être unique !"))
    ]

    name = fields.Char(string="Nom du Client", Translate=True, required=True)
    tel_mob = fields.Char(string="Téléphone / Mobile")
    adresse = fields.Text(string="Adresse")
    est_fidel = fields.Boolean(
        string="Client fidèle",
        default=False,
        help=_("Si vrai, le client peut prendre les marchandises sans payer la consigne des emballages.")
    )
    date_creation = fields.Datetime(string="Date de Création", default=fields.Datetime.now)
    solde_initiale = fields.Monetary(string="Solde Initial", currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id.id
    )
    region_id = fields.Many2one('gecafle.region', string="Région")
    observation = fields.Text(string="Observation")
    langue_client = fields.Selection([
        ('fr', 'Français'),
        ('ar', 'Arabe'),
    ], string="Langue du Client", default='fr')
