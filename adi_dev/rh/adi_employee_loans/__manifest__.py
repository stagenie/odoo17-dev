# -*- coding: utf-8 -*-
{
    'name': 'Gestion des Prêts Employés',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Accounting',
    'summary': 'Gestion des prêts employés avec échéancier de remboursement',
    'description': """
        Module de gestion des prêts employés :
        - Enregistrement des demandes de prêt
        - Calcul automatique des échéances
        - Suivi des remboursements
        - Intégration avec la paie
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "website": 'https://adicops.com/',
    'depends': ['hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee_loan_views.xml',
        'views/loan_installment_views.xml',
        'views/menu_views.xml',
        'reports/loan_agreement_report.xml',
    ],
    "license": "AGPL-3",
    'installable': True,
    'application': True,
    'auto_install': False,
}

