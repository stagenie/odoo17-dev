# -*- coding: utf-8 -*-
{
    'name': 'Treasury Sequence Fix',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Corrige les droits sur ir.sequence pour les opérations de trésorerie',
    'description': """
Treasury Sequence Fix
=====================

Ce module corrige le problème d'accès aux séquences (ir.sequence) pour les
utilisateurs non-administrateurs lors des opérations de trésorerie.

Problème résolu:
- Les utilisateurs sans droits admin ne pouvaient pas valider les transferts
  entre caisses et coffres à cause des restrictions sur ir.sequence

Solution:
- Utilisation de sudo() pour les opérations de recherche/création/incrémentation
  des séquences dans les modèles de trésorerie
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
