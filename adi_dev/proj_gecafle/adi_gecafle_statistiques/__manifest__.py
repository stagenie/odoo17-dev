# -*- coding: utf-8 -*-
{
    'name': 'ADI GECAFLE - Statistiques et Analyses',
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Sales/Statistics',
    'summary': 'Module de statistiques avancées et relevés pour GECAFLE',
    'description': """
        Module de statistiques et analyses pour GECAFLE:
        - Statistiques par produit, producteur, période
        - Graphiques dynamiques (barres, camembert, courbes)
        - Relevé détaillé Réceptions et leurs Ventes
        - Tableaux de bord interactifs
        - Export Excel et PDF
    """,
    'depends': [
        'adi_gecafle_vente_invoices',
        'adi_gecafle_receptions',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/sequence_tracabilite.xml',
        'views/statistiques_ventes_views.xml',
        'views/releve_reception_ventes_views.xml',
        'views/dashboard_views.xml',
        # pour liste des ventes
        'views/listes_ventes_views.xml',

        'reports/report_liste_ventes.xml',
        'reports/report_tracabilite.xml',
        'views/tracabilite_views.xml',
        'views/menus.xml',

        'reports/report_releve_reception_ventes.xml',
        'reports/report_releve_reception_ventes_pages.xml',
        'reports/report_statistiques.xml',
        'wizard/wizard_statistiques_views.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'adi_gecafle_statistiques/static/src/css/tracabilite.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
