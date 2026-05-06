# -*- coding: utf-8 -*-
"""Extension de `general.situation.cash.line` avec ventilation et fraîcheur.

Ajoute par caisse :
- la décomposition solde clôturé / mouvements en cours,
- la date de dernière clôture validée,
- le nombre de jours écoulés depuis,
- un sélecteur de fraîcheur (utilisé pour la décoration ligne).
"""
from odoo import api, fields, models


# Seuils en jours pour la classification de fraîcheur. Réglés sur le
# rythme de clôture standard observé (clôtures journalières) : on
# considère normal jusqu'à une semaine, à surveiller jusqu'à un mois,
# alarmant au-delà.
_FRESH_THRESHOLD = 7
_STALE_THRESHOLD = 30


class GeneralSituationCashLineFreshness(models.TransientModel):
    _inherit = 'general.situation.cash.line'

    closing_balance = fields.Monetary(
        string='Solde clôturé',
        currency_field='currency_id',
        readonly=True,
        help="Montant compté à la dernière clôture validée — partie "
             "vérifiée physiquement.",
    )
    pending_delta = fields.Monetary(
        string='Mouvements en cours',
        currency_field='currency_id',
        readonly=True,
        help="Somme algébrique (entrées − sorties) des opérations "
             "postées depuis la dernière clôture validée. Théorique : "
             "non encore comptée.",
    )
    last_closing_date = fields.Date(
        string='Dernière clôture',
        readonly=True,
    )
    days_since_closing = fields.Integer(
        string='Jours depuis clôture',
        compute='_compute_days_since_closing',
    )
    freshness = fields.Selection(
        selection=[
            ('fresh', 'À jour'),
            ('stale', 'À surveiller'),
            ('very_stale', 'Périmé'),
            ('never', 'Jamais clôturée'),
        ],
        compute='_compute_freshness',
        string='Fraîcheur',
    )

    @api.depends('last_closing_date', 'situation_id.date_to')
    def _compute_days_since_closing(self):
        """Nombre de jours entre la dernière clôture et `date_to` du parent.

        On utilise `date_to` (et non `today`) pour rester cohérent avec
        une situation calculée à une date passée.
        """
        for line in self:
            ref_date = line.situation_id.date_to or fields.Date.today()
            if line.last_closing_date:
                line.days_since_closing = (ref_date - line.last_closing_date).days
            else:
                line.days_since_closing = 0

    @api.depends('last_closing_date', 'days_since_closing')
    def _compute_freshness(self):
        for line in self:
            if not line.last_closing_date:
                line.freshness = 'never'
            elif line.days_since_closing <= _FRESH_THRESHOLD:
                line.freshness = 'fresh'
            elif line.days_since_closing <= _STALE_THRESHOLD:
                line.freshness = 'stale'
            else:
                line.freshness = 'very_stale'
