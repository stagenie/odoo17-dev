# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
        
    bank_sending = fields.Many2one('res.partner.bank', string='Compte Bancaire')
    def _prepare_invoice(self):
        invoice_vals=super(PurchaseOrder,self)._prepare_invoice()
        invoice_vals['bank_sending']=self.bank_sending.id                        
        return  invoice_vals
    
 
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    # part number qui sera sélectionné par l'utilisateur 
    item = fields.Char("Item")
    partnumber = fields.Char(
        related="product_id.partnumber",
        string="Part Number",
        store=True)