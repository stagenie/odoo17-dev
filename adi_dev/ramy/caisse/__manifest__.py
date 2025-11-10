# -*- coding: utf-8 -*-
{
    'name': "Caisse",
    'sequence' : '1',
    'version': '1.5',
    'summary': 'Cash & Account',
    'category': 'Account',
    'author': 'DJORF Ibtissem & Rachid Bencherif',
    'maintainer': 'DJORF Ibtissem',

    'depends': [
        'account_payment' ,'account', 'tax_identification_dz', 'hr', 'analytic','account_bnk_stm_cash_box'
        ],

    # always loaded
    'data': [ 
            'security/caisse_principale_security.xml',
            'security/ir.model.access.csv',

            'data/ir_sequence_data.xml',
            'data/motif_family_data.xml',
            'data/account_analytic_data.xml',
            'data/fund_motif_data.xml',
            'wizards/transaction.xml' ,

            'wizards/caisse_date_fin_view.xml',
            'views/fund_motif_family_view.xml',
            'views/fund_motif_view.xml',
            'wizards/account_payment_wizard.xml',

            'wizards/fund_advance_repproche_wizard_view.xml',
            'wizards/update_ecart_view.xml',

            'reports/report_stats_caisse.xml',
            'reports/caisse_report.xml',
           'reports/report_stats_avance.xml',
            
            'views/res_currency_view.xml' ,
            'views/fund_advance_view.xml' ,
            'views/res_config_settings_view.xml' ,
            'views/caisse.xml' ,
            'wizards/wizard_selection_periode_view.xml',
            #'views/caisse_annuelle.xml' ,
            # 'views/account_payment_view.xml',
            # 'reports/caisse_report.xml',
            
            'views/type_caisse_view.xml',
            'views/account_payment_view.xml',
            'views/menuitems.xml',
    ],
    # only loaded in demonstration mode
    'installable': True,
    'auto_install': False,
    'application': True,
}
