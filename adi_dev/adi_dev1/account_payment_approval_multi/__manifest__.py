# -*- coding: utf-8 -*-
{
    'name': 'Payment Approval Multi',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Permet la validation multiple de paiements',
    'description': """
Payment Approval Multi
======================

Extension du module account_payment_approval pour permettre:
- La validation de plusieurs paiements à la fois depuis la vue liste
- La validation de plusieurs paiements via une action groupée

Seul l'utilisateur ayant les droits d'approbation peut effectuer cette action.
    """,
    'author': 'ADI Dev',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['account_payment_approval'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
