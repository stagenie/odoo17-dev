# -*- coding: utf-8 -*-
{
    'name': 'General Situation - Cash Freshness Breakdown',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': "Décomposition solde caisse (clôturé / mouvements en cours) "
               "et indicateur de fraîcheur",
    'description': """
General Situation Freshness Fix
================================

Étend `general.situation` pour rendre lisible la part **vérifiée** du
solde de chaque caisse vs la part **théorique** (mouvements postés
depuis la dernière clôture validée mais non encore comptés).

Ajouts par caisse dans le détail :
- **Solde clôturé** : `balance_end_real` de la dernière clôture validée
- **Mouvements en cours** : delta des opérations postées depuis
- **Solde théorique** : somme des deux (= ancien champ `balance`)
- **Date dernière clôture** + **Jours depuis** + indicateur de fraîcheur
  (vert ≤ 7 j, orange ≤ 30 j, rouge > 30 j, gris si jamais clôturée)

La formule `balance_net` reste identique (utilise le solde théorique) ;
ce module ajoute uniquement de la transparence sur la composition.
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'adi_general_situation',
        'adi_treasury',
    ],
    'data': [
        'views/general_situation_views.xml',
        'reports/general_situation_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
