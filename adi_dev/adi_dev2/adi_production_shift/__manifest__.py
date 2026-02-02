# -*- coding: utf-8 -*-
{
    'name': 'ADI - Gestion des Shifts de Production',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Extension du module de coût de production pour gérer les shifts (2 ou 3 équipes)',
    'description': """
ADI - Gestion des Shifts de Production
======================================

Ce module étend le module adi_simple_production_cost pour permettre :

* Système 8 heures (pas de shift) : 1 production par jour (comportement par défaut)
* Système 2 Shifts : 2 productions par jour (Jour / Nuit)
* Système 3 Shifts : 3 productions par jour (Matin / Après-midi / Nuit)

Fonctionnalités :
-----------------
* Configuration du système de shift dans les paramètres
* Sélection du shift lors de la création d'une production
* Filtres et groupements par shift
* Contrainte unique par date ET par shift
    """,
    'author': 'ADI',
    'website': '',
    'depends': [
        'adi_simple_production_cost',
    ],
    'data': [
        'views/ron_config_views.xml',
        'views/ron_daily_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
