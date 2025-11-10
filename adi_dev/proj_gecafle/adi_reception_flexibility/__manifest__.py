# -*- coding: utf-8 -*-
{
    'name': 'ADI GECAFLE - Flexibilité Réceptions',
    'version': '17.0.2.1.0',  # Version augmentée
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Stock/Sales',
    'summary': "Permet la modification complète des réceptions confirmées avec synchronisation",
    'description': """
        Module amélioré pour permettre la modification des réceptions :
        ✓ Modification directe sans wizard
        ✓ Synchronisation automatique des emballages
        ✓ Modification de l'option acheté pour toutes les réceptions
        ✓ Suppression intelligente avec sync
        ✓ Gestion cohérente des états
    """,
    'depends': [
        'adi_gecafle_reception_extended',
        'adi_gecafle_ventes',
        'adi_reception_valorisee',  # Si disponible
    ],
    'data': [
        'views/reception_flexible_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
