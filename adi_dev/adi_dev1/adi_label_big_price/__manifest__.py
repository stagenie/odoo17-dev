# -*- coding: utf-8 -*-
{
    'name': 'Étiquettes Produit - Prix Agrandi',
    'version': '17.0.1.0.0',
    'category': 'Product',
    'summary': 'Agrandit le prix sur les étiquettes produit Dymo',
    'author': 'ADI',
    'depends': ['product'],
    'assets': {
        'web.report_assets_common': [
            'adi_label_big_price/static/src/scss/label_big_price.scss',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
