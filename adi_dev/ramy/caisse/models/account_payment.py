# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class account_payment(models.Model):
    _inherit = 'account.payment'
    
    def get_facture_courante(self):
        if self.env.context.get('payment_from_wizard', []): 
            return self.env['account.move'].browse([])
        act_id = self.env.context.get('active_id', []) #get current active invoice
        act_id = self.env['account.move'].browse(act_id)
        return act_id


    
    caisse = fields.Many2one('caisse', copy=False)
    type_methode=fields.Char(compute='set_type')

    @api.depends('journal_id')
    def set_type(self):
        self.type_methode= self.journal_id.type

    def article_facture(self, act_id):
        articles = [line.product_id.name for line in act_id.invoice_line_ids]
        return articles

    
    def create_caisse_ligne(self, act_id):
        if self.caisse:
            articles = self.article_facture(act_id)
            if self.partner_type == 'customer':
                vals= {
                    'payment_id': self.id,
                    'res_partner_id':self.partner_id.id,
                    'date':self.date, 
                    'name' :self.name, 
                    'montant':self.amount, 
                    'ligne_id' : self.caisse.id,
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.context.get('refund',False) and self.env.ref('caisse.fund_motif_customer_refund').id\
                        or self.env.ref('caisse.fund_motif_customer_paiement').id,
                    'type_trans': True, 
                    'payment': True, 
                    'type_entre' : self.env.context.get('refund',False) and 'depense' or 'recette',
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
                if self.env.context.get('refund',False):
                    del vals['ligne_id']
                    vals.update({'d_id' : self.caisse.id})
                return vals 
            
            elif self.partner_type == 'supplier':
                if self.caisse.total<self.amount and not self.env.context.get('refund',False):
                    raise ValidationError("Le montant de cette transaction est supérieur au solde de la caisse")
                vals= {
                    'payment_id': self.id,
                    'res_partner_id':self.partner_id.id,
                    'date':self.date, 
                    'name' :self.name, 
                    'montant_d':self.amount, 
                    'montant':self.amount,
                    'type_entre' : self.env.context.get('refund',False) and 'recette' or 'depense',
                    'd_id' : self.caisse.id,
                    'caisse_parent' : self.caisse.id,
                    'motif_id' : self.env.context.get('refund',False) and self.env.ref('caisse.fund_motif_supplier_refund').id\
                        or self.env.ref('caisse.fund_motif_supplier_paiement').id,
                    'type_trans': True,
                    'payment': True,
                    'type_payment': self.type_methode, 
                    'designation': ','.join(articles)}
                if self.env.context.get('refund',False):
                    del vals['d_id']
                    vals.update({'ligne_id' : self.caisse.id})
                return vals
   
    def action_post(self):
        res = super(account_payment,self).action_post()
        # ajout du calcul dans la caisse
        fact_cour = self.get_facture_courante()
        #if self.type_methode=='cash':
        ligne= self.env['ligne.caisse']  
        caisse_ligne_dict = self.create_caisse_ligne(fact_cour)   
        ligne.create(caisse_ligne_dict)   
        return res
    
    def action_draft(self):
        if self.caisse:
            # suppmier la ligne dans la caisse dans la mise en brouillon du paiement 
            if self.caisse.state == "open":
                for line in self.caisse.caisse_line_ids:
                    if line.payment_id == self.payment_id:
                        line.payment = False
                        line.unlink()
            # Empêcher la mise en brouillon du paiement si la caisse est fermé
            elif self.caisse.state == "confirm":
                raise ValidationError("Cette action ne peut être effectué ! La caisse est fermé")
        return super(account_payment,self).action_draft()
    
    def action_cancel(self):
        if self.caisse:
            # suppmier la ligne dans la caisse dans l'annulation du paiement 
            if self.caisse.state == "open":
                for line in self.caisse.caisse_line_ids:
                    if line.payment_id == self.payment_id:
                        line.payment = False
                        line.unlink()
            # Empêcher l'annulation du paiement si la caisse est fermé
            elif self.caisse.state == "confirm":
                for line in self.caisse.caisse_line_ids:
                    if line.payment_id == self.payment_id:
                        raise ValidationError("Cette action ne peut être effectué ! La caisse est fermé")
        return super(account_payment,self).action_cancel()

