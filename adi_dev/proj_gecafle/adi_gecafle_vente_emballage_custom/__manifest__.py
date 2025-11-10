# -*- coding: utf-8 -*-
{
    'name': 'ADI GECAFLE - Personnalisation Emballages Vente',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Personnalisation du comportement des emballages et rapports',
    'description': """
        Module de personnalisation des emballages et consignes pour GECAFLE :
        - Sélecteur Rendu/Non Rendu personnalisable par ligne de vente
        - Prix de colis modifiable directement sur la ligne
        - Calcul correct du poids brut unitaire
        - Poids unitaire moyen et prix brut unitaire
        - Rapports de bon de vente améliorés (FR et AR)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'license': 'AGPL-3',
    'depends': [
        #'adi_gecafle_ventes',
        #'adi_gecafle_vente_invoices',
        #'adi_gecafle_base_stock',
        'adi_gecafle_ventes',
        'account',
        'adi_arabic_reports',  # Si vous avez le module arabe

    ],
    'data': [
       # 'security/ir.model.access.csv',
        'views/vente_form_views.xml',
      #  'views/vente_tree_views.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
