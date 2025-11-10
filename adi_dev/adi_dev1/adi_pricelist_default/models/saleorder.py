from odoo import api,fields,models
class SaleOrder(models.Model):
    _inherit = 'sale.order'


    

    def action_add_from_catalog(self):
        # Appel de la méthode originale pour ajouter les produits depuis le catalogue
        res = super(SaleOrder, self).action_add_from_catalog()

        # Mise à jour des prix en fonction du type de prix après ajout des produits
        for line in self.order_line:
            if line.product_id:
                if self.type_prix == 'public':
                    line.price_unit = line.product_id.list_price
                elif self.type_prix == 'revendeur':
                    line.price_unit = line.product_id.prix_revendeur
                elif self.type_prix == 'grossiste':
                    line.price_unit = line.product_id.prix_grossiste

        return res
    """
    @api.onchange('order_line')
    def _onchange_order_line_catalog(self):
        for line in self.order_line:
            if line.product_id:
                if self.type_prix == 'public':
                    line.price_unit = line.product_id.list_price
                elif self.type_prix == 'revendeur':
                    line.price_unit = line.product_id.prix_revendeur
                elif self.type_prix == 'grossiste':
                    line.price_unit = line.product_id.prix_grossiste

    """
    

   
    
    """
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'type_prix' in vals or 'order_line' in vals:
            for order in self:
                for line in order.order_line:
                    if line.product_id:
                        if order.type_prix == 'public':
                            line.price_unit = line.product_id.list_price
                        elif order.type_prix == 'revendeur':
                            line.price_unit = line.product_id.prix_revendeur
                        elif order.type_prix == 'grossiste':
                            line.price_unit = line.product_id.prix_grossiste
        return res
    

    """
    
    type_prix = fields.Selection([
        ('public', 'Prix de Vente Public'),
        ('revendeur', 'Prix revendeur'),
        ('grossiste', 'Prix grossiste')
    ], string="Type de prix", default='public')
    
     
    @api.onchange('type_prix')
    def _onchange_type_prix_order(self):
        for order in self:
            for line in order.order_line:
                if order.type_prix == 'public':
                    line.price_unit = line.product_id.list_price
                elif order.type_prix == 'revendeur':
                    line.price_unit = line.product_id.prix_revendeur
                elif order.type_prix == 'grossiste':
                    line.price_unit = line.product_id.prix_grossiste
        
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    
    @api.onchange('product_id', 'order_id.type_prix')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                if line.order_id.type_prix == 'public':
                    line.price_unit = line.product_id.list_price
                elif line.order_id.type_prix == 'revendeur':
                    line.price_unit = line.product_id.prix_revendeur
                elif line.order_id.type_prix == 'grossiste':
                    line.price_unit = line.product_id.prix_grossiste