# -*- coding: utf-8 -*-
{
    'name': 'Suppression Factures Annulées',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Permet la suppression des factures annulées (clients et fournisseurs)',
    'description': """
Suppression des Factures Annulées
=================================

Ce module permet de supprimer les factures qui sont en état "Annulé".

Fonctionnalités:
- Bouton de suppression sur les factures annulées
- Dissociation automatique des bordereaux avant suppression
- Accessible à tous les utilisateurs ayant accès aux factures
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'adi_gecafle_ventes',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
