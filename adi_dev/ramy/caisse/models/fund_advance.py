# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError, UserError
import time


class FundAdvance(models.Model):
    _name = 'fund.advance'
    _description = 'Demande avance'
    _order = "create_date desc"

    name = fields.Text(string='Référence', copy=False)
    res_partner_id = fields.Many2one('res.partner', string='Demandeur', copy=False)
    date = fields.Date(string="Date", default=time.strftime('%Y-%m-%d'), copy=False)
    caisse = fields.Many2one('caisse','Caisse', )
    def fonct(self):
        return self.env.user.company_id.id
    company_id = fields.Many2one('res.company', 'Company', default=fonct,readonly=True)
    currency_id = fields.Many2one('res.currency',related="company_id.currency_id",readonly=True)
    amount = fields.Monetary(string="Montant",)
    designation = fields.Char('Mémo')
    total = fields.Monetary(string="Dépenses Justifiées",compute="compute_total", store=True)
    ecart = fields.Monetary(string="Écart",compute="compute_ecart", store=True)
    ecart_show = fields.Monetary(string="Écart",compute="compute_ecart", store=True)
    complement = fields.Monetary(string="Complement avance",compute="compute_ecart", store=True)
    retour = fields.Monetary(string="Retour avance",compute="compute_ecart", store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'En cours'),
        ('reproched', 'Rapproché'),
        ('close', 'Cloturé'),
    ], default='draft', copy=False)
    

    fund_expense_ids = fields.One2many(
        string='Dépenses',
        comodel_name='fund.expense.line',
        inverse_name='fund_advance_id',
        copy=False,)
    advance_gap_ids = fields.One2many(
        string='Gestio écart d\'avance',
        comodel_name='advance.gap',
        inverse_name='fund_advance_id',
        copy=False,)
    
    @api.model
    def create(self, vals):
        advance = super(FundAdvance, self).create(vals)
        if not advance['name']:
            advance['name'] = self.env['ir.sequence'].next_by_code('fund.advance')
        return advance

    @api.depends('total','amount')
    def compute_ecart(self):
        for advance in self:
            advance.ecart = advance.amount-advance.total
            if advance.state in ('draft','confirm') and not self._context.get('recompute_ecart',False):
                advance.ecart_show = advance.amount
                advance.complement, advance.retour = 0, 0
            elif self._context.get('recompute_ecart',False):
                advance.ecart_show =0
                compare_ecart = advance.amount-advance.total
                if compare_ecart>0:
                    advance.complement==0
                    advance.retour=compare_ecart
                elif compare_ecart<0:
                    advance.complement= abs(compare_ecart)
                    advance.retour=0
                else:
                    advance.complement, advance.retour = 0, 0
    
    @api.depends('fund_expense_ids.amount')
    def compute_total(self):
        for advance in self:
            total = 0
            for line in advance.fund_expense_ids:
                total += line.amount
            advance.total = total

    def action_confirm(self):
        validate = True
        if self.amount <= 0:
            raise ValidationError("Attention : Le montant doit être superieure à zéro")
        elif self.amount > self.caisse.total:
            raise ValidationError("Veuillez SVP vérifier le montant demandé ! Il est supérieur au solde de la caisse." )
        if validate == True:
            fund_motif = self.env.ref('caisse.fund_motif_3')
            self.state = 'confirm'
            # création de ligne de dépende dans la caisse
            caisse_line = self.env['ligne.caisse'].create({
                'date':self.date,
                'name' :self.name,
                'designation' :self.designation,                            
                'montant':self.amount,   
                'montant_d':self.amount,   
                'd_id' : self.caisse.id,
                'caisse_parent' : self.caisse.id,
                'res_partner_id' : self.res_partner_id.id,
                'type_entre' : 'depense',
                'montant_signe' : self.amount,
                'type_caisse' : self.caisse.type_caisse.id,
                'motif_id' : fund_motif.id,
                'motif_family_id' : fund_motif.fund_motif_family_id.id,
                "fund_advance_id": self.id,
                "advance": True
                })
            
            # caisse_line = self.env['account.bank.statement.line'].create({
            #     'date': self.date,
            #     'statement_id': caisse.id,
            #     'journal_id': self.account_journal_id.id,
            #     'partner_id': self.res_partner_id.id,
            #     'type': 'out',
            #     'fund_motif_family_id': fund_motif.fund_motif_family_id.id,
            #     'amount': self.amount,
            #     'payment_ref': self.name,
            #     "fund_motif_id": fund_motif.id,
            #     "fund_advance_id": self.id,
            #     "advance": True
            # })

            # self.caisse = caisse.id
            return caisse_line

    def action_confirm_cancel(self):
        if self.caisse.state != "open":
            raise ValidationError("Désolé! lannulaion de l'avance est impossible, car la caisse n'est plus ouverte")
        else:
            caisse_lines = self.env['ligne.caisse'].search([("fund_advance_id", "=", self.id)],)
            for line in caisse_lines:
                line.advance = False
                line.unlink()
        if self.fund_expense_ids:
            for line in self.fund_expense_ids:
                line.unlink()
        self.state = 'draft'

    def _create_analytic_lines(self):
        for line in self.fund_expense_ids:
            line._create_analytic_line()
            
    def action_canceled(self):
        if self.fund_expense_ids:
            raise ValidationError("Vous devez d'abord supprimer les lignes de dépense.")
        open_caisse = self.env['caisse'].search([('type_caisse','=',self.caisse.type_caisse.name),
                                                 ("state", "=", 'open')],limit=1)
        if not open_caisse:
            raise ValidationError("Aucune caisse n'est ouverte pour cet type")
            
        tran = self.env['ligne.caisse'].create({
            'date':self.date,
            'name' :self.name,          
            # 'designation' :self.memo,
            # 'type_payment': self.type_payment,                         
            'montant':self.amount, 
            'ligne_id' : open_caisse.id,
            'caisse_parent' : open_caisse.id,
            'type_entre' : 'recette',
            'montant_signe' : self.amount,
            'type_caisse' : open_caisse.type_caisse.id,
            'motif_id' : self.env.ref('caisse.fund_motif_cancel_avance').id,
            'motif_family_id' : self.env.ref('caisse.motif_family_cancel_avance').id,
            'res_partner_id' : self.res_partner_id.id,
            # 'demandeur_id' : self.demandeur_id.id,
            # 'collaborator_id' : self.collaborator_id.id,
            # 'ordonator_id' : self.ordonator_id.id,
            # 'collaborator_ext_id' : self.collaborator_ext_id.id,
            # 'beneficiary_id' : self.beneficiary_id.id,
            # 'structure_id' : self.structure_id.id,
            })
        self.state='close'
            
        
        
    def action_repproched(self):
        self.with_context(recompute_ecart=True).compute_ecart()
        if not self.fund_expense_ids:
            raise ValidationError("Vous devez d'abord renseigner les lignes de dépense, sinon le rapprochement ne s'effectue pas.")
        if self.ecart == 0:
            self._create_analytic_lines()
            self.state = 'reproched'
            # comptabiliser les lignes de dépenses
        else:
            compose_form = self.env.ref('caisse.fund_advance_repproche_wizard_view', raise_if_not_found=False)
            self.ensure_one()
            return {
            'name': _("Imputer l'écart"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fund.advance.repproche.wizard',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            # 'context': ctx,
            }
        
        for line in self.fund_expense_ids:
            if line.fund_motif_id == self.env.ref('caisse.fund_motif_supplier_paiement'):
                account_payment = self.env['account.payment'].create({
                    # 'ref':self.ref,
                    'date':line.date,
                    'caisse':self.caisse.id,
                    'amount':line.amount,
                    'payment_type':'outbound',
                    'partner_id': line.res_partner_id.id,
                    'destination_account_id': line.res_partner_id.property_account_payable_id.id,
                    'journal_id': self.env['account.move']._search_default_journal(('', 'cash')).id,
                    # 'is_internal_transfer': self.is_internal_transfer,
                    'partner_type': 'supplier',
                    'company_id': self.company_id.id,
                    })
                account_payment.with_context(payment_from_wizard=True).action_post()


    def action_repproched_cancel(self):
        self.state = 'confirm'
    
class FundExpenseLine(models.Model):
    _name = 'fund.expense.line'
    _description = "Dépenses de l'avance"

    # def default_motif(self):
    #     return self.env.ref('caisse.fund_motif_3')
    # def default_analytique_account(self):
    #     return self.env.ref('caisse.fund_motif_3').account_analytic_account_id
    fund_advance_id = fields.Many2one(string='Avance',comodel_name='fund.advance',ondelete='cascade',)
    res_partner_id = fields.Many2one('res.partner', string='Partenaire')
    collaborator_id = fields.Many2one('hr.employee', string='Collaborateur',)
    ordonator_id = fields.Many2one('res.partner', string='Ordonnateur',)
    demandeur_id = fields.Many2one('res.partner', string='Demandeur',)
    fund_motif_id = fields.Many2one('fund.motif',string='Motif', required=True,)
    date = fields.Date(string="Date", copy=False)
    currency_id = fields.Many2one('res.currency',related="fund_advance_id.currency_id",readonly=True)
    account_analytic_id = fields.Many2one(string='Axe analytique',comodel_name='account.analytic.account')
    amount = fields.Monetary(string="Montant",)
    attachment = fields.Binary('Pièce jointe', help="Allowed formats: jpg, pdf, png. Maximum allowed size: 4MB.")
    attachment_filename = fields.Char()


    # @api.onchange('date')
    # def _onchange_date(self):
    #     for rec in self:
    #         if rec.date:
    #             if rec.fund_advance_id.caisse.type_c == 'daily' and rec.date != rec.fund_advance_id.caisse.date:
    #                 raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
    #             elif rec.fund_advance_id.caisse.type_c != 'daily' and rec.date.month != int(rec.fund_advance_id.caisse.date.month):
    #                 raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
                
    @api.onchange('fund_motif_id')
    def _onchange_fund_motif_id(self):
        if self.fund_motif_id:
            self.account_analytic_id  = self.fund_motif_id.account_analytic_account_id
        else:
            self.account_analytic_id = False

    def _create_analytic_line(self):
        for expense in self:
            account_analytic_id = expense.account_analytic_id
            account_analytic_line=self.env['account.analytic.line'].create({
                'name': expense.account_analytic_id.name,
                'date': expense.date,
                'account_id': account_analytic_id.id,
                'group_id': account_analytic_id.group_id,
                'unit_amount': 1,
                'amount': expense.amount,
                # 'general_account_id': expense.account_id.id,
                'ref': expense.id,
                'user_id': self._uid,
                'partner_id': expense.res_partner_id.id,
                'company_id': expense.fund_advance_id.company_id.id or self.env.company.id,
            })
        return account_analytic_line

class AdvanceGap(models.Model):
    _name = 'advance.gap'
    _description = "Gestion écart d'avance"

    fund_advance_id = fields.Many2one(string='Avance',comodel_name='fund.advance',ondelete='cascade',)
    fund_motif_id = fields.Many2one('fund.motif',string='Motif', required=True, )
    date = fields.Date(string="Date", copy=False)
    currency_id = fields.Many2one('res.currency',related="fund_advance_id.currency_id",readonly=True)
    amount = fields.Monetary(string="Montant",)
    caisse = fields.Many2one('caisse', string='Caisse ', )
