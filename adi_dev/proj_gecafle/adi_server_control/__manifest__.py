# -*- coding: utf-8 -*-
{
    'name': 'ADI Server Control',
    'version': '17.0.2.0.0',
    'summary': 'Contrôle avancé du serveur Ubuntu et service Odoo configurable',
    'description': """
        Module de contrôle serveur permettant:
        - Arrêt sécurisé du serveur Ubuntu
        - Redémarrage du serveur Ubuntu
        - Redémarrage du service Odoo (configurable)
        - Gestion par groupe de sécurité dédié
        - Configuration du nom du service Odoo
        - Sans mot de passe (via sudoers)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Technical',
    'depends': ['base', 'web'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/server_config_data.xml',
        'wizard/wizard_views.xml',
        'views/server_control_views.xml',
        'views/server_config_views.xml',
        'views/database_backup_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
}
