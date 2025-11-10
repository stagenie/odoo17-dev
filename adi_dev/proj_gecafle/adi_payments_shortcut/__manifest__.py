# -*- coding: utf-8 -*-
{
    'name': ' Payment Sorcut',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment',
    'summary': 'Payment Sorcut',
    'description': """
Smart Payment Dispatch - Répartition automatique intelligente des paiements sur les factures impayées
==============================================================

Ce module permet de:
- Répartition automatique intelligente des paiements sur les factures impayées
- racourci payement clients / product

    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops-dz.com',
    'support': 'info@adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_payment',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/menu_views.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
