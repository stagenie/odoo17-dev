# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import  UserError, ValidationError
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp
import calendar
#from odoo.tools.amount_to_text import amount_to_text_fr

class CaisseAccountPaymentWizard(models.TransientModel):
    _name = 'caisse.account.payment.wizard'

    def default_caisse(self):
        caisse =self.env['caisse'].browse(self.env.context.get('active_id',False)) 
        if caisse == None:
            caisse = self.env['caisse'].search([('user_id', '=', self.env.user.id)])
        return caisse.id

    def _get_default_partner_type(self):
        return self.env.context.get('payment_type',False)

    def _get_default_payment_type(self):
        if (self.env.context.get('payment_type',False)=='customer' and not self.env.context.get('refund',False)) or \
            (self.env.context.get('payment_type',False)=='supplier' and self.env.context.get('refund',False)):
            return 'inbound'
        else:
            return 'outbound'
        
        # return self.env.context.get('payment_type',False)=='customer' and 'inbound' or 'outbound'
    
    def _get_default_journal(self):
        # return self.env['account.move']._search_default_journal(('', 'cash'))
        return self.env['account.move']._search_default_journal()
    
    partner_type = fields.Selection([
        ('customer', 'Client'),
        ('supplier', 'Fournisseur'),
    ], default=_get_default_partner_type, string="Type de partenaire")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date = fields.Date(
        string='Date',
        required=True
    )
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                   default=_get_default_journal)
    ref = fields.Char(string='Mémo')
    caisse = fields.Many2one('caisse', string='Caisse ', default=default_caisse, readonly=True)
    amount = fields.Monetary(currency_field='currency_id', string="Montant")
    payment_type = fields.Selection([
        ('outbound', "Envoyer de l'argent"),
        ('inbound', 'Règlement'),
    ], string='Type de paiement', default=_get_default_payment_type, required=True, readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Client/Fournisseur",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Compte de destination',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)
    is_internal_transfer = fields.Boolean(string="Transfer Interne",
        readonly=False, store=True,
        compute="_compute_is_internal_transfer")
    currency_id = fields.Many2one('res.currency',
                                  string='Currency',
                                  )
    
    @api.depends('partner_id', 'destination_account_id', 'journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            is_partner_ok = payment.partner_id == payment.journal_id.company_id.partner_id
            is_account_ok = payment.destination_account_id and payment.destination_account_id == payment.journal_id.company_id.transfer_account_id
            payment.is_internal_transfer = is_partner_ok and is_account_ok
            
    @api.depends('is_internal_transfer')
    def _compute_partner_id(self):
        for pay in self:
            if pay.is_internal_transfer:
                pay.partner_id = pay.journal_id.company_id.partner_id
            elif pay.partner_id == pay.journal_id.company_id.partner_id:
                pay.partner_id = False
            else:
                pay.partner_id = pay.partner_id

    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            if rec.date:
                if rec.caisse.type_c == 'daily' and rec.date != rec.caisse.date:
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
                elif rec.caisse.type_c != 'daily' and rec.date.month != int(rec.caisse.date.month):
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))               
                  
    @api.depends('journal_id', 'partner_id','partner_type','is_internal_transfer')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        # ('internal_type', '=', 'receivable'),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        # ('internal_type', '=', 'payable'),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
                    
    def action_confirm(self):
        
        account_payment = self.env['account.payment'].create({
            'ref':self.ref,
            'date':self.date,
            'caisse':self.caisse.id,
            'amount':self.amount,
            'payment_type':self.payment_type,
            'partner_id': self.partner_id.id,
            'destination_account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'is_internal_transfer': self.is_internal_transfer,
            'partner_type': self.partner_type,
            'company_id': self.company_id.id,
            })
        account_payment.with_context(payment_from_wizard=True).action_post()