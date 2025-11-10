{
    'name': 'Adicops BLS Avec NS  ',
    'version': '17.0.1.0',
    'sequence': 1,
    'category': 'Sales',
    'summary': 'Ce module va Adicops BLS Avec NS ',
    'description': "Ce module va permettre Adicops BLS Avec NS,...  ",
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
    ], 
    "data":  [                
         
         'views/adi_stock_move.xml',
         'views/adi_stock_report_views.xml',
         'views/adi_report_deliveryslip.xml'
         
    
        ],
    'demo': [],
    'test': [],
    'qweb': [],    
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
