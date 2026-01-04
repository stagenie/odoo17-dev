{
    'name': "GECAFLE - Reset des Données",
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com/',
    'category': 'Tools',
    'summary': "Outil de réinitialisation des données transactionnelles GECAFLE",
    'description': """
        Module de Reset des Données GECAFLE
        ====================================

        Ce module permet aux administrateurs de :
        - Supprimer toutes les données transactionnelles (ventes, réceptions, etc.)
        - Conserver les données de base (produits, clients, producteurs, etc.)
        - Réinitialiser tous les compteurs à leur valeur initiale

        ATTENTION : Cette opération est IRRÉVERSIBLE !
        Seuls les administrateurs système peuvent utiliser cette fonctionnalité.
    """,
    'depends': [
        'adi_gecafle_base_stock',
        'adi_gecafle_ventes',
        'adi_gecafle_receptions',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/reset_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
