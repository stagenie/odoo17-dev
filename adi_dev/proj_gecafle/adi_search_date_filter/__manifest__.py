# -*- coding: utf-8 -*-
{
    'name': 'ADI Recherche par Date',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Ajoute la recherche par date dans les paiements et factures',
    'description': """
        Ce module ajoute un champ de recherche par date (sans heure) dans :
        - Paiements clients
        - Paiements fournisseurs
        - Factures clients
        - Factures fournisseurs
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_payment_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
