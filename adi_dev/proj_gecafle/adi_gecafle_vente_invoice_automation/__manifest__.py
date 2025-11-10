# -*- coding: utf-8 -*-
{
    'name': 'ADI GECAFLE - Automatisation Facturation Vente',
    'version': '17.0.1.0.2',
    'category': 'Sales/Accounting',
    'summary': 'Automatisation de la création des factures avec comptabilisation directe',
    'description': """
        Ce module permet d'automatiser la création des factures depuis les ventes GECAFLE
        avec la possibilité de les comptabiliser directement ou de les créer en brouillon.

        Fonctionnalités :
        - Paramètre société pour activer la comptabilisation automatique
        - Gestion intelligente des erreurs avec fallback en mode brouillon
        - Logs détaillés des opérations
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'depends': [
        'adi_gecafle_ventes',
        'adi_gecafle_vente_invoices',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        #'views/gecafle_vente_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,  # Priorité maximale
}
