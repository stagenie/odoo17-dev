{
    'name': 'Account Bank Statement Cashbox',
    'version': '17.0.0.1',
    'description': 'Account Bank Statement Cashbox',
    'author': 'NEKKACHE Abderrahmen',
    'license': 'LGPL-3',
    'category': 'Accounting',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'vue/accnt_bnk_stm_cashbox.xml',
    ],
    'auto_install': False,
    'application': False,
}