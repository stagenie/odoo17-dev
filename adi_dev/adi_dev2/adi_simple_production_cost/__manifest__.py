# -*- coding: utf-8 -*-
{
    'name': 'ADI - Coût de Production Simplifié',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Calcul du prix de revient journalier sans module MRP',
    'description': """
ADI - Coût de Production Simplifié
==================================

Module de gestion de production simplifié pour le calcul du prix de revient
sans utiliser le module MRP (Manufacturing).

Fonctionnalités:
----------------
* Saisie des consommations journalières de matières premières
* Gestion des rebuts (vendables et non vendables)
* Gestion de la pâte récupérable/irrécupérable
* Gestion des coûts d'emballage (cartons, plastification, etc.)
* Calcul automatique du coût/kg
* Calcul du coût unitaire par produit avec ratio configurable
* Génération automatique des achats vers le fournisseur "Production"
* Rapports de suivi quotidien

Architecture:
-------------
* DMP (Dépôt Matière Première): Achats avec méthode AVCO
* DPR (Dépôt Production): Simulation consommation via BL
* DPF (Dépôt Produits Finis): Réception produits finis via achat

Cas d'usage:
------------
Production de biscuits avec deux variantes:
* SOLO: Carton = 48 packs × 4 unités = 192 unités
* CLASSICO: Carton = 24 packs × 13 unités = 312 unités
* Ratio configurable: Coût SOLO = 1.65 × Coût CLASSICO (par défaut)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'base',
        'stock',
        'purchase',
        'sale',
        'account',
        'product',
        'uom',
        'mail',
    ],
    'data': [
        # 1. Sécurité
        'security/security.xml',
        'security/ir.model.access.csv',

        # 2. Data (séquences)
        'data/sequence_data.xml',

        # 3. Vues
        'views/product_views.xml',
        'views/ron_bom_views.xml',
        'views/ron_daily_production_views.xml',
        'views/ron_config_views.xml',
        'views/menu_views.xml',

        # 4. Wizard
        'wizard/generate_purchase_wizard.xml',

        # 5. Rapports
        'reports/daily_production_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
