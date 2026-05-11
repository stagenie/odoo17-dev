# -*- coding: utf-8 -*-
{
    'name': 'Treasury Operation Closing Fix',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Treasury',
    'summary': "Rattache toute opération de caisse à la clôture en cours, "
               "indépendamment de sa date d'ouverture",
    'description': """
Treasury Operation Closing Fix
==============================

Corrige un bug qui empêche d'enregistrer une opération de caisse (paiement,
dépense ADI, etc.) lorsque la clôture en cours pour la caisse a été ouverte
un jour antérieur.

Symptôme
--------
À la validation d'une dépense liée à une caisse, l'erreur suivante apparaît :

    ❌ Impossible de créer une nouvelle clôture !
    Il existe déjà une clôture en cours pour la caisse '<X>' :
    📋 CLO/.../YYYY-MM-DD/NN (État : Brouillon) du YYYY-MM-DD

Cause
-----
Le module `adi_treasury` cherche la clôture courante en filtrant sur
`closing_date = aujourd'hui` (cf. treasury_cash_operation.py:261, 314, 554).
Si la clôture en cours a été ouverte un autre jour, la recherche échoue
et le code tente de créer une *nouvelle* clôture — bloquée par la
contrainte d'unicité `_check_unique_pending_closing_per_cash` (qui, elle,
ne filtre pas par date).

Correctif
---------
Le module surcharge :

* `treasury.cash.operation.create()`
* `treasury.cash.operation.create_manual_operation_with_closing()`
* `treasury.cash.operation._check_operation_closing()` (constraint)

…pour rechercher la clôture en cours **sans** filtre de date. Toute
clôture en état `draft` ou `confirmed` pour la caisse est réutilisée,
quelle que soit sa date d'ouverture — cohérent avec la règle métier
"une seule clôture en cours par caisse" déjà imposée par la contrainte
d'unicité.

Conséquence : une clôture ouverte le 06/05 reste la session active de
la caisse jusqu'à sa validation (ou annulation). Toutes les opérations
créées entre temps (paiements, dépenses…) s'y rattachent.
    """,
    'author': 'ADICOPS',
    'website': 'https://www.adicops.com',
    'license': 'LGPL-3',
    'depends': [
        'adi_treasury',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
