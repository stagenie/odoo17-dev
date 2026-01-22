# -*- coding: utf-8 -*-
{
    'name': 'Mouvements des Produits - Enhanced',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Reporting',
    'sequence': 1,
    'author': 'ADICOPS',
    'summary': 'Rapport Mouvements Produits avec filtrage par Entrepôts et Emplacements',
    'description': """
Mouvements des Produits - Version Améliorée
============================================

Ce module étend le rapport de mouvements de produits avec des fonctionnalités avancées :

**Nouvelles fonctionnalités :**
* Sélection des entrepôts (Tous ou certains)
* Sélection des emplacements liés aux entrepôts sélectionnés
* Filtrage dynamique des emplacements selon les entrepôts choisis
* Rapport détaillé par emplacement

**Utilisation :**
1. Choisir "Tous les entrepôts" ou sélectionner des entrepôts spécifiques
2. Choisir "Tous les emplacements" ou sélectionner des emplacements spécifiques
3. Les emplacements disponibles sont filtrés selon les entrepôts sélectionnés
4. Générer le rapport avec les filtres appliqués

    """,
    'website': '',
    'depends': [
        'adi_stock_moves_report',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/product_movement_wizard_enhanced_view.xml',
        'reports/product_movements_enhanced_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
