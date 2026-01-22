# -*- coding: utf-8 -*-
{
    'name': 'SAV Electroménager',
    'version': '17.0.2.0.0',
    'category': 'Services/After Sales',
    'summary': 'Gestion des retours et service après-vente électroménager',
    'description': """
SAV Electroménager - Gestion des Retours Multi-Niveaux
=======================================================

Module de gestion du service après-vente pour l'électroménager avec workflow multi-niveaux:

**Gestion Multi-Articles:**
* Retour de plusieurs articles simultanément avec numéros de série
* Lien vers plusieurs commandes et BL d'origine

**Circuit Multi-Acteurs:**
* Points de Vente: Déclarent les retours
* Centre de Retour: Centralise et coordonne
* Réparateurs: Effectuent les réparations

**Workflow Complet:**
* 10 états de suivi: Draft → Submitted → Received Center → Sent to Repairer → In Repair → Repaired → Returned to Center → Sent to Sales Point → Closed
* Traçabilité complète avec dates de chaque étape
* Boutons contextuels selon le rôle et l'état

**Sécurité par Rôle:**
* Utilisateur Point de Vente: Voir/modifier ses retours
* Gérant Centre: Gérer workflow complet
* Administrateur SAV: Accès total et configuration

**Documents PDF:**
* Bon de Livraison Centre → Réparateur
* Bon de Retour Réparateur → Centre
* Bon de Livraison Centre → Point de Vente

**Statistiques Avancées:**
* Rapports Pivot et Graph
* Filtres par point de vente, centre, réparateur
* Suivi des durées de réparation
    """,
    'author': 'ADI Dev',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'sale', 'stock'],
    'data': [
        # Security
        'security/sav_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/sav_category_data.xml',
        'data/sav_fault_type_data.xml',
        'data/sav_failure_reason_data.xml',
        # Views - Partenaires et Utilisateurs
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        # Views - Configuration
        'views/sav_category_views.xml',
        'views/sav_fault_type_views.xml',
        'views/sav_failure_reason_views.xml',
        # Views - Retours
        'views/sav_return_views.xml',
        # Menus
        'views/sav_menus.xml',
        # Reports
        'report/sav_report.xml',
        'report/sav_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
