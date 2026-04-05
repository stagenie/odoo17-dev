# -*- coding: utf-8 -*-
{
    'name': 'ADI - Affichage Lignes Devis/Commandes',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Numéros de ligne, nom produit sans référence et tri alphabétique",
    'description': """
Améliorations d'affichage des lignes de devis/commandes :
- Numérotation automatique des lignes (N°)
- Nouveau champ "Nom du produit" affichant uniquement le nom sans la référence
- Champ description masqué par défaut (optional=hide)
- Possibilité de trier par nom de produit
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'sale',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
