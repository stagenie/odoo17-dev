from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    prix_revendeur = fields.Monetary(string="Prix revendeur")
    pourcentage_revendeur = fields.Float(string="Marge Prix revendeur (%)")
    prix_grossiste = fields.Monetary(string="Prix grossiste")
    pourcentage_grossiste = fields.Float(string="Marge Prix grossiste (%)")
    pourcentage_public = fields.Float(string="Marge Prix de Vente Public (%)")
    
    standard_price = fields.Float(string="Coût")
    list_price = fields.Float(string="Prix de Vente Public")
    
    """
    @api.onchange('standard_price', 'pourcentage_revendeur', 'pourcentage_grossiste', 'pourcentage_public')
    def _compute_prices(self):
        for product in self:
            product.prix_revendeur = product.standard_price * (1 + product.pourcentage_revendeur / 100)
            product.prix_grossiste = product.standard_price * (1 + product.pourcentage_grossiste / 100)
            product.list_price = product.standard_price * (1 + product.pourcentage_public / 100)

    """

    
    # Onchange pour Marge Public
    @api.onchange('pourcentage_public')
    def _onchange_pourcentage_public(self):
        for product in self:
            if product.standard_price:
                product.list_price = product.standard_price * (1 + product.pourcentage_public / 100)

    # Onchange pour Prix Public
    @api.onchange('list_price')
    def _onchange_list_price(self):
        for product in self:
            if product.standard_price:
                product.pourcentage_public = ((product.list_price - product.standard_price) / product.standard_price) * 100

    # Onchange pour Marge Revendeur
    @api.onchange('pourcentage_revendeur')
    def _onchange_pourcentage_revendeur(self):
        for product in self:
            if product.standard_price:
                product.prix_revendeur = product.standard_price * (1 + product.pourcentage_revendeur / 100)

    # Onchange pour Prix Revendeur
    @api.onchange('prix_revendeur')
    def _onchange_prix_revendeur(self):
        for product in self:
            if product.standard_price:
                product.pourcentage_revendeur = ((product.prix_revendeur - product.standard_price) / product.standard_price) * 100

    # Onchange pour Marge Grossiste
    @api.onchange('pourcentage_grossiste')
    def _onchange_pourcentage_grossiste(self):
        for product in self:
            if product.standard_price:
                product.prix_grossiste = product.standard_price * (1 + product.pourcentage_grossiste / 100)

    # Onchange pour Prix Grossiste
    @api.onchange('prix_grossiste')
    def _onchange_prix_grossiste(self):
        for product in self:
            if product.standard_price:
                product.pourcentage_grossiste = ((product.prix_grossiste - product.standard_price) / product.standard_price) * 100
