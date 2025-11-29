# -*- coding: utf-8 -*-
{
    'name': 'GeCaFle - Synchronisation Temps Réel V2',
    'version': '17.2.0',
    'category': 'Stock',
    'summary': 'Synchronisation en temps réel des réceptions dans les ventes',
    'description': """
        Module de synchronisation temps réel pour GeCaFle - Version 2
        ==============================================================

        Fonctionnalités:
        * Communication inter-onglets via BroadcastChannel API
        * Widgets Many2One personnalisés pour réceptions
        * Rechargement automatique des options en temps réel
        * Fallback localStorage pour navigateurs anciens
        * Aucune notification intrusive - rafraîchissement silencieux

        Architecture:
        * Service BroadcastChannel pour la communication
        * Widget reception_realtime pour le champ reception_id
        * Widget detail_reception_realtime pour detail_reception_id
        * Patches FormController et ListController pour broadcast
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "license": 'AGPL-3',
    "website": 'https://adicops.com/',

    'depends': [
        'base',
        'adi_gecafle_receptions',
        'adi_gecafle_ventes',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/vente_views_inherit.xml',
    ],

    'assets': {
        'web.assets_backend': [
            # Service de communication inter-onglets (doit être chargé en premier)
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
