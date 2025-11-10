from odoo import models, fields

class DepensesDepense(models.Model):
    _name = 'depenses.depense'
    _description = 'Gestion des Dépenses'
    _order = 'date desc'
    _rec_name = 'categorie'


    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    montant = fields.Float(string="Montant", required=True)
    categorie = fields.Many2one('depenses.categorie',
                                string="Catégorie", required=True)
    region = fields.Many2one('res.country.state', string="Région",
                             default=lambda self: self.env.user.region_id)
    description = fields.Text(string="Description")
    user_id = fields.Many2one('res.users', string="Utilisateur",
                              default=lambda self: self.env.user)


class DepensesCategorie(models.Model):
    _name = 'depenses.categorie'
    _description = 'Catégorie de Dépenses'

    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")

