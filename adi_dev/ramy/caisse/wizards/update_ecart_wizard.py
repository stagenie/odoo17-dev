# -*- coding: utf-8 -*-
from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError

class UpdateEcart(models.TransientModel):
    _name = 'update.ecart'

    def default_caisse(self):
        type_caisse = self.env['caisse'].browse(self._context['active_id']).type_caisse.id
        open_caisse = self.env['caisse'].search([('type_caisse','=',type_caisse),("state", "=", 'open')])
        if not open_caisse:
            raise ValidationError("Aucune caisse n'est ouverte pour cet type")
        return open_caisse.id, 
    
    def default_amount(self):
        caisse =  self.env['caisse'].browse(self._context['active_id'])
        if self._context.get('ecart_cumule', False):
            return abs(caisse.cumul_ecart)
        else:
            return abs(caisse.end_ecart_variable)

        
    def default_motif(self):
        caisse = self.env['caisse'].browse(self._context['active_id'])
        if self._context.get('ecart_cumule', False):
            if caisse.cumul_ecart > 0:
                return 'positive_ecart'
            else:
                return 'negative_ecart'
        else:
            if caisse.end_ecart_variable > 0:
                return 'positive_ecart'
            else:
                return 'negative_ecart'
        
    caisse_id = fields.Many2one('caisse','Caisse', default=default_caisse)
    date = fields.Date('Date', required=True ,)
    name = fields.Char('Référence',)
    designation = fields.Char('Désignation')
    note = fields.Text(string='Mémo')
    motif_id =  fields.Many2one(string='Motif',comodel_name='fund.motif')
    motif = fields.Selection([('positive_ecart','Ecart positif'),
                                   ('negative_ecart','Ecart négatif'),],
                                   'Type des ecarts', 
                                   readonly=True ,
                                   default=default_motif,)
    montant = fields.Monetary('Montant', digits_compute=dp.get_precision('Account'), default=default_amount)

    
            
        
        
    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            if rec.date:
                if rec.caisse_id.type_c == 'daily' and rec.date != rec.caisse_id.date:
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
                elif rec.caisse_id.type_c != 'daily' and rec.date.month != int(rec.caisse_id.date.month):
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))                
    
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = self.env.company.currency_id
    currency_id = fields.Many2one('res.currency ' , string='Currency', default=_compute_currency )

    def action_confirm(self, test=None):
        if not self.env['res.config.settings'].search([],order='id desc', limit=1).default_get_balance_end_real:
            active_caisse = self.env['caisse'].browse(self._context['active_id'])
            open_caisse = self.env['caisse'].search([('type_caisse','=',active_caisse.type_caisse.name),("state", "=", 'open')])
            if self._context.get('ecart_cumule', False):
                caisses1 = self.env['caisse'].search([('type_caisse', '=', active_caisse.type_caisse.name),
                                                    ('state','=','confirm'),('end_ecart_variable','!=',0.0),
                                                    ('id','<=',self._context['active_id'])], order='id')
            else:
                caisses1 = active_caisse
            active_caisse.with_context(get_cumul=True)._compute_cumul_state(caisses1,open_caisse) 
            return True
        if self.montant <= 0 or self.montant >self.default_amount():
            raise ValidationError("Veuillez SVP vérifier le montant.")
        else:
            sens = ""
            if self.motif== 'negative_ecart':
                sens = 'recette'
                motif_id = self.env.ref('caisse.fund_motif_1') 
            else:
                sens = 'depense'
                motif_id = self.env.ref('caisse.fund_motif_2') 
                
            if self._context.get('ecart_cumule', False):
                active_caisse = self.env['caisse'].browse(self._context['active_id'])
                amount_proccess= self.montant
                caisses = self.env['caisse'].search([('type_caisse', '=', active_caisse.type_caisse.name),
                                                     ('state','=','confirm'),('end_ecart_variable','!=',0.0),
                                                     ('id','<=',self._context['active_id'])], order='id')

                for c in caisses:
                    montant =  amount_proccess <= abs(c.end_ecart_variable) and amount_proccess or abs(c.end_ecart_variable)
                    line = self.env['ligne.caisse'].create({
                        'date':self.date,
                        'name' :('Ecart-négatif/' if sens == 'recette' else 'Ecart-positif/') +c.name,          
                        'designation' :self.note,                        
                        'montant':montant, 
                        'ligne_id' : self.caisse_id.id if sens == 'recette' else False,
                        'd_id': self.caisse_id.id if sens != 'recette' else False,
                        'caisse_parent' : self.caisse_id.id,
                        'type_entre' : sens,
                        'montant_signe' : montant,
                        'type_caisse' : self.caisse_id.type_caisse.id,
                        'motif_id' : motif_id.id,
                        
                    })
                    if sens == 'recette':
                        # line.ligne_id =  self.caisse_id.id
                        c.write({'end_ecart_variable':c.end_ecart_variable+montant})
                    else:
                        # line.d_id = self.caisse_id.id,
                        amount = -float(montant)
                        line.montant_signe = amount
                        c.write({'end_ecart_variable':c.end_ecart_variable+amount})
                    self.caisse_id.write({'caisse_ecart_state':'with_ecart_t'})
                    
                    amount_proccess -= abs(montant)
                    if amount_proccess <=0:
                        break                 
            else:
                line = self.env['ligne.caisse'].create({
                    'date':self.date,
                    'name' :('Ecart-négatif/' if sens == 'recette' else 'Ecart-positif/') +self.caisse_id.name,        
                    'designation' :self.note,                        
                    'montant':self.montant, 
                    'ligne_id' : self.caisse_id.id if sens == 'recette' else False,
                    'd_id': self.caisse_id.id if sens != 'recette' else False,
                    'caisse_parent' : self.caisse_id.id,
                    'type_entre' : sens,
                    'montant_signe' : self.montant,
                    'type_caisse' : self.caisse_id.type_caisse.id,
                    'motif_id' : motif_id.id,
                    
                })
                updated_caisse = self.env['caisse'].browse(self._context['active_id'])
                if sens == 'recette':
                    # line.ligne_id =  self.caisse_id.id
                    updated_caisse.write({'end_ecart_variable':updated_caisse.end_ecart_variable+self.montant})
                else:
                    # line.d_id = self.caisse_id.id,
                    amount = -float(self.montant)
                    line.montant_signe = amount
                    updated_caisse.write({'end_ecart_variable':updated_caisse.end_ecart_variable+amount})

                self.caisse_id.write({'caisse_ecart_state':'with_ecart_t'})
                
                
            return True