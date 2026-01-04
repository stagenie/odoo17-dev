# -*- coding: utf-8 -*-
{
    "name": "ADI GECAFLE Consigne Emballage Fix",
    "version": "17.0.1.1.0",
    "author": "ACICOPS",
    "website": "https://adicops-dz.com/",
    "license": "AGPL-3",
    "category": "Sales",
    "summary": "Correction du suivi R/NR des emballages dans les consignes",
    "description": """
Correction du comportement Rendu/Non Rendu des emballages
==========================================================

Ce module corrige le problème où le comportement R/NR forcé sur les lignes
de vente n'était pas pris en compte dans:
- Le suivi des emballages (gecafle.details_emballage_vente)
- Le calcul de l'état de consigne
- La création des retours de consigne

Modifications:
- Ajoute le champ 'est_consigne' sur gecafle.details_emballage_vente
- Regroupe les emballages par (emballage_id + est_consigne)
- Corrige le calcul de l'état de consigne
- Corrige la préparation des lignes de retour

Inclut un wizard pour corriger les données existantes.
    """,
    "depends": [
        "adi_gecafle_vente_emballage_custom",
        "adi_gecafle_consigne_management",
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/details_emballage_vente_views.xml',
        'views/vente_button_fix_views.xml',
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
