{
    'name': 'ORA Caisse Extend',
    'version': '17.0.0.1',
    'description': 'ORA Caisse Extend',
    'author': 'ORA Formed',
    'license': 'LGPL-3',
    'depends': [
        'caisse','account_bnk_stm_cash_box',
    ],
    'data': [
        'vue/caisse_cashbox.xml',
        'vue/res_currency.xml',
        'wizards/account_payment_register.xml',
    ],
    'auto_install': False,
    'application': False,
}