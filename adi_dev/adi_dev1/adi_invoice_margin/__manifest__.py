# -*- coding: utf-8 -*-
{
    'name': 'Adicops Marge sur factures',
    'version': '17.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Calcul de la marge sur les factures et avoirs clients',
    'description': (
        "Ajoute des champs de marge (montant et %) sur les factures et avoirs "
        "clients, ainsi que dans les vues d'analyse."
    ),
    'author': 'ADICOPS',
    'website': 'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'views/account_invoice_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
