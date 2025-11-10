{
    'name': 'Adicops STOCK QUANT User Restriction ',
    'version': '17.0.1.0',
    'sequence': 1,
    'category': 'Inventory',
    'summary': 'Adicops STOCK QUANT User Restriction',
    'description': "Adicops STOCK QUANT User Restriction...  ",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    
    "website":'https://adicops.com/',
    'license': "AGPL-3", 
    'depends': [
        'base',
        'product',
        'stock',
        'user_warehouse_restriction',
    ],

    "data":  [                
         
        'security/stock_quant_rule.xml',
         'views/adi_stock_quant.xml',
         'views/quant_tree_inventory_editable.xml',
         'views/res_user_locations_ids.xml',

         
    
        ],
    'demo': [],
    'test': [],
    'qweb': [],    
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
