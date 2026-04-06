{
    'name': 'Ticket de Vente Amélioré',
    'version': '17.0.1.0',
    'sequence': 2,
    'category': 'Sales',
    'summary': 'Ticket de vente compact avec numérotation des lignes',
    'description': 'Ticket de vente optimisé pour imprimante thermique 80mm avec N° de ligne, désignation compacte et texte réduit.',
    'author': 'ADICOPS',
    'email': 'info@adicops.com',
    'website': 'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': [
        'sale',
        'stock',
    ],
    'data': [
        'reports/sale_ticket_report.xml',
        'reports/report_templates.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
