# -*- coding: utf-8 -*-
{
    "name": "ADI GECAFLE Gestion des Ventes",
    "version": "17.0.1.1.0",
    "author": "ACICOPS",
    "website": "https://adicops-dz.com/",
    "license": "AGPL-3",
    "category": "Sales",
    "depends": ["adi_gecafle_receptions", "mail", "account"],
    "data": [
        'security/security.xml',
        # 'security/adjustment_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',

        "views/param_res_comp.xml",
        "views/client_views.xml",
        "views/menus_app_vente.xml",
        "views/vente_views.xml",
        'views/gecafle_emballage_client.xml',
        'views/reception_extended.xml',
        'reports/recap_actions.xml',
        'views/account_move_inherit_views.xml',

        'reports/recap_reports.xml',
        'reports/recap_templates.xml',
        'reports/report_vendor_invoice_gecafle.xml',
        'reports/report_avoir_producteur.xml',
        'reports/report_bon_pese.xml',

        'views/recap_receptions_views.xml',
        'views/reception_extended_recap.xml',

        'reports/reports.xml',
        'reports/sale_recap_reports.xml',
        'reports/sale_recap_templates.xml',
        'reports/report_bon_vente.xml',

        'views/gecafle_bon_achat.xml',
        # Avoir clients producteuts
        'data/sequence.xml',
        'views/avoir_client_views.xml',
        'views/avoir_producteur_views.xml',
        'views/menus.xml',
        'reports/report_avoir_client.xml',

    ],
    "installable": True,
    "application": True,
}
