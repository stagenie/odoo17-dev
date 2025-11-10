
# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    
    def default_caisse(self):
        # caisse =self.env['caisse'].browse(self.env.context.get('active_id',False)) 
        # if caisse == None:
        caisse = self.env['caisse'].search([
            ('user_id', '=', self.env.user.id),
            ('state', '=', "open"),
            ],limit=1)
        return caisse.id
    
    def get_facture_courante(self):
        # act_id = self.env.context.get('active_id', []) #get current active invoice
        # act_id = self.env['account.move'].browse(act_id)
        # if act_id == None:
        act_id = self.line_ids[0].move_id
        return act_id

    
    caisse = fields.Many2one('caisse', default=default_caisse, readonly=True)
    type_methode=fields.Char(compute='set_type')

    @api.depends('journal_id')
    def set_type(self):
        self.type_methode= self.journal_id.type

    def article_facture(self, act_id):
        articles = [line.product_id.name for line in act_id.invoice_line_ids if line.product_id and line.product_id.name]
        
        return articles

    
    def create_caisse_ligne(self, act_id):
        if self.caisse:
            articles = self.article_facture(act_id)
            if act_id.move_type == 'out_invoice':
                return {
                    'date':self.payment_date, 
                    'name' :"Paiement/" + act_id.name, 
                    'montant':self.amount, 
                    'ligne_id' : self.caisse.id,
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.ref('caisse.fund_motif_customer_paiement').id,
                    'type_trans': True, 
                    'type_entre' : 'recette',
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
            if act_id.move_type == 'in_invoice':
                if self.caisse.total<self.amount:
                    raise UserError("Le montant de cette transaction est supérieur au solde de la caisse")
                return {
                    'date':self.payment_date, 
                    'name' :"Paiement/" + act_id.name, 
                    'montant_d':self.amount, 
                    'montant':self.amount,
                    'd_id' : self.caisse.id,
                    'type_entre' : 'depense',
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.ref('caisse.fund_motif_supplier_paiement').id,
                    'type_trans': True, 
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
        
    def action_create_payments(self):
        fact_cour = self.get_facture_courante()
        #if self.type_methode=='cash':
        ligne= self.env['ligne.caisse']  
        caisse_ligne_dict = self.create_caisse_ligne(fact_cour)  
        ligne.create(caisse_ligne_dict)  
        return super(AccountPaymentRegister,self).action_create_payments()

