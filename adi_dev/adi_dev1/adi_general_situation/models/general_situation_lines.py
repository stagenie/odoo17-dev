# -*- coding: utf-8 -*-
"""Lignes de détail pour `general.situation`.

Permettent d'afficher le solde par caisse et la valeur de stock par
entrepôt sous forme de tableaux dans la vue formulaire et le rapport PDF.
"""
from odoo import fields, models


class GeneralSituationCashLine(models.TransientModel):
    """Solde individuel d'une caisse à la date `date_to` du parent."""

    _name = 'general.situation.cash.line'
    _description = 'Détail solde par caisse — Situation Générale'
    _order = 'balance desc, name'

    situation_id = fields.Many2one(
        'general.situation',
        string='Situation',
        required=True,
        ondelete='cascade',
    )
    cash_id = fields.Many2one(
        'treasury.cash',
        string='Caisse',
        readonly=True,
    )
    name = fields.Char(string='Nom', readonly=True)
    code = fields.Char(string='Code', readonly=True)
    balance = fields.Monetary(
        string='Solde',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='situation_id.currency_id',
        readonly=True,
    )


class GeneralSituationStockLine(models.TransientModel):
    """Valeur de stock par entrepôt à la date `date_to` du parent."""

    _name = 'general.situation.stock.line'
    _description = 'Détail valeur stock par entrepôt — Situation Générale'
    _order = 'value desc, name'

    situation_id = fields.Many2one(
        'general.situation',
        string='Situation',
        required=True,
        ondelete='cascade',
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt',
        readonly=True,
    )
    name = fields.Char(string='Nom', readonly=True)
    code = fields.Char(string='Code', readonly=True)
    value = fields.Monetary(
        string='Valeur',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='situation_id.currency_id',
        readonly=True,
    )
