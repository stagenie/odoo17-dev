# -*- coding: utf-8 -*-
{
    'name': 'ADI Production Warehouse Transfer',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Inventory',
    'summary': 'Gestion automatique des transferts entre entrepôts pour la production',
    'description': """
        Gestion Avancée des Transferts Inter-Entrepôts
        ==============================================

        Ce module facilite les transferts entre :
        - Magasin Matières Premières → Magasin Production
        - Magasin Production → Magasin Produits Finis

        Fonctionnalités :
        - Génération automatique des bons de transfert depuis la nomenclature
        - Calcul intelligent des quantités manquantes
        - Workflow de validation
        - Intégration avec les achats si stock insuffisant
        - Tableau de bord des transferts avec KPIs
        - Graphiques interactifs
        - Alertes proactives
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'LGPL-3',
    'depends': ['mrp', 'stock', 'purchase'],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',

        # Données
        'data/stock_data.xml',

        # Vues
        'views/res_company_views.xml',
        'views/stock_warehouse_views.xml',
        'views/mrp_bom_views.xml',
        'views/stock_picking_views.xml',
        'views/production_dashboard.xml',
        'views/mrp_production_views.xml',

        # Wizards
        'wizard/mrp_bom_transfer_wizard_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
