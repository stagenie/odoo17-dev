# -*- coding: utf-8 -*-
{
    'name': 'ADI Réception Valorisée',
    'version': '17.0.1.0.0',
    'category': 'Stock/Purchase',
    'summary': 'Gestion des réceptions valorisées (achats) avec facturation',
    'description': """
        Ce module étend les réceptions pour gérer les achats valorisés:
        - Ajout de prix et montants sur les réceptions
        - Gestion des emballages achetés/rendus
        - Création de factures fournisseurs
        - Rapports FR/AR
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'AGPL-3',
    'depends': [

        'adi_gecafle_reception_extended',
        'adi_gecafle_ventes',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/reception_valorisee_views.xml',
        'views/details_reception_views.xml',
        'views/recap_views_inherit.xml',
        'views/account_move_views.xml',
        'reports/report_bon_reception_valorise.xml',
        'reports/report_bon_reception_valorise_ar.xml',
        #'reports/report_templates.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
