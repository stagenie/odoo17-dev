# -*- coding: utf-8 -*-
"""Rattache toute opération de caisse à la clôture en cours, sans filtre de date.

`adi_treasury` filtre les recherches de clôture par `closing_date = today`
(treasury_cash_operation.py:261, 314, 554). Combiné à la contrainte
`_check_unique_pending_closing_per_cash` qui interdit deux clôtures en cours
*toutes dates confondues*, ce filtre rend impossible la création d'opérations
sur une caisse dont la clôture a été ouverte un autre jour.

Ce module retire le filtre de date de ces trois points. Il ne change rien
d'autre : la création automatique d'une clôture en l'absence de toute clôture
en cours est conservée.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TreasuryCashOperation(models.Model):
    _inherit = 'treasury.cash.operation'

    @api.model_create_multi
    def create(self, vals_list):
        """Pré-attribue la clôture en cours (toute date) avant super().

        L'override d'`adi_treasury` cherche la clôture du jour et, en l'absence,
        en crée une nouvelle. En pré-renseignant `closing_id` ici, super()
        skippe sa branche de recherche/création et utilise la clôture existante.
        """
        Closing = self.env['treasury.cash.closing']
        for vals in vals_list:
            if vals.get('closing_id') or not vals.get('cash_id'):
                continue
            pending = Closing.search([
                ('cash_id', '=', vals['cash_id']),
                ('state', 'in', ['draft', 'confirmed']),
            ], limit=1)
            if pending:
                vals['closing_id'] = pending.id
        return super().create(vals_list)

    @api.constrains('closing_id', 'transfer_id')
    def _check_operation_closing(self):
        """Rattache l'opération à la clôture en cours (toute date) si manquante.

        Override total : le parent filtre par `closing_date = today`, ce qui
        ne convient pas. On reproduit la logique sans ce filtre.
        """
        Closing = self.env['treasury.cash.closing']
        for operation in self:
            if operation.transfer_id or operation.closing_id:
                continue
            if operation.state != 'posted':
                continue
            pending_closing = Closing.search([
                ('cash_id', '=', operation.cash_id.id),
                ('state', 'in', ['draft', 'confirmed']),
            ], limit=1)
            if not pending_closing:
                pending_closing = Closing.create({
                    'cash_id': operation.cash_id.id,
                    'closing_date': fields.Date.today(),
                })
            operation.closing_id = pending_closing

    @api.model
    def create_manual_operation_with_closing(self, vals):
        """Réutilise toute clôture en cours (draft|confirmed), peu importe sa date.

        Si une clôture existe déjà pour la caisse, on l'utilise sans tenter
        d'en créer une nouvelle — ce qui violerait
        `_check_unique_pending_closing_per_cash`.
        Sinon on délègue à super() qui se charge de créer la clôture du jour.
        """
        cash_id = vals.get('cash_id')
        if not cash_id:
            raise ValidationError(_("Veuillez sélectionner une caisse."))

        pending_closing = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', cash_id),
            ('state', 'in', ['draft', 'confirmed']),
        ], limit=1)

        if not pending_closing:
            return super().create_manual_operation_with_closing(vals)

        vals['closing_id'] = pending_closing.id
        operation = self.create(vals)
        if operation.state == 'posted':
            pending_closing._compute_totals()
            pending_closing._compute_closing_lines()
        return operation
