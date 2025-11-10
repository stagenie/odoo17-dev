
# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    num_piece_cheq_tpe = fields.Char("Num Piece")
    bank_id = fields.Many2one("res.bank","Banque")
    bank_type = fields.Boolean('bank_type',compute="compute_bank_type")


    @api.depends('journal_id')
    def compute_bank_type(self):
        for rec in self:
            rec.bank_type = False
            if rec.journal_id.type == "bank":
                rec.bank_type = True




    def create_caisse_ligne(self, act_id):
        if self.caisse:
            res = super(AccountPaymentRegister,self).create_caisse_ligne(act_id)
            articles = self.article_facture(act_id)
            if act_id.move_type == 'out_refund':
                return {
                    'date':self.payment_date, 
                    'name' :"Rembourcement Client/" + act_id.name, 
                    'montant':-(self.amount), 
                    'd_id' : self.caisse.id,
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.ref('caisse.fund_motif_customer_paiement').id,
                    'type_trans': True, 
                    # 'type_entre' : 'recette',
                    'type_entre' : 'depense',
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
            if act_id.move_type == 'in_refund':
                if self.caisse.total<self.amount:
                    raise UserError("Le montant de cette transaction est supérieur au solde de la caisse")
                return {
                    'date':self.payment_date, 
                    'name' :"Rembourcement Fournisseur/" + act_id.name, 
                    'montant_d':self.amount, 
                    'montant':self.amount,
                    'ligne_id' : self.caisse.id,
                    # 'type_entre' : 'depense',
                    'type_entre' : 'recette',
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.ref('caisse.fund_motif_supplier_paiement').id,
                    'type_trans': True, 
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
            return res


    def create_cashbox_line(self,move_id):
        if self.bank_type:
            if move_id.move_type in ['out_refund',"in_invoice",]:
                if self.journal_id.name == 'TPE':
                    vals = {
                        'partner_id':move_id.partner_id.id, 
                        'cheq_tpe_val':-(self.amount), 
                        'piece_num' : self.num_piece_cheq_tpe,
                        'bank_id' : self.bank_id.id,
                        'cashbox_tpe_id' : self.caisse.cashbox_caisse_end_id.id,
                        }
                    self.env['account.cashbox.line'].create(vals)
                else:
                    vals = {
                        'partner_id':move_id.partner_id.id, 
                        'cheq_tpe_val':-(self.amount), 
                        'piece_num' : self.num_piece_cheq_tpe,
                        'bank_id' : self.bank_id.id,
                        'cashbox_cheque_id' : self.caisse.cashbox_caisse_end_id.id,
                        }
                    self.env['account.cashbox.line'].create(vals)
            if move_id.move_type in ['in_refund',"out_invoice",]:
                if self.journal_id.name == 'TPE':
                    vals = {
                        'partner_id':move_id.partner_id.id, 
                        'cheq_tpe_val':(self.amount), 
                        'piece_num' : self.num_piece_cheq_tpe,
                        'bank_id' : self.bank_id.id,
                        'cashbox_tpe_id' : self.caisse.cashbox_caisse_end_id.id,
                        }
                    self.env['account.cashbox.line'].create(vals)
                else:
                    vals = {
                        'partner_id':move_id.partner_id.id, 
                        'cheq_tpe_val':(self.amount), 
                        'piece_num' : self.num_piece_cheq_tpe,
                        'bank_id' : self.bank_id.id,
                        'cashbox_cheque_id' : self.caisse.cashbox_caisse_end_id.id,
                        }
                    self.env['account.cashbox.line'].create(vals)



    def action_create_payments(self):
        fact_cour = self.get_facture_courante()
        caisse_ligne_dict = self.create_cashbox_line(fact_cour)  
        self.caisse.balance_end_real = self.caisse.cashbox_caisse_end_id.total_general
        return super(AccountPaymentRegister,self).action_create_payments()