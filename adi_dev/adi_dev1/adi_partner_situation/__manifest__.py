# -*- coding: utf-8 -*-
{
    'name': 'Situation Partenaires',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Grand Livre Partenaires avec filtrage par vendeur',
    'description': """
Module Situation Partenaires
============================
Ce module ajoute:
- Un filtre par vendeur (utilisateur) dans le rapport PDF Grand Livre Partenaires
- Un menu dans Facturation > Situation Partenaires avec:
  * Situation Partenaire PDF (rapport avec filtre vendeur)
  * Consulter les Soldes Partenaires (affichage ecran)

Le filtrage est base sur le champ invoice_user_id des factures.
    """,
    'author': 'ADI Dev',
    'website': '',
    'depends': [
        'account',
        'accounting_pdf_reports',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_partner_ledger_user.xml',
        'wizard/partner_ledger_user_views.xml',
        'views/partner_balance_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
