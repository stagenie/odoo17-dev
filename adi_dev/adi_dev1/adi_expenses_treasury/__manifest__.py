{
    'name': 'Adicops Frais — Intégration Trésorerie',
    'version': '17.0.1.0.0',
    'sequence': 2,
    'category': 'Accounting/Treasury',
    'summary': "Lie les frais (adi_expenses) à la gestion de trésorerie (adi_treasury).",
    'description': """
Module pont entre `adi_expenses` et `adi_treasury`.

Ajoute aux frais un état (brouillon / comptabilisé / annulé), une caisse
obligatoire, un partenaire optionnel et un motif. Lors du post, une
opération de trésorerie est créée automatiquement dans la clôture en cours
de la caisse choisie.

Le module original `adi_expenses` reste inchangé : ce module l'étend
exclusivement par héritage de modèle et de vues.
""",
    'author': 'ADICOPS',
    'website': 'https://adicops.com/',
    'license': 'AGPL-3',
    'depends': [
        'mail',
        'adi_expenses',
        'adi_treasury',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/treasury_category_data.xml',
        'views/depense_views.xml',
        'wizard/depense_report_wizard_views.xml',
        'reports/depense_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
