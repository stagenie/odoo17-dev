# -*- coding: utf-8 -*-
{
    'name': 'Company About - Informations Intégrateur',
    'version': '17.0.1.0.0',
    'category': 'Administration',
    'summary': 'Module pour afficher les informations sur la société intégratrice dans Odoo',
    'description': '''
        Ce module permet de configurer et d'afficher les informations 
        sur la société qui a intégré et développé les modules Odoo.

        Fonctionnalités:
        - Configuration des informations société (admin uniquement)
        - Menu About accessible à tous les utilisateurs Odoo
        - Interface responsive dans le backend Odoo        
    ''',
    'author': 'Adicops',
    'website': 'https://www.adicops-dz.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/company_about_config_views.xml',
        'views/company_about_display_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
