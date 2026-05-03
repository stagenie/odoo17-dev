# -*- coding: utf-8 -*-
{
    'name': 'ADI - Analyse Consommations Production : Emballages & Films',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Extension qui inclut les emballages et films dans l'analyse "
               "et le rapport PDF des consommations",
    'description': """
ADI - Analyse Consommations - Extension Emballages & Films
==========================================================

Module **complémentaire** à `adi_consumption_analysis` qui ajoute, sans
modifier le module de base :

* Intégration des **emballages** (SOLO / CLASSICO / Sandwich GF) et
  **films** (SOLO / CLASSICO / Sandwich GF) dans la vue SQL d'analyse
  via un UNION ALL — ils deviennent visibles dans les vues
  pivot / graph / tree.
* Filtre **Catégorie de consommation** (Matière Première / Emballage / Film)
  dans la barre de recherche et le groupement.
* Wizard d'impression enrichi avec un sélecteur **Portée du rapport** :
  - MP + Emballages/Films (rapport complet)
  - Matières Premières uniquement
  - Emballages/Films uniquement (coûts seulement)
* Rapport PDF avec une section dédiée **Emballages & Films** affichant
  uniquement les coûts (Quantité / Coût Unitaire / Coût Total).

Le module de base reste totalement intact ; sa désinstallation supprime
proprement cette extension.
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'adi_consumption_analysis',
    ],
    'data': [
        'wizard/print_consumption_report_wizard_views.xml',
        'views/ron_consumption_analysis_views.xml',
        'reports/consumption_period_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
