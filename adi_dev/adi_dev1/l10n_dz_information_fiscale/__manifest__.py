# -*- coding: utf-8 -*-

{
    'name': "Information Fiscale",
    'category': 'Accounting/Accounting',
    'summary': """ Information Fiscale - odoo 14 """,
    "contributors": [
        "1 <Nassim REFES>",
    ],
    'sequence': 1,
    'version': '17.0.1.0',
    "license": "LGPL-3",
    'author': 'DevNationSolutions',
    'website': 'https://devnation-solutions.com/',
    "price": 0.0,
    "currency": 'EUR',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'data/forme_juridique_datas.xml',

        'views/forme_juridique.xml',
        'views/res_company.xml',
        'views/res_partner.xml',

        'security/ir.model.access.csv',
    ],
    'images': ['images/main_screenshot.gif'],

    'installable': True,
    'auto_install': False,
    'application':False,
}