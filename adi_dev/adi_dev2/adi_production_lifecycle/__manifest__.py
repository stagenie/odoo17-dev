# -*- coding: utf-8 -*-
{
    'name': 'ADI - Cycle de Vie Production',
    'version': '17.0.2.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Remise en brouillon et verrouillage des productions journalières",
    'description': """
Gestion du cycle de vie des productions journalières :
- Remise en brouillon avec annulation en cascade des documents (BL, achats, factures)
- Retours de stock automatiques pour les opérations déjà validées
- Verrouillage des champs une fois la production confirmée ou terminée
- Protection contre la suppression des productions non-brouillon
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'adi_simple_production_cost',
        'stock',
        'purchase',
        'account',
    ],
    'data': [
        'views/ron_daily_production_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
