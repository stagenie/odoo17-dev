{
    'name': 'ADI Ventes - Factures Clients',
    'version': '17.0.1.0.0',
    'category': 'Sales/Accounting',
    'summary': 'Intégration des ventes GECAFLE avec la facturation Odoo',
    'description': """
        Ce module permet de créer automatiquement des factures clients
        à partir des bons de vente GECAFLE tout en conservant toutes
        les informations spécifiques (poids, emballages, consignes, etc.)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops.com/',
    'depends': [
        'adi_gecafle_ventes',
        'account',
    ],
    'data': [

        'security/ir.model.access.csv',
        'views/gecafle_vente_views.xml',
        'views/account_move_views.xml',
        'views/gecafle_vente_payment_views.xml',
        'reports/report_invoice_gecafle.xml',
        'reports/report_bon_vente_from_invoice.xml',
        'reports/report_bon_vente_inherit.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
