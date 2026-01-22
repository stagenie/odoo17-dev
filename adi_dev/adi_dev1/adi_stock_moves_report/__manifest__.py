# -*- coding: utf-8 -*-
{
    'name': 'Mouvements des Produits',
    'version': '17.0.0.0',
    'category': 'Account',
    'sequence': 1,
    'author': 'ADICOPS',
    'summary': 'Product  Stock Moves',
    'description': """
    
         Afficher les mouvements des Propduits 

    """,
    'website': '',
    'depends': [
        'base','product','stock',
	],
    'data': [
        'security/ir.model.access.csv',
        #'reports/pallet_movement_report.xml',
        'reports/products_movements_report.xml',
        #'wizards/pallet_movement_wizard_view.xml',
        'wizards/products_mouvements_wizard_view.xml',

    ],
    'installable': True,
    'application': False,
}
