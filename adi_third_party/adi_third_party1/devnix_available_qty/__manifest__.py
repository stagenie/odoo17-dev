# -*- coding: utf-8 -*-
{
    'name': "Available Quantity Sale/Purchase ",
    'summary': """
        the module adds Available Qty Field To Sale Order Line and Purchase Order Line
       """,
    'description': """the module adds Available Qty Field To Sale Order Line and Purchase Order Line
    """,
    "version": "17.0",
    "author": "Devnix Solutions",
    "website": "https://devnix.solutions",
    "support": "info@devnix.solutions",
    'version': '0.4',
    'depends': ['base', 'sale_management', 'purchase', 'stock'],
    "images": ['static/description/Banner.png'],
    'data': [
        'views/sale_order.xml',
        'views/purchase_order.xml',
    ],
    "license": "OPL-1"
}
