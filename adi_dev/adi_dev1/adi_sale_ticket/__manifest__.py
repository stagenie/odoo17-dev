{
    'name': 'Ticket de Vente  ',
    'version': '17.0.1.0',
    'sequence': 1,
    'category': 'Sales',
    'summary': 'Ce module va permettre d\'imprimer un Ticket de vente du le module Vente ',
    'description': "Ce module va permettre d\'imprimer un Ticket de vente du le module Vente,...  ",
    "author" : "ADICOPS",
    "email": 'info@adicops.com',
    
    "website":'https://adicops.com/',
    'license': "AGPL-3", 
    'depends': [
        'base',
        'sale',
    ], 
    "data":  [

            'reports/sale_ticket_report.xml',
        'reports/report_templates.xml',
         
    
        ],
    'demo': [],
    'test': [],
    'qweb': [],    
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
