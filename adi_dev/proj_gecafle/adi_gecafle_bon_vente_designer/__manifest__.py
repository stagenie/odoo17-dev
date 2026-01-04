# -*- coding: utf-8 -*-
{
    'name': 'GECAFLE - Designer Bon de Vente',
    'version': '17.0.1.7.0',
    'category': 'Sales',
    'summary': 'Modèles de rapports personnalisables pour Bon de Vente',
    'description': """
        Module de personnalisation des rapports Bon de Vente GECAFLE
        ============================================================

        Fonctionnalités:
        ----------------
        * 3 styles d'en-têtes configurables (Classique, Moderne, Premium)
        * 3 styles de corps de document (Standard, Moderne, Premium)
        * Configuration manuelle des informations d'en-tête
        * Wizard de sélection du modèle à l'impression
        * Designs professionnels et impressionnants

        Développé par ADI Solutions
    """,
    'author': 'ADI Solutions',
    'website': 'https://www.adi-solutions.dz',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'adi_gecafle_ventes',
        'adi_gecafle_base_stock',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/default_styles.xml',
        # Views
        'views/template_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizards/print_wizard_views.xml',
        # Reports
        'reports/external_layout_clean.xml',
        'reports/report_actions.xml',
        'reports/headers/header_classic.xml',
        'reports/headers/header_modern.xml',
        'reports/headers/header_premium.xml',
        'reports/bodies/body_standard.xml',
        'reports/bodies/body_modern.xml',
        'reports/bodies/body_premium.xml',
        'reports/report_bon_vente_designer.xml',
        # Button inherit
        'views/vente_button_inherit.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'adi_gecafle_bon_vente_designer/static/src/css/bon_vente_styles.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
