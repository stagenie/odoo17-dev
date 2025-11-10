from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
from datetime import date


class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'


    subtotal_cheque = fields.Float('Total Cheque',compute="compute_subtotal_cheque")
    subtotal_espece = fields.Float('Total Espece',compute="compute_subtotal_espece")
    subtotal_tpe = fields.Float('Total TPE',compute="compute_subtotal_tpe")
    total_general = fields.Float('Total', compute="compute_total_general")
    cashbox_lines_cheque_ids = fields.One2many('account.cashbox.line', 'cashbox_cheque_id', string='Cheque')
    cashbox_lines_tpe_ids = fields.One2many('account.cashbox.line', 'cashbox_tpe_id', string='TPE')

    
    @api.depends('cashbox_lines_cheque_ids','cashbox_lines_cheque_ids.cheq_tpe_val')
    def compute_subtotal_cheque(self):
        for rec in self:
            val = 0.0
            for line in rec.cashbox_lines_cheque_ids:
                val += line.cheq_tpe_val
            rec.subtotal_cheque = val 

    @api.depends('cashbox_lines_tpe_ids','cashbox_lines_tpe_ids.cheq_tpe_val')
    def compute_subtotal_tpe(self):
        for rec in self:
            val = 0.0
            for line in rec.cashbox_lines_tpe_ids:
                val += line.cheq_tpe_val
            rec.subtotal_tpe = val 

    @api.depends('cashbox_lines_coin_ids','cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number')
    def compute_subtotal_espece(self):
        for rec in self:
            val = 0.0
            for line in rec.cashbox_lines_coin_ids:
                val += line.subtotal
            rec.subtotal_espece = val 

            
    
    @api.depends('cashbox_lines_coin_ids','cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number', 'cashbox_lines_tpe_ids','cashbox_lines_cheque_ids','cashbox_lines_tpe_ids.cheq_tpe_val','cashbox_lines_cheque_ids','cashbox_lines_cheque_ids.cheq_tpe_val')
    def compute_total_general(self):
        for rec in self:
            val = 0.0
            for line_ in rec.cashbox_lines_cheque_ids:
                val += line_.cheq_tpe_val
            
            for line__ in rec.cashbox_lines_tpe_ids:
                val += line__.cheq_tpe_val
            
            for line___ in rec.cashbox_lines_coin_ids:
                val += line___.subtotal
            print('valavala aizb')
            print(val)
            rec.total_general = val

    @api.depends('cashbox_lines_ids', 'cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number','subtotal_espece', 'subtotal_tpe','subtotal_cheque')
    def _compute_total(self):
        for cashbox in self:
            # cashbox.total = sum([line.subtotal for line in cashbox.cashbox_lines_ids])
            res = super(AccountBankStmtCashWizard,self)._compute_total()
            cashbox.total += cashbox.subtotal_tpe + cashbox.subtotal_cheque


class AccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'


    partner_id = fields.Many2one("res.partner","Client")
    piece_num = fields.Char('Piéce')
    bank_id = fields.Many2one('res.bank',"Banque")
    cheq_tpe_val = fields.Float("Valeur")
    coin_value = fields.Float(string='Coin/Bill Value', required=False, digits=0)
    cashbox_cheque_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox Cjeque")
    cashbox_tpe_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox TPE")




