# -*- coding: utf-8 -*-
"""Enrichit `_compute_cash_balance_value` avec la décomposition par caisse.

On garde le total et le solde théorique (= comportement d'origine), et
on ajoute, pour chaque ligne caisse, les champs nécessaires à
l'affichage de la fraîcheur :
- `closing_balance` : balance_end_real de la dernière clôture validée
- `pending_delta`   : entrées − sorties postées depuis cette clôture
- `last_closing_date` : date de cette clôture (ou False si jamais)

La somme `closing_balance + pending_delta` doit être égale au champ
`balance` calculé par le parent ; on ne le re-calcule pas, on
décompose simplement la même grandeur.
"""
from datetime import datetime, timedelta

from odoo import fields, models


class GeneralSituationFreshness(models.TransientModel):
    _inherit = 'general.situation'

    def _compute_cash_balance_value(self):
        """Override : enrichit chaque ligne caisse avec la ventilation.

        On délègue au parent pour le calcul du `balance` (théorique) et
        du `total`, puis on complète chaque dict avec les nouveaux
        champs. Aucune duplication de logique : on requête uniquement
        ce que le parent ne retourne pas.
        """
        total, lines = super()._compute_cash_balance_value()
        if not lines:
            return total, lines

        # date_to peut être False (vue par défaut) — on retombe sur today.
        date_to = self.date_to or fields.Date.today()
        end_of_day = datetime.combine(date_to, datetime.max.time())

        Closing = self.env['treasury.cash.closing']
        Operation = self.env['treasury.cash.operation']

        for line_vals in lines:
            cash_id = line_vals.get('cash_id')
            if not cash_id:
                # Sécurité : si une future évolution renvoyait une
                # ligne sans cash_id, on neutralise les nouveaux champs.
                line_vals.update({
                    'closing_balance': 0.0,
                    'pending_delta': line_vals.get('balance', 0.0),
                    'last_closing_date': False,
                })
                continue

            last_closing = Closing.search([
                ('cash_id', '=', cash_id),
                ('state', '=', 'validated'),
                ('closing_date', '<=', date_to),
            ], order='closing_date desc, closing_number desc', limit=1)

            if last_closing:
                closing_bal = last_closing.balance_end_real or 0.0
                ops_lower_bound = datetime.combine(
                    last_closing.closing_date, datetime.max.time(),
                ) + timedelta(seconds=1)
                ops = Operation.search([
                    ('cash_id', '=', cash_id),
                    ('state', '=', 'posted'),
                    ('date', '>=', ops_lower_bound),
                    ('date', '<=', end_of_day),
                ])
                delta = sum(
                    op.amount if op.operation_type == 'in' else -op.amount
                    for op in ops
                )
                line_vals.update({
                    'closing_balance': closing_bal,
                    'pending_delta': delta,
                    'last_closing_date': last_closing.closing_date,
                })
            else:
                # Aucune clôture validée : tout est "en cours" / théorique.
                line_vals.update({
                    'closing_balance': 0.0,
                    'pending_delta': line_vals.get('balance', 0.0),
                    'last_closing_date': False,
                })

        return total, lines
