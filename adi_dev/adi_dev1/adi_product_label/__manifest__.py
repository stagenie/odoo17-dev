{
    'name': 'ADI Product Label',
    'version': '17.0.1.0',
    'category': 'Inventory',
    'summary': 'Impression étiquette produit 20x40mm avec code-barres',
    'author': 'ADICOPS',
    'depends': ['product'],
    'data': [
        'report/product_label_report.xml',
        'report/product_label_template.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
