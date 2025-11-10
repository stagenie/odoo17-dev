{
    'name': 'Adicops Facture de R  ',
    'category': 'Sales',
    'version': '17.0.1.0',
    'sequence': 1,

    'summary': 'Adicops Facture de R ',
    'description': "Adicops Facture de R...  ",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    "website":'https://adicops.com/',
    'license': "AGPL-3", 
    'depends': [
        'base',
        'sale',
        'stock',
        'dns_amount_to_text_dz',
    ], 
    "data":  [

         'views/adi_report_deliveryslip.xml',
         'views/adi_report_deliveryslip_faroute.xml',
         'views/adi_stock_report_views.xml',
         'views/stock_picking.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
