{
    'name': 'Cachet et Signature sur Factures',
    'category': 'Accounting',
    'version': '17.0.1.0',
    'sequence': 1,
    'summary': 'Ajouter un cachet/signature scanné sur les rapports de factures',
    'description': "Permet de télécharger un cachet/signature et de l'afficher sur les factures PDF avec dimensions configurables.",
    'author': 'ADICOPS',
    'email': 'info@adicops.com',
    'website': 'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'adi_dz_reports',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/report_invoice_stamp.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
