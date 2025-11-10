from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Référence à la ligne de vente source
    gecafle_detail_vente_id = fields.Many2one(
        'gecafle.details_ventes',
        string="Ligne de vente source",
        readonly=True
    )

    # Champs copiés depuis gecafle.details_ventes - Mêmes noms exactement
    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur"
    )

    gecafle_produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit GECAFLE"
    )

    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )

    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type d'emballage"
    )

    nombre_colis = fields.Integer(
        string="Nb Colis",
        default=0
    )

    poids_brut = fields.Float(
        string="Poids brut",
        digits=(16, 2)
    )

    poids_colis = fields.Float(
        string="Poids colis",
        digits=(16, 2)
    )

    poids_net = fields.Float(
        string="Poids net",
        digits=(16, 2)
    )

    prix_unitaire = fields.Float(
        string="Prix unitaire",
        digits=(16, 2)
    )

    montant_net = fields.Monetary(
        string="Montant Net",
        currency_field='currency_id'
    )

    taux_commission = fields.Float(
        string="% Commission",
        digits=(5, 2),
        groups="adi_gecafle_ventes.group_gecafle_direction"
    )

    montant_commission = fields.Monetary(
        string="Montant Commission",
        currency_field='currency_id',
        groups="adi_gecafle_ventes.group_gecafle_direction"
    )

    # Type de ligne pour distinguer
    gecafle_line_type = fields.Selection([
        ('produit', 'Produit'),
        ('emballage', 'Emballage'),
        ('remise', 'Remise')
    ], string="Type de ligne", default='produit')
