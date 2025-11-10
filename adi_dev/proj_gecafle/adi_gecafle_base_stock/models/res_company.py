from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    carreau_number = fields.Char(string='N° de Carreau', translate=True)
    marge_fruits = fields.Float(string='Marge Fruits (%)',  default=8.0)
    marge_legumes = fields.Float(string='Marge Légumes (%)',  default=5.0)
    
    # Compteurs à 8 chiffres
    reception_counter = fields.Char(string='N° de réception en cours', default='00000001',)
    vente_counter = fields.Char(string='N° de souche (Vente) en cours', default='00000001',)
    reglement_client_counter = fields.Char(string='Num de Règlement Client', default='00000001',)
    reglement_producteur_counter = fields.Char(string='Num de Règlement Producteur', default='00000001',)
    versement_producteur_counter = fields.Char(string='Num de Versement Producteur', default='00000001',)
    emballage_producteur_counter = fields.Char(string='Num de Emballage Producteur', default='00000001',)
    emballage_client_counter = fields.Char(string='Num de Emballage Client', default='00000001',)
    versement_client_counter = fields.Char(string='Num de Versement Client', default='00000001',)
    conditions_ventes=fields.Text(string='Conditions de ventes', translate=True)
    
    def increment_counter(self, counter_field):
        """Incrémente un compteur spécifique à 8 chiffres"""
        current_value = int(getattr(self, counter_field))
        new_value = current_value + 1
        setattr(self, counter_field, f"{new_value:08d}")
        return getattr(self, counter_field)