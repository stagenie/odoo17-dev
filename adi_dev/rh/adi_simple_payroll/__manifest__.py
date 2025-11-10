# -*- coding: utf-8 -*-
{
    'name': 'Gestion Simplifiée de Paie',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Module de paie simplifié avec intégration pointage, avances et prêts',
    'description': """
        Module de gestion de paie simplifiée :
        - Calcul automatique basé sur les pointages
        - Intégration des avances et prêts
        - Gestion par période et par lot
        - Génération de bulletins de paie
        - Comptabilisation groupée
    """,
    "author": "ADICOPS",
    "license": "AGPL-3",
    "email": 'info@adicops.com',
    "website": 'https://adicops.com/',
    'depends': [
        'hr',
        'hr_contract',
        'account',
        'adi_simple_attendance',
        'adi_employee_advance',
        'adi_employee_loans'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payroll_data.xml',
        'views/payroll_period_views.xml',
        'views/payroll_batch_views.xml',
        'views/payroll_slip_views.xml',
        'views/menu_views.xml',
        'reports/payroll_slip_report.xml',
        'reports/payroll_batch_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


