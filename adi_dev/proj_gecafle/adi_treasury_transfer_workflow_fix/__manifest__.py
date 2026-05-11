# -*- coding: utf-8 -*-
{
    'name': 'Treasury Transfer One-Click Workflow',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': "Fusionne Confirmer + Effectuer en un seul clic (draft → done)",
    'description': """
Treasury Transfer One-Click Workflow
====================================

L'étape « Effectuer le transfert » du module d'origine n'apportait
aucune sécurité financière supplémentaire : les opérations de caisse
étaient déjà postées et les soldes déjà impactés au moment du clic
sur « Confirmer ». La phase Done ne servait qu'à poser un tampon
« validé par X ».

Ce fix simplifie : un seul clic pour passer un transfert de Brouillon
à Effectué.

Ce qui change
-------------
- `action_confirm` enchaîne maintenant `super().action_confirm()` puis
  `action_done()` ⇒ pas d'arrêt intermédiaire en état 'confirm' pour
  les nouveaux transferts.
- Le bouton « Confirmer » est renommé « Effectuer le transfert » et
  reçoit la dialog de confirmation qui était précédemment sur Done.

Compatibilité legacy
--------------------
- Les transferts déjà en état 'confirm' au moment de l'install
  restent atteignables via le bouton existant (action_done) qui
  apparaît tant qu'un enregistrement est dans cet état.
- L'état 'confirm' lui-même n'est pas supprimé du Selection — pas
  de migration de données nécessaire.
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'adi_treasury',
        'adi_treasury_transfer_balance_fix',
    ],
    'data': [
        'views/treasury_transfer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
