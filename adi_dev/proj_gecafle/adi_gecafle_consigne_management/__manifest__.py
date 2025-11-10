
# -*- coding: utf-8 -*-
{
    'name': "GECAFLE - Gestion des Consignes",
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops.com/',
    'category': 'Sales/Sales',
    'summary': "Gestion des consignes et retours d'emballages",
    'description': """
        Module de gestion des consignes pour GECAFLE :
        - Gestion des retours d'emballages consignés
        - Création automatique d'avoirs pour remboursement de consignes
        - Suivi des états de consigne par vente
        - Processus de remboursement automatisé
    """,
    'depends': [
        'adi_gecafle_ventes',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/vente_inherit_views.xml',
        'views/consigne_retour_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
