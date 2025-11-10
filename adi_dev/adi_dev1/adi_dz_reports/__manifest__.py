{
    'name': 'Adicops Personnalisation des Rapports liés à SIEMTEC  ',
    'category': 'Sales',
    'version': '17.0.1.0',
    'sequence': 1,

    'summary': 'Ce module va permettre Personnalisation des Rapports liés à SIEMTEC  ',
    'description': "Ce module va permettre Personnalisation des Rapports liés à SIEMTEC ,...  ",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    "website":'https://adicops.com/',
    'license': "AGPL-3", 
    'depends': [
        'base',
        'product',
        'purchase',
        'account',
        'sale',
        'stock',
        'dns_amount_to_text_dz',
    ], 
    "data":  [
         'views/adi_purchase_reports.xml',
         'views/adi_purchase_quotation_templates.xml',
         'views/adi_purchase_order_templates.xml',
         'views/document_tax_total.xml',
         'views/action_report_sale_order.xml',
         'views/adi_sale_order_with_tva.xml',
         'views/adi_sale_order_with_tva_proforma.xml',
         'views/adi_account_report.xml',
         'views/adi_report_invoice_atva.xml',
         'views/adi_report_invoice_atva_item.xml',

    
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
