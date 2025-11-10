# __manifest__.py
{
    'name': 'ADI GECAFLE - Contrôle des Ventes',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Contrôle avancé des ventes et protection des factures',
    'description': """
        Module de contrôle des ventes GECAFLE :
        ✓ Protection des factures contre les modifications
        ✓ Remise en brouillon conditionnelle des ventes  
        ✓ Gestion automatique des paiements et factures
        ✓ Intégration avec les récaps producteur
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'depends': [
        'adi_gecafle_ventes',
        'adi_gecafle_vente_invoices',
        'adi_treasury',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_move_payment_button.xml',
        'views/account_move_button_visibility.xml',
        'views/gecafle_avoir_producteur_views.xml',
        'views/gecafle_recap_control_views.xml',  # AJOUT
        'views/gecafle_vente_views.xml',
        'wizard/vente_reset_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adi_gecafle_vente_control/static/src/js/hide_create_button.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
