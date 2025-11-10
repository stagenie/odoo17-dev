{
    'name': 'Todo App',
    'version': '17.0.1.0',
    'sequence': 1,
    'category': 'Productivity',
    'summary': 'Simple todo management application',
    'description': 'A simple todo application to manage your daily tasks',
    'author': 'ADI Dev',
    'email': 'dev@adicops.com',
    'website': 'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/todo_views.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
