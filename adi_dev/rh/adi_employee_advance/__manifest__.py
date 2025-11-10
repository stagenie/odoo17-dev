# -*- coding: utf-8 -*-
{
    'name': 'Gestion des Avances Employés',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Accounting',
    'summary': 'Gestion des avances sur salaire avec factures fournisseur automatiques',
    'description': """
        Module de gestion des avances employés :
        - Enregistrement des avances sur salaire
        - Création automatique de factures fournisseur
        - Suivi des remboursements
        - Intégration avec la paie
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "license" : "AGPL-3",

    "website": 'https://adicops.com/',
    'depends': ['hr', 'account','product','stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee_advance_views.xml',
        'views/menu_views.xml',
        'reports/advance_receipt_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
