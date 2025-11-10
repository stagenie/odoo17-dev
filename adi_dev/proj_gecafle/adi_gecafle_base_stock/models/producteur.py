from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleProducteur(models.Model):
    _name = 'gecafle.producteur'
    _description = 'Producteur de Fruits et Légumes'
    
    name = fields.Char(string='Nom et Prénom', required=True, translate=True, index=True)
    phone = fields.Char(string='Téléphone / Mobile')
    address = fields.Text(string='Adresse', translate=True)
    
    initial_balance = fields.Monetary(string='Solde Initial', currency_field='currency_id')
    creation_date = fields.Date(string='Date de création', default=fields.Date.context_today)
    
    use_custom_margin = fields.Boolean(string='Marge personnalisée', default=False)
    fruit_margin = fields.Float(string='Marge Fruits (%)')
    vegetable_margin = fields.Float(string='Marge Légumes (%)')
    
    language = fields.Selection([
        ('fr_FR', 'Français'),
        ('ar_DZ', 'العربية (Arabe)'),
    ], string='Langue', default='fr_FR', required=True)
    
    currency_id = fields.Many2one('res.currency', string='Devise',
                                 default=lambda self: self.env.company.currency_id.id)
    
    product_ids = fields.One2many('gecafle.produit', 'producteur_id', string='Produits')
    product_count = fields.Integer(compute='_compute_product_count', string='Nombre de produits')


    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Le nom du producteur doit être unique!'))
    ]


    
    @api.model
    def create(self, vals):
        """Au moment de création, définir les marges par défaut si nécessaire"""
        if not vals.get('use_custom_margin'):
            company = self.env.company
            vals['fruit_margin'] = company.marge_fruits
            vals['vegetable_margin'] = company.marge_legumes
        return super().create(vals)
    
    @api.onchange('use_custom_margin')
    def _onchange_use_custom_margin(self):
        """Si on désactive les marges personnalisées, reprendre les marges par défaut"""
        if not self.use_custom_margin:
            company = self.env.company
            self.fruit_margin = company.marge_fruits
            self.vegetable_margin = company.marge_legumes
    
    def _compute_product_count(self):
        """Calcule le nombre de produits associés à ce producteur"""
        for producteur in self:
            producteur.product_count = len(producteur.product_ids)