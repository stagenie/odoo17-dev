{
    'name': "GECAFLE - Configuration des Séquences",
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com/',
    'category': 'Sales/Configuration',
    'summary': "Configuration des formats de séquences Vente et Réception",
    'description': """
        Module de configuration des séquences pour GECAFLE
        ===================================================

        Ce module permet aux utilisateurs de configurer :
        - Le format du N° de Vente
        - Le format du N° de Bon de Réception

        Options disponibles :
        - Choix du séparateur (- ou /)
        - Inclusion de l'année en cours
        - Préfixe personnalisable
    """,
    'depends': [
        'adi_gecafle_base_stock',
        'adi_gecafle_ventes',
        'adi_gecafle_receptions',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
