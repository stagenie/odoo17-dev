# -*- coding: utf-8 -*-
{
    'name': 'ADI - Situation Générale',
    'version': '17.0.1.0.0',
    'sequence': 1,
    'category': 'Accounting',
    'summary': "Tableau de bord Balance & Bénéfice sur période, avec impression PDF A4",
    'description': """
ADI - Situation Générale
========================

Application autonome présentant à un instant donné, sur une période
configurable :

* **Balance** = Trésorerie + Valeur Stock + Créances Clients − Dettes
  Fournisseurs
* **Bénéfice** = Marge Brute (factures clients) − Total Frais (dépenses)

Vue plein écran avec gros chiffres et impression PDF A4 portrait.

Périodes prédéfinies (Aujourd'hui / Cette Semaine / Ce Mois / Mois
Précédent / Ce Trimestre / Cette Année / Année Précédente / Personnalisée)
ou sélection libre des dates de début et fin.

Sources de données :
  - Trésorerie  : adi_treasury (treasury.cash.current_balance)
  - Stock       : stock_account (stock.valuation.layer)
  - Créances    : account.move.line (account_type='asset_receivable')
  - Dettes      : account.move.line (account_type='liability_payable')
  - Marge       : adi_invoice_margin (account.move.margin)
  - Frais       : adi_expenses_treasury (depenses.depense.montant)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
    'depends': [
        'account',
        'stock_account',
        'adi_treasury',
        'adi_invoice_margin',
        'adi_expenses_treasury',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/general_situation_views.xml',
        'reports/general_situation_report.xml',
    ],
    'images': ['static/description/icon.png'],
}
