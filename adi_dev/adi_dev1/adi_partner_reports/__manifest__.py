# -*- coding: utf-8 -*-
{
    'name': 'Rapports Partenaires - Créances, Dettes et Grand Livre Détaillé',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Rapports PDF Créances Clients, Dettes Fournisseurs et Grand Livre Détaillé',
    'depends': ['account', 'accounting_pdf_reports'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_actions.xml',
        'report/report_partner_balance.xml',
        'report/report_partner_ledger_detailed.xml',
        'wizard/partner_balance_report_views.xml',
        'wizard/partner_ledger_detailed_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
