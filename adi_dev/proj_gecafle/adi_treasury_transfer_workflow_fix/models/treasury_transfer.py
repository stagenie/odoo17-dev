# -*- coding: utf-8 -*-
"""Workflow simplifié : draft → done en un seul clic.

Le module d'origine sépare le clic en deux phases (Confirm puis Done)
mais les opérations de caisse sont posted dès la phase Confirm. La
phase Done n'apportait que la traçabilité (validated_by + chatter).
On chaîne donc directement les deux pour aligner l'UX sur la réalité.

Ordre d'exécution avec les autres fix installés :
    workflow_fix.action_confirm
        super() → balance_fix.action_confirm
            super() → adi_treasury.action_confirm
                # crée les ops posted, contrôle solde, state='confirm'
            balance_fix : force _compute_current_balance des deux côtés
        workflow_fix : appelle action_done
            # state='done', validated_by, messages chatter

Si super() lève (ex. solde insuffisant), action_done n'est pas appelé
et le rollback du parent reste actif.
"""
from odoo import models


class TreasuryTransferWorkflowFix(models.Model):
    _inherit = 'treasury.transfer'

    def action_confirm(self):
        """Chaîne immédiatement vers Done après le confirm du parent.

        Pour les transferts effectivement passés à 'confirm' (super peut
        avoir levé pour certains records dans un appel multi-records),
        on enchaîne sur `action_done`. Les autres restent inchangés.
        """
        res = super().action_confirm()
        to_finalize = self.filtered(lambda t: t.state == 'confirm')
        if to_finalize:
            to_finalize.action_done()
        return res
