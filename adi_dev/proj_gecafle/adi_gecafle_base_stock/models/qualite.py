from odoo import models, fields, api, _


class GecafleQualite(models.Model):
    _name = 'gecafle.qualite'
    _description = 'Qualité de Produit'
    

    name = fields.Char(string='Nom de qualité', required=True, translate=True)
    classification = fields.Integer(string='Classification', required=True, 
                                   help='Numéro entier pour le classement')
    
    _sql_constraints = [
        ('name_uniq',
         'UNIQUE(name)',
         _('Le nom de qualité doit être unique!')),

        ('classification_positive',
         'CHECK(classification > 0)',
         "La classification doit être supérieure à 0 !")
    ]