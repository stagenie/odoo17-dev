# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonProductionConfig(models.Model):
    """
    Configuration globale pour la production RON.
    Un seul enregistrement par société.
    """
    _name = 'ron.production.config'
    _description = 'Configuration Production RON'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade'
    )

    # ================== PRODUITS FINIS ==================
    product_solo_id = fields.Many2one(
        'product.product',
        string='Produit SOLO',
        domain="[('type', '=', 'product')]",
        help="Produit fini SOLO (Carton = 48 packs × 4 unités = 192 unités)"
    )

    product_classico_id = fields.Many2one(
        'product.product',
        string='Produit CLASSICO',
        domain="[('type', '=', 'product')]",
        help="Produit fini CLASSICO (Carton = 24 packs × 13 unités = 312 unités)"
    )

    # Poids par carton (pour calcul)
    solo_weight_per_carton = fields.Float(
        string='Poids SOLO par Carton (kg)',
        default=0.0,
        help="Poids net d'un carton SOLO en kilogrammes"
    )

    classico_weight_per_carton = fields.Float(
        string='Poids CLASSICO par Carton (kg)',
        default=0.0,
        help="Poids net d'un carton CLASSICO en kilogrammes"
    )

    # Ratio de coût
    cost_ratio_solo_classico = fields.Float(
        string='Ratio Coût SOLO/CLASSICO',
        default=1.65,
        help="SOLO = Ratio × CLASSICO (par défaut 1.65)"
    )

    # ================== DÉPÔTS ==================
    warehouse_mp_id = fields.Many2one(
        'stock.warehouse',
        string='Dépôt Matière Première (DMP)',
        help="Dépôt pour les achats de matières premières"
    )

    warehouse_production_id = fields.Many2one(
        'stock.warehouse',
        string='Dépôt Production (DPR)',
        help="Dépôt de production pour la simulation"
    )

    warehouse_pf_id = fields.Many2one(
        'stock.warehouse',
        string='Dépôt Produits Finis (DPF)',
        help="Dépôt pour les produits finis"
    )

    location_production_id = fields.Many2one(
        'stock.location',
        string='Emplacement Production',
        domain="[('usage', '=', 'internal')]",
        help="Emplacement de production interne"
    )

    # ================== PARTENAIRES ==================
    partner_consumption_id = fields.Many2one(
        'res.partner',
        string='Contact Consommation',
        help="Contact fictif pour les BL de consommation"
    )

    partner_production_id = fields.Many2one(
        'res.partner',
        string='Fournisseur Production',
        help="Fournisseur fictif pour les achats de produits finis"
    )

    # ================== PRODUITS REBUTS ==================
    product_scrap_sellable_id = fields.Many2one(
        'product.product',
        string='Produit Rebut Vendable',
        domain="[('type', '=', 'product')]",
        help="Produit rebut qui peut être vendu"
    )

    product_scrap_unsellable_id = fields.Many2one(
        'product.product',
        string='Produit Rebut Non Vendable',
        domain="[('type', '=', 'product')]",
        help="Produit rebut qui ne peut pas être vendu"
    )

    product_paste_recoverable_id = fields.Many2one(
        'product.product',
        string='Pâte Récupérable',
        domain="[('type', '=', 'product')]",
        help="Produit pâte récupérable (peut être réutilisée)"
    )

    product_paste_unrecoverable_id = fields.Many2one(
        'product.product',
        string='Pâte Irrécupérable',
        domain="[('type', '=', 'product')]",
        help="Produit pâte irrécupérable (perte)"
    )

    # ================== PARAMÈTRES ==================
    auto_create_delivery = fields.Boolean(
        string='Créer BL Consommation Auto',
        default=True,
        help="Créer automatiquement le BL de consommation à la validation"
    )

    auto_create_purchase = fields.Boolean(
        string='Créer Achat Prod. Finis Auto',
        default=True,
        help="Créer automatiquement l'achat des produits finis à la validation"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='company_id.currency_id',
        readonly=True
    )

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)',
         'Une seule configuration par société est autorisée!')
    ]

    @api.model
    def get_config(self, company_id=None):
        """Récupère la configuration pour la société courante ou spécifiée."""
        if not company_id:
            company_id = self.env.company.id

        config = self.search([('company_id', '=', company_id)], limit=1)
        if not config:
            config = self.create({'company_id': company_id})
        return config

    def action_open_config(self):
        """Ouvre le formulaire de configuration."""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configuration Production RON',
            'res_model': 'ron.production.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
        }
