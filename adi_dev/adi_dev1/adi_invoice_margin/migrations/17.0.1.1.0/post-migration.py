# -*- coding: utf-8 -*-
"""
Migration 17.0.1.1.0 — recalcule purchase_price / margin / margin_percent
sur les lignes de factures clients existantes.

Motivation :
  La formule de `margin_percent` est passée de ratio (0.5) à valeur pourcent
  (50.0) en multipliant par 100. Comme les champs sont `store=True`,
  Odoo ne recalcule PAS automatiquement les enregistrements existants
  lors d'un `-u` quand seule la formule change. Ce script force le recompute
  pour aligner les données déjà en base.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return  # première installation : rien à recalculer

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Lignes des factures et avoirs clients
    lines = env['account.move.line'].search([
        ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
    ])
    if lines:
        # Appel direct des compute, puis flush pour persister en base.
        lines._compute_purchase_price()
        lines._compute_margin()
        lines.flush_recordset(['purchase_price', 'margin', 'margin_percent'])

    # 2) Recalcul des agrégats au niveau facture
    moves = lines.move_id
    if moves:
        moves._compute_margin()
        moves.flush_recordset(['margin', 'margin_percent'])
