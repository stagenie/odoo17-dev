{
    "name": "ADI GECAFLE Receptions",
    "version": "17.0.1.0.0",
    "author": "ACICOPS",
    "website": "https://adicops-dz.com/",
    "license": "AGPL-3",
    "category": "Stock",
    "depends": ["adi_gecafle_base_stock", "mail",'account'],
    "data": [
        'security/ir.model.access.csv',
        "views/adi_gecafle_receptions_views.xml",
        'views/account_payment_views.xml',
        'views/reception_product_details.xml',
        'views/stock.xml',
        'views/destockage_views.xml',
        'views/gecafle_emballage_prod.xml',
        'reports/report_bon_reception.xml',
        'reports/report_stock_list.xml',
        #"views/adi_gecafle_destockage_views.xml"
    ],
    "installable": True,
    "application": True,
}
