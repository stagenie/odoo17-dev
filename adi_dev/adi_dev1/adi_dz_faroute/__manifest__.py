{
    'name': 'Adicops BLV - Facture de R  ',
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
        'dns_amount_to_text_dz',
    ], 
    "data":  [

         'views/action_report_sale_order.xml',
         'views/adi_sale_order_with_tva.xml',
         'views/sale_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
