# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import  UserError
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp
import calendar
from odoo.exceptions import ValidationError
#from odoo.tools.amount_to_text import amount_to_text_fr

class ajouter_ligne_transaction(models.TransientModel):
    _name = 'wizard.transaction'

    
    name = fields.Char('Transaction')
    memo = fields.Char('Mémo')
    complement_name = fields.Char('Mémo')
    user_id = fields.Many2one('res.users', string='Demandé par', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    date = fields.Date('Date')
    effective_date = fields.Date("Date d'effet", default=fields.Date.today())
    montant = fields.Monetary('Montant', digits_compute=dp.get_precision('Account'))
    banque = fields.Char('Banque')
    designation = fields.Char('Désignation')
    type_trans= fields.Selection([('recette', 'Recette'),
                                   ('depense','Dépense'),
                                   ('demande', 'Transfert intern'),
                                   ('avance','Avance')],
                                   'Type', required=True,default='demande')
    motif_id =  fields.Many2one(string='Motif',comodel_name='fund.motif',)
    motif_dep_id =  fields.Many2one(string='Motif',comodel_name='fund.motif',)
    motif_family_id = fields.Many2one(string='Famille motif', comodel_name='fund.motif.family',)
    res_partner_id = fields.Many2one('res.partner', string='Partenaire',)
    collaborator_id = fields.Many2one('hr.employee', string='Collaborateur',)
    ordonator_id = fields.Many2one('res.partner', string='Ordonnateur',)
    demandeur_id = fields.Many2one('res.partner', string='Demandeur',)
    collaborator_ext_id = fields.Many2one('res.partner', string='Collaborateur externe',)
    beneficiary_id = fields.Many2one('res.partner', string='Bénéficiaire',)
    structure_id = fields.Many2one('hr.department', string='Structure',)
    amount_word_num = fields.Char (string = "Montant en lettres",)

    @api.onchange('motif_id', 'motif_dep_id')
    def _compute_motif_family(self):
        for rec in self: 
            if rec.motif_id:
                rec.motif_family_id = rec .motif_id.fund_motif_family_id.id
            if rec.motif_dep_id:
                rec.motif_family_id = rec .motif_dep_id.fund_motif_family_id.id

    # montant du paiment en lettre 
    @api.onchange('montant')
    def _onchange_montant(self):
        for rec in self: 
            rec.amount_word_num = str (rec.currency_id.amount_to_text (rec.montant))

    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            if rec.date:
                if rec.caisse_recette.type_c == 'daily' and rec.date != rec.caisse_recette.date:
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
                elif rec.caisse_recette.type_c != 'daily' and rec.date.month != int(rec.caisse_recette.date.month):
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))               
                rec.effective_date=rec.date
    
    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency',default=get_currency)
    source = fields.Many2one('caisse','Source', )
    source_central = fields.Many2one('caisse','Source')
    compte_source = fields.Many2one('account.account', 'Compte Source' )
    destination = fields.Many2one('caisse','Destination')
    destination_central = fields.Many2one('caisse','Destination')
    compte_destination = fields.Many2one('account.account', 'Compte principal')
    
    compte_virement_fond = fields.Many2one('account.account', 'Compte virement de fonds' )
    type_payment = fields.Selection([('bank', 'Bank'),
                                   ('cash','Cash'),],
                                   'Type de paiement',default='cash')

    def default_caisse(self):
        return self.env.context.get('active_id', [])

    caisse_recette = fields.Many2one('caisse','Caisse', default=default_caisse)
    compte_caisse_recette = fields.Many2one('account.account','Compte caisse')
    caisse_depense = fields.Many2one('caisse','Caisse', default=default_caisse)
    compte_caisse_depense = fields.Many2one('account.account','Compte caisse')

    @api.onchange('type_trans')
    def set_caisse_source(self):
        caisses_centrales = self.env['caisse'].search([('state','=', 'open'),('type_c','=', 'mensuel')])
        for caisse in caisses_centrales:
            if self.type_trans == 'recette':
                self.source = caisse.id



    @api.onchange('source','source_central')
    def set_comp_s(self):
        if self.source_central:
            self.compte_source=self.source_central.compte_id.id
        elif self.source:       
            self.compte_source=self.source.compte_id.id

    @api.onchange('destination', 'destination_central')
    def set_comp_d(self):   
        if self.destination_central:
            self.compte_destination=self.destination_central.compte_id.id
        elif self.destination:      
            self.compte_destination=self.destination.compte_id.id

    @api.model
    def create(self, vals):
        transaction = super(ajouter_ligne_transaction, self).create(vals)
        if not transaction['name']:
            if transaction['type_trans'] == 'recette':
                transaction['name'] = self.env['ir.sequence'].next_by_code('recette.seq')
            if transaction['type_trans'] == 'depense':
                transaction['name'] = self.env['ir.sequence'].next_by_code('depense.seq')
            if transaction['type_trans'] == 'demande':
                transaction['name'] = self.env['ir.sequence'].next_by_code('trans.intr')
        return transaction

    def enregistrer(self):
        vals = {}
        caisse_sr = self.source.id
        caisse_ds = self.destination.id
        design = ''

        if self.montant <= 0:
            raise UserError(('Veuillez vérifier le montant SVP'))

        #recette    
        if self.type_trans=='recette':
            if not self.compare_date_caisse_transaction(self.caisse_recette,self.date,self.caisse_recette.type_c):
                raise UserError(('La date de la transaction doit correspondre à la période ou la date de la caisse sélectionnée !'))
            if not self.motif_id.account_analytic_account_id:
                raise UserError("Veuillez SVP renseigner le compte analytic du motif")
            
            tran = self.env['ligne.caisse'].create({
            'date':self.date,
            'name' :self.name,          
            'designation' :self.memo,
            'type_payment': self.type_payment,                         
            'montant':self.montant, 
            'ligne_id' : self.caisse_recette.id,
            'caisse_parent' : self.caisse_recette.id,
            'type_entre' : 'recette',
            'montant_signe' : self.montant,
            'type_caisse' : self.caisse_recette.type_caisse.id,
            'motif_id' : self.motif_id.id,
            'motif_family_id' : self.motif_id.fund_motif_family_id.id,
            'res_partner_id' : self.res_partner_id.id,
            'demandeur_id' : self.demandeur_id.id,
            'collaborator_id' : self.collaborator_id.id,
            'ordonator_id' : self.ordonator_id.id,
            'collaborator_ext_id' : self.collaborator_ext_id.id,
            'beneficiary_id' : self.beneficiary_id.id,
            'structure_id' : self.structure_id.id,
            })
            #### ajouter l'impact du recette sur le compte analytic
            
            account_analytic_line=self.env['account.analytic.line'].create({
                'name': self.motif_id.account_analytic_account_id.name,
                'date': self.date,
                'account_id': self.motif_id.account_analytic_account_id.id,
                'group_id': self.motif_id.account_analytic_account_id.group_id,
                'unit_amount': 1,
                'amount': self.montant,
                'ref': tran.name,
                'user_id': self._uid,
                'partner_id': self.res_partner_id.id,
                'company_id': self.caisse_recette.company_id.id or self.env.company.id,
            })
            tran.account_analytic_line_id = account_analytic_line.id

            #afficher la caisse directement après l'enregistrement du mouvement de la caisse
            result = self.env.ref('caisse.caisse_mensuel_action').read()[0]#notre action créé
            res = self.env.ref('caisse.view_caisse_mens_form')#notre vue crée
            result['views'] = [(res.id, 'form')]
            pick_ids = self.caisse_recette.id #l'objet généré
            result['res_id'] = pick_ids
            result['type'] = 'ir.actions.act_window';
            return result


        #depense            
        elif self.type_trans=='depense':
            if not self.compare_date_caisse_transaction(self.caisse_depense,self.date,self.caisse_depense.type_c):
                raise UserError(('La date de la transaction doit correspondre à la période ou la date de la caisse sélectionnée !'))
            if not self.motif_dep_id.account_analytic_account_id:
                raise UserError("Veuillez SVP renseigner le compte analytic du motif")
            if self.caisse_depense.total < self.montant:
                raise UserError("Attention! Le montant de dépense dépasse le solde de la caisse")
            tran_d = self.env['ligne.caisse'].create({
            'date':self.date,
            'name' :self.name,
            'type_payment': self.type_payment,           
            'designation' :self.memo,                            
            'montant':self.montant,   
            'montant_d':self.montant,   
            'd_id' : self.caisse_depense.id,
            'caisse_parent' : self.caisse_depense.id,
            'type_entre' : 'depense',
            'montant_signe' : -self.montant,
            'type_caisse' : self.caisse_depense.type_caisse.id,
            'motif_id' : self.motif_dep_id.id,
            'motif_family_id' : self.motif_dep_id.fund_motif_family_id.id,
            'res_partner_id' : self.res_partner_id.id,
            'demandeur_id' : self.demandeur_id.id,
            'collaborator_id' : self.collaborator_id.id,
            'ordonator_id' : self.ordonator_id.id,
            'collaborator_ext_id' : self.collaborator_ext_id.id,
            'beneficiary_id' : self.beneficiary_id.id,
            'structure_id' : self.structure_id.id,
            })
            #### ajouter l'impact du dépense sur le compte analytic
            amount = -self.montant
            account_analytic_line_dep =self.env['account.analytic.line'].create({
                'name': self.motif_dep_id.account_analytic_account_id.name,
                'date': self.date,
                'account_id': self.motif_dep_id.account_analytic_account_id.id,
                'group_id': self.motif_dep_id.account_analytic_account_id.group_id,
                'unit_amount': 1,
                'amount': amount,
                'ref': self.name,
                'user_id': self._uid,
                'partner_id': self.res_partner_id.id,
                'company_id': self.caisse_depense.company_id.id or self.env.company.id,
            })
            tran_d.account_analytic_line_id = account_analytic_line_dep.id
                
            #afficher la caisse directement après l'enregistrement du mouvement de la caisse
            result = self.env.ref('caisse.caisse_mensuel_action').read()[0]#notre action créé
            res = self.env.ref('caisse.view_caisse_mens_form')#notre vue crée
            result['views'] = [(res.id, 'form')]
            pick_ids = self.caisse_depense.id #l'objet généré
            result['res_id'] = pick_ids
            result['type'] = 'ir.actions.act_window';
            return result

        #création des lignes des demandes de virement envoyés 
        elif self.type_trans=='demande':
            if not self.compare_date_caisse_transaction(self.source,self.date,self.source.type_c) or not self.compare_date_caisse_transaction(self.destination,self.date,self.destination.type_c):
                raise UserError(('La date de la transaction doit correspondre à la période ou la date de la caisse sélectionnée !'))

            tran = self.env['ligne.demande'].create({
                'date':self.date,
                'type_payment': self.type_payment,           
                'name' :self.name,
                'montant':self.montant, 
                'amount_ok':self.montant, 
                'caisse_dem':self.source.id,
                'source':self.source.id,
                'destination':self.destination.id,
                'designation' :'Virement vers : ' + str(self.source.name),
                'designation_d' :'Demande de virement depuis : ' + str(self.destination.name),
                'state':'demande',
                'demande_id' : caisse_ds,
                'res_partner_id' : self.res_partner_id.id,
                'demandeur_id' : self.demandeur_id.id,
                'collaborator_id' : self.collaborator_id.id,
                'ordonator_id' : self.ordonator_id.id,
                'collaborator_ext_id' : self.collaborator_ext_id.id,
                'beneficiary_id' : self.beneficiary_id.id,
                'structure_id' : self.structure_id.id,
                })
        #création des lignes des demandes de virement envoyés 
        elif self.type_trans=='avance':

            tran = self.env['fund.advance'].create({
            'date':self.date,
            # 'name' :self.name,          
            'designation' :self.memo,
            'caisse': self.caisse_recette.id,
            # 'type_payment': self.type_payment,                         
            'amount':self.montant, 
            # 'ligne_id' : self.caisse_recette.id,
            # 'caisse_parent' : self.caisse_recette.id,
            # 'type_entre' : 'avance',
            # 'montant_signe' : self.montant,
            # 'type_caisse' : self.caisse_recette.type_caisse.id,
            # 'motif_id' : self.motif_id.id,
            # 'motif_family_id' : self.motif_id.fund_motif_family_id.id,
            'res_partner_id' : self.res_partner_id.id,
            # 'demandeur_id' : self.demandeur_id.id,
            # 'collaborator_id' : self.collaborator_id.id,
            # 'ordonator_id' : self.ordonator_id.id,
            # 'collaborator_ext_id' : self.collaborator_ext_id.id,
            # 'beneficiary_id' : self.beneficiary_id.id,
            # 'structure_id' : self.structure_id.id,
            })
            tran.action_confirm()
            
            # result = self.env.ref('caisse.caisse_mensuel_action').read()[0]#notre action créé
            # res = self.env.ref('caisse.view_caisse_mens_form')#notre vue crée
            # result['views'] = [(res.id, 'form')]
            # pick_ids = caisse_sr #l'objet généré
            # result['res_id'] = pick_ids
            # result['type'] = 'ir.actions.act_window';
            # return result





    def compare_date_caisse_transaction(self,caisse,date,type_c):
        if type_c == 'mensuel':
            date_debut_caisse = datetime.strptime(str(caisse.annee) + '-' + str(caisse.mois) + '-01','%Y-%m-%d').date()
            jour_fin = calendar.monthrange(int(caisse.annee),int(caisse.mois))
            date_fin_caisse = datetime.strptime(str(caisse.annee) + '-' + str(caisse.mois) + '-' + str(jour_fin[1]),'%Y-%m-%d').date()
            if date < date_debut_caisse or date > date_fin_caisse:
                return False
        elif type_c == 'daily':
            if caisse.date_caisse != date:
                return False
        return True
