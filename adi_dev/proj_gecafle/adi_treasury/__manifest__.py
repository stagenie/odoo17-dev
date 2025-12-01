# -*- coding: utf-8 -*-
{
    'name': 'Gestion de Trésorerie Avancée',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Gestion complète de la trésorerie avec caisses, coffres et transferts',
    'description': """
        Module de Gestion de Trésorerie Avancée
        ========================================

        Fonctionnalités :
        - Gestion des caisses
        - Transferts entre caisses (à venir)
        - Opérations de caisse (à venir)
        - Intégration avec les paiements (à venir)
        - Clôtures journalières (à venir)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],

    'external_dependencies': {
        'python': ['num2words'],
    },
    'data': [
        'data/treasury_data.xml',
        'security/treasury_security.xml',
        'security/ir.model.access.csv',
        'views/treasury_cash_views.xml',
        'reports/treasury_transfer_report_templates.xml',
        'reports/treasury_cash_closing_report.xml',
        'views/treasury_transfer_views.xml',
        'views/treasury_safe_views.xml',
        'views/treasury_safe_operation_views.xml',
        'views/treasury_operation_category_views.xml',
        'views/treasury_cash_operation_views.xml',
        'views/treasury_cash_closing_views.xml',
        'views/account_payment_views.xml',
        'views/treasury_dashboard_views.xml',  # Tableau de bord
        'views/treasury_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
