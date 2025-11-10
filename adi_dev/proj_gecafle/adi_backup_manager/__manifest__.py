# -*- coding: utf-8 -*-
{
    'name': 'ADI Backup Manager',
    'version': '17.0.1.0.0',
    'summary': 'Gestionnaire avancé de sauvegardes avec récupération automatique',
    'description': """
        Module de gestion des sauvegardes permettant:
        - Configuration de répertoires de backup
        - Scan automatique des sauvegardes
        - Téléchargement individuel ou par lot
        - Monitoring de l'espace disque
        - Historique des récupérations
        - Synchronisation automatique (optionnel)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Technical',
    'depends': ['base', 'mail'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/backup_cron.xml',
        'views/backup_directory_views.xml',
        'views/backup_file_views.xml',
        'views/backup_recovery_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
}
