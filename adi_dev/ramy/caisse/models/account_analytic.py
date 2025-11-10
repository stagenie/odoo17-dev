# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def unlink(self):
        for motif in self:
            # suppression des lignes de caisses ouvertes
            caisse_lines = self.env['ligne.caisse'].search([("account_analytic_line_id", "=", self.id)],) 
            for line in caisse_lines:
                if line.caisse_parent.state == 'confirm':
                    raise ValidationError(('Désolé, vous ne pouvez pas supprimer les ligne analytics liées à une caisse fermé".'))
                elif line.caisse_parent.state == 'open':
                    line.account_analytic_line_id = False
                    line.unlink()
        return super(AccountAnalyticLine,self).unlink()