{
    'name': 'ADI GECAFLE Synchronisation Partners',
    'version': '17.0.1.0.0',
    'category': 'Base',
    'summary': 'Synchronisation bidirectionnelle Clients/Fournisseurs Odoo ↔ GECAFLE',
    'description': """
        Ce module synchronise automatiquement :
        - res.partner (clients) ↔ gecafle.client
        - res.partner (fournisseurs) ↔ gecafle.producteur

        Fonctionnalités :
        - Création automatique bidirectionnelle
        - Synchronisation des modifications
        - Archivage au lieu de suppression
        - Gestion des doublons
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'adi_gecafle_ventes',
        'adi_gecafle_base_stock',
        'contacts',
        'account',
        'accounting_pdf_reports',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/gecafle_client_views.xml',
        'views/gecafle_producteur_views.xml',
        'views/menu_partners.xml',
    ],
    'application': True,
    'installable': True,
}
