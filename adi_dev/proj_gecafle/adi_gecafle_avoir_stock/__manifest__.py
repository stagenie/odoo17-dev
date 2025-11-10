# -*- coding: utf-8 -*-
{
    'name': 'GECAFLE - Avoir Stock avec Sélection Détaillée',
    'version': '17.0.2.0.0',  # Version mise à jour
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Sales/Accounting',
    'summary': "Extension pour gérer les avoirs stock avec sélection détaillée et création de réceptions de retour",
    'description': """
        Module d'extension des avoirs GECAFLE pour les cas de stock :
        ✅ Sélection détaillée des produits à inclure dans l'avoir
        ✅ Chargement automatique des lignes de vente
        ✅ Gestion des quantités par produit (colis et kg)
        ✅ Calcul automatique du montant basé sur les produits sélectionnés
        ✅ Interface utilisateur intuitive avec toggles
        ✅ Support des avoirs partiels
        ✅ Création de réceptions de retour avec regroupement intelligent
        ✅ Gestion du retour de stock pour revente ou déstockage
    """,
    'depends': [
        'adi_gecafle_avoir_automation',
        'adi_gecafle_ventes',
        'adi_gecafle_receptions',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/vente_views.xml',
        'views/reception_views.xml',  # NOUVEAU
        'wizard/avoir_stock_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
