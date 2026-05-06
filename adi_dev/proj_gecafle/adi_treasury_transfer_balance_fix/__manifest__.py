# -*- coding: utf-8 -*-
{
    'name': 'Treasury Transfer Balance Fix',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': "Force le recalcul du solde des deux côtés d'un transfert",
    'description': """
Treasury Transfer Balance Fix
=============================

Corrige un bug où, après un transfert (caisse↔caisse, caisse↔coffre,
coffre↔coffre), seul le solde du côté **source** était rafraîchi
correctement. Le côté **destination** restait avec sa valeur précédente
parce que la dépendance @api.depends('operation_ids…') ne se déclenche
pas toujours de manière fiable lors de la création d'une opération
liée.

Solution
--------
Override de `action_confirm` et `action_cancel` sur `treasury.transfer`
pour forcer `_compute_current_balance` sur tous les enregistrements
caisse/coffre concernés après que le super() a fait son travail.

Ce module n'altère pas la logique métier d'origine ; il complète
uniquement la propagation du solde.
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'adi_treasury',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
