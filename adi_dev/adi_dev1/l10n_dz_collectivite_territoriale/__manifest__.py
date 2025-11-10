# -*- coding: utf-8 -*-
{
    'name': "Collectivité territoriale algérienne",
    'category': '',
    'summary': """ Collectivité territoriale algérienne - odoo 17 """,
    "contributors": [
        "1 <Nassim REFES>",
    ],
    'sequence': 1,
    'version': '17.0.1.0',
    "license": "LGPL-3",
    'author': 'DevNationSolutions',
    'website': 'https://devnation-solutions.com/',
    "price": 1.99,
    "currency": 'EUR',
    'depends': [
        'base',
    ],
    'data': [
        'views/res_country_state_composition.xml',
        'views/res_country_state.xml',
        'views/res_company.xml',
        'views/res_partner.xml',

        'data/wilayas.xml',
        'data/res.country.state.composition.csv',
        'data/res_country_disposition.xml',

        'security/ir.model.access.csv',
    ],
    'images': ['images/main_screenshot.gif'],

    'installable': True,
    'auto_install': False,
    'application': False,
}