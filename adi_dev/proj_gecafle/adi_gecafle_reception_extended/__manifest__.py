{
    'name': 'ADI GECAFLE Reception Extended',
    'version': '17.0.1.0.0',
    'category': 'Stock',
    'summary': 'Extension pour bordereaux avec tri et regroupement',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'license': 'AGPL-3',
    'depends': [
        'adi_gecafle_receptions',
        'adi_gecafle_ventes',
        'account',
        "adi_arabic_reports",
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_actions.xml',
        'views/wizard_views.xml',
        'views/reception_views.xml',
        'views/recap_views.xml',
        'views/recap_views_extended.xml',
        'reports/report_bordereau_grouped_fr.xml',
        'reports/report_bordereau_simple_fr.xml',
        'reports/report_bordereau_grouped_ar.xml',
        'reports/report_bordereau_simple_ar.xml',
        'reports/report_emballages_reception_fr.xml',
        'reports/report_emballages_reception_ar.xml',
        'reports/report_bon_reception_inherit.xml',  # NOUVEAU
        'reports/report_bon_reception_ar_inherit.xml',  # NOUVEAU
        'reports/report_bon_reception_ticket_inherit.xml',  # Héritage ticket avec transport/emballage
    ],
    'application': True,
    'installable': True,
}
