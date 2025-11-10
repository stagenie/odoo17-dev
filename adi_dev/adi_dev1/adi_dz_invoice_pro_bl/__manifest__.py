{
    'name': 'Adicops Proforma BL Invoice Report ',
    'category': 'Sales',
    'version': '17.0.1.0',
    'sequence': 1,

    'summary': 'Ce module va permettre Personnalisation des Rapports Fact',
    'description': "Ce module va permettre Personnalisation des Rapports Fact",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    "website":'https://adicops.com/',
    'license': "AGPL-3", 
    'depends': [
        'base',
        'account',
        'dns_amount_to_text_dz',
    ], 
    "data":  [
         'views/adi_account_move.xml',
         'views/document_tax_total.xml',
         'views/adi_account_report.xml',
         'views/adi_report_invoice_atva.xml',
         'views/adi_report_invoice_atva_item.xml',
         'views/adi_report_invoice_atva_item_nv.xml',

        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
