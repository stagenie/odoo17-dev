from odoo import models, fields, api, _


class GecafleEmballage(models.Model):
    _name = 'gecafle.emballage'
    _description = 'Emballage'
    

    name = fields.Char(string='Nom de l\'emballage', required=True, index=True, translate=True)
    weight = fields.Float(string='Poids en Kilos', digits='Stock Weight')
    price_unit = fields.Float(string='Prix Unitaire', digits='Product Price')
    non_returnable = fields.Boolean(string='Non rendu', default=True)
    
    quantity_initial = fields.Integer(string='Quantité initiale', default=0)
    creation_date = fields.Date(string='Date création', default=fields.Date.context_today)
    
    quantity_available = fields.Integer(string='Quantité disponible', compute='_compute_quantity_available', 
                                       store=True, help='Quantité calculée en fonction des mouvements')
    
    _sql_constraints = [
        ('nom_uniq', 'UNIQUE(name)', _('Le nom de l\'emballage doit être unique!'))
    ]
    
     
    def _compute_quantity_available(self):
        """Calcule la quantité disponible en fonction des mouvements
        Pour l'instant, c'est juste la quantité initiale"""
        for emballage in self:
            emballage.quantity_available = emballage.quantity_initial