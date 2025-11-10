from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import time

class FundadvanceRepprocheWizard(models.TransientModel):
    _name = "fund.advance.repproche.wizard"
    _description = "Rapprocher une avance"

    def default_advance(self):
        return self.env['fund.advance'].browse(self.env.context.get('active_id',False)).id

    def default_journal(self):
        return self.env['fund.advance'].browse(self.env.context.get('active_id',False)).account_journal_id.id

    def default_caisse(self):
        advance =self.env['fund.advance'].browse(self.env.context.get('active_id',False)) 
        if advance.caisse.state == 'open':
            return advance.caisse.id
        else:
            type_caisse = advance.caisse.type_caisse
            caisse = self.env["caisse"].search([("state", "=", "open"),("type_caisse", "=", type_caisse.id)], limit=1)
            if caisse:
                return caisse.id

    name = fields.Char(string='Méssage', compute="compute_name", readonly=1) 
    advance_id = fields.Many2one(string='Avance',comodel_name='fund.advance',default=default_advance)
    date = fields.Date(string="Date", default=time.strftime('%Y-%m-%d'), copy=False)
    caisse = fields.Many2one('caisse', string='Caisse ', default=default_caisse)
    
    @api.depends('advance_id')
    def compute_name(self):
        for record in self:
            if record.advance_id.ecart < 0:
                record.name = "Le montant des dépenses est supérieur à celui de l'avance ! Veuillez imputer l'ecart sur un relevé sinon le rapprochement ne s'effectue pas." 
            elif record.advance_id.ecart > 0:
                record.name = "Le montant des dépenses est inférieur à celui de l'avance ! Veuillez imputer l'ecart sur un relevé sinon le rapprochement ne s'effectue pas."
    def action_validate(self):
        if sum(self.advance_id.fund_expense_ids.mapped('amount'))- self.advance_id.amount>self.caisse.total:
            raise ValidationError("Le montant retour avance est supérieur au solde théorique de la caisse !")
            
        type_trans = 'in'
        fund_motif = False
        if self.advance_id.ecart < 0:
            type_trans = 'out'
            fund_motif = self.env.ref('caisse.fund_motif_4')
        elif self.advance_id.ecart > 0:
            fund_motif = self.env.ref('caisse.fund_motif_5')
        #création de la ligne d'écart dans la caisse (relevé) 
        if type_trans == 'in':
            # Création de la ligne d'écart recette dans caisse
            caisse_line = self.env['ligne.caisse'].create({
                'date':self.date,
                'name' :self.advance_id.name,
                'designation' :self.advance_id.designation,                            
                'montant':self.advance_id.ecart,   
                'ligne_id' : self.caisse.id,
                'caisse_parent' : self.caisse.id,
                'type_entre' : 'recette',
                'montant_signe' : self.advance_id.ecart,
                'type_caisse' : self.caisse.type_caisse.id,
                'motif_id' : fund_motif.id,
                "fund_advance_id": self.advance_id.id,
                "advance": True
                })
        else:
            # Création de la ligne d'écart dépense dans caisse
            caisse_line = self.env['ligne.caisse'].create({
                'date':self.date,
                'name' :self.advance_id.name,
                'designation' :self.advance_id.designation,                            
                'montant':abs(self.advance_id.ecart),   
                'montant_d':abs(self.advance_id.ecart),   
                'd_id' : self.caisse.id,
                'caisse_parent' : self.caisse.id,
                'type_entre' : 'depense',
                'montant_signe' : -self.advance_id.ecart,
                'type_caisse' : self.caisse.type_caisse.id,
                'motif_id' : fund_motif.id,
                "fund_advance_id": self.advance_id.id,
                "advance": True
                })
        for line in self.advance_id.fund_expense_ids:
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
                    'company_id': self.advance_id.company_id.id,
                    })
                account_payment.with_context(payment_from_wizard=True).action_post()

        # account_bank_statement_line = self.env['account.bank.statement.line'].create({
        #         'date': self.date,
        #         'statement_id': self.account_bank_statement_id.id,
        #         'journal_id': self.account_journal_id.id,
        #         'partner_id': self.advance_id.res_partner_id.id,
        #         'type': type_trans,
        #         # 'fund_motif_family_id': fund_motif.fund_motif_family_id,
        #         'amount': self.advance_id.ecart,
        #         'payment_ref': self.advance_id.name,
        #         "fund_motif_id": fund_motif.id,
        #         "fund_advance_id": self.advance_id.id,
        #         "advance": True,
        #     })
        # caisse_line.fund_motif_family_id = fund_motif.fund_motif_family_id
        #création de la ligne d'écart dans le gestion d'écart d'avance 
        advance_gap_line = self.env['advance.gap'].create({
                'date': self.date,
                'amount': self.advance_id.ecart,
                "fund_motif_id": fund_motif.id,
                "fund_advance_id": self.advance_id.id,
                "caisse": self.caisse.id
            })
        self.advance_id._create_analytic_lines()
        self.advance_id.state = 'reproched'
        return True

        