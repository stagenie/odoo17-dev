# -*- coding: utf-8 -*-
{
    'name': 'GECAFLE - Automatisation des Avoirs',
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Sales/Accounting',
    'summary': "Automatisation complète du processus de création d'avoirs",
    'description': """
        Module d'automatisation des avoirs GECAFLE :
        ✓ Validation automatique des avoirs clients
        ✓ Création automatique des notes de crédit
        ✓ Validation automatique des documents comptables  
        ✓ Génération intelligente des avoirs producteurs
        ✓ Processus en un clic avec le bouton "Avoir Express"
        ✓ Configuration flexible par société
        ✓ Gestion intelligente selon le type d'avoir
    """,
    'depends': [
        'adi_gecafle_ventes',
        'adi_gecafle_consigne_management',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'wizard/avoir_express_wizard_view.xml',
        'views/avoir_client_views.xml',
        'views/company_avoir_settings.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
