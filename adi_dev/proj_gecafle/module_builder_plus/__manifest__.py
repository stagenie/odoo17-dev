# -*- coding: utf-8 -*-
{
    'name': 'Module Builder Plus',
    'version': '2.0',
    'category': 'Development',
    'summary': 'Advanced Odoo module builder with export and generation features',
    'description': """
Module Builder Plus
==================
Module avancé pour créer et gérer des modules Odoo avec des fonctionnalités étendues :
- Import de modules ZIP/RAR avec analyse complète
- Export sélectif par type de fichier (Python, XML, JS, etc.)
- Génération automatique de modules à partir de code
- Support étendu de tous les formats de fichiers Odoo
    """,
    'author': 'OdooMaster AI',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_views.xml',
        'wizard/module_merge_wizard_views.xml',  # Ajouter cette ligne
        'views/module_content_plus_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
