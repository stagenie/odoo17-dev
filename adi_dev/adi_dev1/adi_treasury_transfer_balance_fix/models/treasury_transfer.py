# -*- coding: utf-8 -*-
"""Force le recalcul du solde des deux côtés d'un transfert.

Le module d'origine `adi_treasury` ne force `_compute_current_balance`
que sur la caisse **source** dans `action_confirm` (cf. treasury_transfer.py:455).
Pour la destination, il compte sur la propagation automatique de
`@api.depends('operation_ids…')` — qui s'avère peu fiable lorsque la
nouvelle opération vient d'être créée dans la même transaction.

Résultat observé : après un transfert C1 → C2, C1 est à jour mais C2
reste sur son ancien solde tant qu'on ne provoque pas un recompute
manuel (édition, refresh complet, etc.).

Ce module ne touche pas à la logique métier ; il ajoute simplement
un appel explicite à `_compute_current_balance` sur **toutes** les
caisses et coffres impliqués, après que `super()` a posté/annulé les
opérations.
"""
from odoo import models


class TreasuryTransferBalanceFix(models.Model):
    _inherit = 'treasury.transfer'

    def _affected_balance_records(self):
        """Retourne les caisses et coffres dont le solde dépend du transfert.

        :return: tuple (caisses, coffres) — recordsets vides si non concernés.
        """
        self.ensure_one()
        caisses = self.env['treasury.cash']
        coffres = self.env['treasury.safe']
        if self.cash_from_id:
            caisses |= self.cash_from_id
        if self.cash_to_id:
            caisses |= self.cash_to_id
        if self.safe_from_id:
            coffres |= self.safe_from_id
        if self.safe_to_id:
            coffres |= self.safe_to_id
        return caisses, coffres

    def _refresh_all_balances(self):
        """Force le recompute sur toutes les caisses/coffres concernés.

        On appelle `_compute_current_balance` directement plutôt que
        `invalidate_recordset` afin que la nouvelle valeur soit posée
        immédiatement dans le store (les vues qui se rafraîchissent
        derrière voient une donnée fraîche, sans dépendre du moment
        où Odoo décide de relancer le compute).
        """
        for transfer in self:
            caisses, coffres = transfer._affected_balance_records()
            if caisses:
                caisses._compute_current_balance()
            if coffres:
                coffres._compute_current_balance()

    def action_confirm(self):
        """Confirme le transfert puis rafraîchit les soldes des deux côtés.

        On délègue d'abord à super() qui crée les opérations posted et
        contrôle le solde côté source. Ensuite, on rafraîchit aussi le
        côté destination — c'est là le correctif.
        """
        res = super().action_confirm()
        # Ne rafraîchir que les transferts effectivement passés à
        # 'confirm' (super peut avoir levé pour certains).
        confirmed = self.filtered(lambda t: t.state == 'confirm')
        confirmed._refresh_all_balances()
        return res

    def action_cancel(self):
        """Annule le transfert puis rafraîchit les soldes après suppression
        des opérations liées.

        On capture la liste des caisses/coffres impactés AVANT super()
        (les liens sont encore intacts), puis on déclenche le recompute
        après l'annulation.
        """
        # Capture des records avant que super() ne supprime les ops liées.
        impacted_per_transfer = [
            (transfer, transfer._affected_balance_records())
            for transfer in self
        ]
        res = super().action_cancel()
        for transfer, (caisses, coffres) in impacted_per_transfer:
            if transfer.state != 'cancel':
                continue
            if caisses:
                caisses._compute_current_balance()
            if coffres:
                coffres._compute_current_balance()
        return res
