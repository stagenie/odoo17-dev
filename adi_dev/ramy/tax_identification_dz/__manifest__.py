# -*- coding: utf-8 -*-

{
    'name': 'Algerian - tax identification',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
This is the module to add company tax identification in Algeria.
======================================================================
This module applies to companies based in Algeria.
""",
    'author': 'Azertics Consulting',
    'depends': ['base','contacts','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/company_social_reason_view.xml',
        'data/res_partner_social_reason_data.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
