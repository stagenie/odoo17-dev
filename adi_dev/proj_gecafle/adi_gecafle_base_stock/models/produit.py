from odoo import models, fields, api, _

class GecafleFruitsLegumes(models.Model):
    _name = 'gecafle.fruits_legumes'
    _description = 'Liste des fruits et légumes'

    name = fields.Char(string="Nom",Translate=True, required=True)
    #type = fields.Char(string="Type", Translate=True, required=True)
    image = fields.Binary(string='Image du produit', attachment=True)
    type = fields.Selection([
        ('fruit', 'Fruit'),
        ('legume', 'Légume')
    ], string='Type',Translate=True, required=True, default='fruit')
    description = fields.Text(string="Description", translate=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Le nom du Fruit/Légume doit être unique!'))
    ]


class GecafleProduit(models.Model):
    _name = 'gecafle.produit'
    _description = 'Produit (Fruit ou Légume)'

    # Le champ qui permet de sélectionner le fruit ou légume
    fruit_legume_id = fields.Many2one(
        'gecafle.fruits_legumes',
        string="Fruit / Légume",
        required=True,
        ondelete='restrict'
    )

    # Le nom du produit est récupéré depuis le modèle gecafle.fruits_legumes
    name = fields.Char(
        string="Nom du Produit",
        related="fruit_legume_id.name",
        store=True,
        translate=True,
        readonly=True,
    )
    #name = fields.Char(string='Nom du produit', required=True, translate=True, index=True)
    # Le type du produit est aussi tiré du modèle
    type = fields.Selection(
        string="Type",
        related="fruit_legume_id.type",
        store=True,
        readonly=True
    )


    producteur_id = fields.Many2one('gecafle.producteur', string='Producteur', required=True, 
                                   ondelete='restrict', index=True)

    _sql_constraints = [
        ('unique_product_per_producteur', 'UNIQUE(producteur_id, fruit_legume_id)',
         _("Ce produit est déjà affecté à ce producteur."))
    ]

    
    image = fields.Binary(string='Image du produit', attachment=True,
        related = "fruit_legume_id.image",
        store = True,
        readonly = True,)
    
    active = fields.Boolean(default=True)
    # je vais enlever la contrainte unique sur le nom du produit car elle est trop restrictive
    """
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Le nom du produit doit être unique!'))
    ] 
    """

    
    @api.model
    def get_margin(self):
        """Récupère la marge applicable selon le type et le producteur"""
        producteur = self.producteur_id
        if producteur.use_custom_margin:
            if self.type == 'fruit':
                return producteur.fruit_margin
            else:
                return producteur.vegetable_margin
        else:
            company = self.env.company
            if self.type == 'fruit':
                return company.marge_fruits
            else:
                return company.marge_legumes

