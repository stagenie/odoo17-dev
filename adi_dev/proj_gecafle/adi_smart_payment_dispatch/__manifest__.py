# -*- coding: utf-8 -*-
{
    'name': 'Smart Payment Dispatch',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment',
    'summary': 'Répartition automatique intelligente des paiements sur les factures impayées',
    'description': """
Smart Payment Dispatch - Répartition Automatique des Paiements
==============================================================

Ce module permet de:
- Afficher automatiquement toutes les factures impayées d'un partenaire
- Répartir automatiquement un paiement sur plusieurs factures (méthode FIFO)
- Gérer les paiements partiels et les surplus
- Créer un solde créditeur en cas de trop-perçu
- Annuler proprement les allocations en cas d'annulation du paiement

Fonctionnalités principales:
- Vue enrichie des paiements avec détail des factures impayées
- Calcul automatique de la répartition selon l'ancienneté
- Lettrage automatique des écritures comptables
- Gestion bidirectionnelle (clients et fournisseurs)
- Traçabilité complète des allocations
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops-dz.com',
    'support': 'info@adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_payment',
    ],
    'data': [
        # Sécurité
        # 'security/security.xml',  simplifions pour le moment
        'security/ir.model.access.csv',


        # Vues
        'views/account_payment_views.xml',
        'views/payment_allocation_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
