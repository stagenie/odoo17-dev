# -*- coding: utf-8 -*-

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    bank_sending = fields.Many2one('res.partner.bank', string='Compte Bancaire')
    
   
    def _prepare_invoice(self):
        invoice_vals=super(SaleOrder,self)._prepare_invoice()
        invoice_vals['bank_sending']=self.bank_sending.id                        
        return  invoice_vals
    
    

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    
    item = fields.Char("Item")
    
    #partnumber = fields.Char("Part Number")
    def _prepare_invoice_line(self,**optional_values):
        invoice_vals=super(SaleOrderLine,self)._prepare_invoice_line()
        invoice_vals.update({
                              'item' : self.item
                              }
                            )                
        return  invoice_vals

    
   