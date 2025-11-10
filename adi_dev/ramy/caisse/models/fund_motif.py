# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class FundMotif(models.Model):
    _name = 'fund.motif'
    _description = 'Motif d\'alimentation de la caisse'
    _order = "create_date desc"

    name = fields.Char(string='Nom motif', required=True)
    type = fields.Selection([
        ('in', 'Recette'),
        ('out', 'Dépense'),
    ], default='in', string="Sens" )
    
    account_analytic_account_id = fields.Many2one(string='Compte analytique', comodel_name='account.analytic.account',)
    fund_motif_family_id = fields.Many2one(
        string='Famille motif',
        comodel_name='fund.motif.family',
    )
    generated = fields.Boolean("Unquement généré", default=False)
    default_data = fields.Boolean("Enregistrement par défaut", default=False, )
    avnc = fields.Boolean("Est avance", default=False, readonly=True)
    payment = fields.Boolean("Est paiement", default=False, readonly=True)

    def unlink(self):
        for motif in self:
            # ampêcher la suppression des lignes créées a partir des avances 
            if motif.default_data:
                raise ValidationError(('Désolé, vous ne pouvez pas supprimer les enregistrements créés par défaut.'))
        return super(FundMotif,self).unlink()
    

