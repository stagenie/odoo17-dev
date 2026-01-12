# -*- coding: utf-8 -*-
{
    'name': 'SAV Electroménager',
    'version': '17.0.1.0.0',
    'category': 'Services/After Sales',
    'summary': 'Gestion des retours et service après-vente électroménager',
    'description': """
SAV Electroménager - Gestion des Retours
========================================

Module de gestion du service après-vente pour l'électroménager:

* Gestion des retours clients
* Suivi des réparations
* Catégorisation des produits (Congélation, Refroidissement, etc.)
* Types de pannes configurables
* Workflow complet de suivi
* Rapports et statistiques
    """,
    'author': 'ADI Dev',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'sale', 'stock'],
    'data': [
        # Security
        'security/sav_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/sav_category_data.xml',
        'data/sav_fault_type_data.xml',
        # Views
        'views/sav_category_views.xml',
        'views/sav_fault_type_views.xml',
        'views/sav_return_views.xml',
        'views/sav_menus.xml',
        # Reports
        'report/sav_report.xml',
        'report/sav_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
