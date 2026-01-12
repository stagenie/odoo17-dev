# -*- coding: utf-8 -*-
{
    'name': 'Contrôle des Transferts de Stock',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Contrôle des transferts de stock avec affichage de la quantité disponible',
    'description': """
Ce module ajoute les fonctionnalités suivantes:

* Affiche la quantité disponible dans l'entrepôt source dans les lignes de transfert
* Empêche les transferts si la quantité demandée dépasse la quantité disponible
* Alerte visuelle si le stock est insuffisant
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
