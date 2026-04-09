# -*- coding: utf-8 -*-
{
    'name': 'ADI - Analyse Consommations Production',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Analyse des consommations de matières premières par période (graph, pivot, rapport PDF)",
    'description': """
ADI - Analyse des Consommations de Production
==============================================

Module complémentaire à **adi_simple_production_cost** qui ajoute, dans
l'application de Production Journalière, une vue d'analyse des
consommations de matières premières par période.

Fonctionnalités:
----------------
* Vue **Pivot** : consommations par article × période (mois, année, ...)
* Vue **Graph** : visualisation stackée par produit/période
* Vue **Liste** : détail des consommations avec totaux
* Filtres rapides : Aujourd'hui, Ce Mois, Mois Précédent, Cette Année
* Filtres par type de production : SOLO/CLASSICO, Sandwich GF
* Sélection multi-articles ou tous les articles
* Métrique MP/Produit Fini (kg consommés par carton produit)
* Wizard d'impression d'un **rapport PDF** listant période, articles et
  quantités consommées

Exemple: Total Consommation de Farine - Mars 2026 - 200 Tonnes
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'adi_simple_production_cost',
    ],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',

        # Vues analyse
        'views/ron_consumption_analysis_views.xml',

        # Wizard (doit être chargé avant les menus qui le référencent)
        'wizard/print_consumption_report_wizard_views.xml',

        # Rapports
        'reports/consumption_period_report.xml',

        # Menus (dépendent de l'action analyse et de l'action wizard)
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
