{
    'name': 'Adicops Gestion des dépenses ',
    'version': '17.0.1.0',
    'sequence': 1,
    'category': 'Sales',
    'summary': 'Ce module va permettre  gérer les dépenses de l’entreprise ',
    'description': "Ce module va permettre gérer les dépenses de l’entreprise",
    "author": "ADICOPS",
    "email": 'info@adicops.com',

    "website": 'https://adicops.com/',
    'license': "AGPL-3",
    'depends': [
        'base',
        'contacts',

    ],
    "data": [
        'security/ir.model.access.csv',
        'security/expenses_security.xml',
        'views/depense_views.xml',
        'views/depenses_categ.xml',
        'views/res_user.xml',

    ],
    'demo': [],
    'test': [],
    'qweb': [],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
