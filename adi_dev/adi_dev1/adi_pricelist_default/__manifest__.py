{
    'name': 'ADICOPS Simple Price Liste',
    'version': '17.0.0.0',
    'sequence': 1,
    'category': 'Sales',
    'summary': 'ADICOPS Simple Price Liste. ',
    'description': "ADICOPS Simple Price Liste. ",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    "website":'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
        'muk_product',
        #
        #  'website'
    ], 
    "data":  [
       #'security/groups.xml',
        'views/product_sale.xml',
      #  'views/product_list.xml',
        ],
    'demo': [],
    'test': [],
    'qweb': [],    
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
