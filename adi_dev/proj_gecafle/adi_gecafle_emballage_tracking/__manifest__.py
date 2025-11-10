# -*- coding: utf-8 -*-
{
    'name': 'GECAFLE - Tracking Emballages',
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Inventory/Logistics',
    'summary': 'Gestion et tracking des emballages (clients et producteurs)',
    'description': """
        Module de tracking des emballages pour GECAFLE
        ================================================

        Fonctionnalités principales :
        - Suivi des mouvements d'emballages (entrées/sorties)
        - Gestion des balances par client et producteur
        - Rapports détaillés et récapitulatifs
        - Tableau de bord avec indicateurs clés
        - Intégration avec les modules ventes et réceptions
    """,
    'depends': [
        'adi_gecafle_base_stock',
        'adi_gecafle_ventes',
        'adi_gecafle_receptions',
        'adi_gecafle_consigne_management',
    ],
    'data': [
        # Sécurité
        'security/security.xml',
        'security/ir.model.access.csv',

        # Données
        'data/sequence.xml',

        # Vues
        'views/emballage_tracking_views.xml',
        'views/emballage_mouvement_views.xml',
        'views/emballage_balance_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_menu_inherit.xml',



        # Wizards
        'wizard/emballage_report_wizard_views.xml',
        'wizard/emballage_regularisation_wizard_views.xml',

        # Rapports
        'reports/report_actions.xml',
        'reports/report_emballage_client.xml',
        'reports/report_emballage_producteur.xml',
        'reports/report_emballage_global.xml',
        'reports/report_emballage_detail.xml',

        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
