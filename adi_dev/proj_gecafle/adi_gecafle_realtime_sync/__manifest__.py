# -*- coding: utf-8 -*-
{
    'name': 'GeCaFle - Synchronisation Temps Réel V3',
    'version': '17.3.0',
    'category': 'Stock',
    'summary': 'Synchronisation en temps réel des réceptions dans les ventes',
    'description': """
        Module de synchronisation temps réel pour GeCaFle - Version 3
        ==============================================================

        Ce module permet aux réceptions enregistrées d'apparaître instantanément
        dans les listes déroulantes des ventes, sans nécessiter de rafraîchissement F5.

        Changements V3:
        * Correction du bug où les nouvelles réceptions n'apparaissaient pas
        * Override correct de Many2XAutocomplete au lieu de Many2OneField
        * name_search dynamique qui filtre les réceptions avec stock disponible
        * Invalidation du cache ORM à chaque recherche
        * Polling serveur toutes les 2 secondes

        Fonctionnalités:
        * Communication inter-onglets via BroadcastChannel API
        * Widgets Many2One personnalisés avec autocomplete temps réel
        * Rechargement automatique des options sans F5
        * Fallback localStorage pour navigateurs anciens

        Architecture:
        * Service gecafle_sync pour la communication temps réel
        * Override de Many2XAutocomplete.search() pour données fraîches
        * Patches FormController et ListController pour notifications
        * name_search dynamique sur gecafle.reception
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "license": 'AGPL-3',
    "website": 'https://adicops.com/',

    'depends': [
        'base',
        'web',
        'adi_gecafle_receptions',
        'adi_gecafle_ventes',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/vente_views_inherit.xml',
    ],

    'assets': {
        'web.assets_backend': [
            # Service de synchronisation (chargé en premier)
            'adi_gecafle_realtime_sync/static/src/js/broadcast_channel_service.js',
            # Widgets personnalisés
            'adi_gecafle_realtime_sync/static/src/js/reception_realtime_widget.js',
            'adi_gecafle_realtime_sync/static/src/js/detail_reception_realtime_widget.js',
            # Patches des contrôleurs
            'adi_gecafle_realtime_sync/static/src/js/reception_form_patch.js',
            'adi_gecafle_realtime_sync/static/src/js/reception_list_patch.js',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 100,
}
