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

    # ================== PRODUITS FINIS - SOLO/CLASSICO ==================
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

    solo_units_per_carton = fields.Integer(
        string='Unités SOLO par Carton',
        default=192,
        help="48 packs × 4 unités = 192 unités"
    )

    classico_units_per_carton = fields.Integer(
        string='Unités CLASSICO par Carton',
        default=312,
        help="24 packs × 13 unités = 312 unités"
    )

    # Ratio de coût
    cost_ratio_solo_classico = fields.Float(
        string='Ratio Coût SOLO/CLASSICO',
        default=1.65,
        help="SOLO = Ratio × CLASSICO (par défaut 1.65)"
    )

    # ================== PRODUITS FINIS - SANDWICH GRAND FORMAT ==================
    product_sandwich_id = fields.Many2one(
        'product.product',
        string='Produit Sandwich Grand Format',
        domain="[('type', '=', 'product')]",
        help="Produit fini Sandwich Grand Format (produit seul, sans ratio)"
    )

    sandwich_weight_per_carton = fields.Float(
        string='Poids Sandwich par Carton (kg)',
        default=0.0,
        help="Poids net d'un carton Sandwich Grand Format en kilogrammes"
    )

    sandwich_units_per_carton = fields.Integer(
        string='Unités Sandwich par Carton',
        default=0,
        help="Nombre d'unités par carton Sandwich Grand Format"
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

    # ================== PÂTE RÉCUPÉRABLE ==================
    product_paste_id = fields.Many2one(
        'product.product',
        string='Produit Pâte Récupérable',
        domain="[('type', '=', 'product')]",
        help="Produit pâte récupérable (valorisation AVCO, réutilisable le lendemain)"
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

    # ================== VALIDATION AUTOMATIQUE ==================
    auto_validate_operations = fields.Boolean(
        string='Valider Opérations Automatiquement',
        default=False,
        help="Valider automatiquement les BL et Achats lors de la validation de la production"
    )

    auto_create_supplier_invoice = fields.Boolean(
        string='Créer Facture Fournisseur Auto',
        default=False,
        help="Créer automatiquement les factures fournisseur pour les achats validés"
    )

    # ================== EMBALLAGES SOLO/CLASSICO ==================
    product_emballage_solo_id = fields.Many2one(
        'product.product',
        string='Emballage SOLO',
        domain="[('type', '=', 'product')]",
        help="Produit emballage (carton) pour SOLO"
    )

    product_emballage_classico_id = fields.Many2one(
        'product.product',
        string='Emballage CLASSICO',
        domain="[('type', '=', 'product')]",
        help="Produit emballage (carton) pour CLASSICO"
    )

    product_film_solo_id = fields.Many2one(
        'product.product',
        string='Film SOLO',
        domain="[('type', '=', 'product')]",
        help="Produit film plastique pour SOLO"
    )

    product_film_classico_id = fields.Many2one(
        'product.product',
        string='Film CLASSICO',
        domain="[('type', '=', 'product')]",
        help="Produit film plastique pour CLASSICO"
    )

    # ================== EMBALLAGES SANDWICH GF ==================
    product_emballage_sandwich_id = fields.Many2one(
        'product.product',
        string='Emballage Sandwich GF',
        domain="[('type', '=', 'product')]",
        help="Produit emballage (carton) pour Sandwich Grand Format"
    )

    product_film_sandwich_id = fields.Many2one(
        'product.product',
        string='Film Sandwich GF',
        domain="[('type', '=', 'product')]",
        help="Produit film plastique pour Sandwich Grand Format"
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
