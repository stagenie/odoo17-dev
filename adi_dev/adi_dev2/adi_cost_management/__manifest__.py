# __manifest__.py
{
    'name': 'ADI Gestion Prix de Revient avec Rebuts',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Calcul du prix de revient réel incluant la gestion des rebuts',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'depends': [
        'mrp',
        'stock',
        'product',
        'uom',
        'mail',
    ],
    'data': [
        # 1. SÉCURITÉ (toujours en premier)
        'security/security.xml',
        'security/ir.model.access.csv',

        # 2. DATA (séquences, données de base)
        'data/sequence_data.xml',

        # 3. RAPPORTS (DOIT être AVANT les vues qui les référencent)
        'reports/cost_analysis_report.xml',

        # 4. WIZARD (avant les vues si référencé)
        'wizard/cost_calculation_wizard.xml',

        # 5. VUES (référencent les actions des rapports)
        'views/adi_daily_production_views.xml',
        'views/adi_scrap_management_views.xml',
        'views/adi_cost_analysis_views.xml',

        # 6. MENUS (toujours à la fin)
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
