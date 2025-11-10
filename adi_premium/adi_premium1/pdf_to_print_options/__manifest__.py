# -*- coding: utf-8 -*-
{
    'name': 'ADI PDF Report Options',
    'summary': """Options d'impression PDF avancées pour rapports Odoo""",
    'description': """
        Ce module ajoute un wizard de sélection d'impression avec trois options:
        1. Imprimer - Envoie directement à l'imprimante
        2. Télécharger - Télécharge le rapport en PDF
        3. Ouvrir - Ouvre le rapport dans un nouvel onglet
    """,
    'version': '17.0.1.0.0',
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'category': 'Technical',
    'depends': ['base', 'web'],
    'data': [
        'views/ir_actions_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            # ✅ Chemins exacts et explicites (pas de **)
            'adi_pdf_report_options/static/src/js/PdfOptionsModal.js',
            'adi_pdf_report_options/static/src/js/qwebactionmanager.js',
            'adi_pdf_report_options/static/src/xml/report_pdf_options.xml',
        ]
    }
}
