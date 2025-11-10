# -*- coding: utf-8 -*-
{
    'name': 'Gestion Simple de Pointage',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Module simplifié pour la gestion des pointages quotidiens',
    'description': """
        Module de gestion de pointage permettant :
        - Saisie rapide des présences par département
        - Gestion des heures supplémentaires
        - Contrôle des absences
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "license": 'LGPL-3',
    "depends": ['hr', 'hr_contract', 'mail'],
    "website": 'https://adicops.com/',
    'data': [
        'security/ir.model.access.csv',
        'views/attendance_daily_views.xml',
        'reports/attendance_sheet_report.xml',
        'views/menu_views.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
