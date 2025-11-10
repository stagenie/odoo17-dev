# -*- coding: utf-8 -*-
{
    'name': 'GeCaFle - Synchronisation Temps Réel',
    'version': '17.1.0',
    'category': 'Stock',
    'summary': 'Synchronisation en temps réel des réceptions dans les ventes',
    'description': """
        Module de synchronisation temps réel pour GeCaFle
        ==================================================
        
        Fonctionnalités:
        * Synchronisation automatique des réceptions vers les ventes
        * Rafraîchissement automatique sans F5
        * Communication multi-onglets en temps réel
        * Utilisation du système de Bus Odoo (WebSocket/Longpolling)
    """,
    "author": "ADICOPS",
    "email": 'info@adicops.com',
    "license": 'AGPL-3',
    "website": 'https://adicops.com/',
    
    'depends': [
        'base',
        'bus',
        'adi_gecafle_receptions',
        'adi_gecafle_ventes',
    ],
    
    'data': [
        'security/ir.model.access.csv',
    ],
    
    'assets': {
        'web.assets_backend': [
            'adi_gecafle_realtime_sync/static/src/js/realtime_sync_service.js',
            'adi_gecafle_realtime_sync/static/src/js/reception_realtime.js',
        ],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 100,
}
