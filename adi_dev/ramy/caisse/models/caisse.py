# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import time
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp
from operator import itemgetter 
import re
from odoo.tools import float_compare, float_round, float_repr

class caisse(models.Model):
    _name = "caisse"
    _inherit = ['mail.thread']
    
    def get_default_company(self):
        return self.env.user.company_id

    company_id = fields.Many2one('res.company',default=get_default_company)

    def set_user(self):
        return self.env.user

    @api.model
    def _default_journal(self):
        company_id = self.env.company.id
        journals = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', company_id)])
        if journals:
            return journals[0]
    
    def _default_account(self):
        company_id = self.env.company.id
        accounts = self.env['account.account'].search([('code', '=', "530000")],limit=1)# sur la v17 530000 fait reference au compt caisse il est natif
        if accounts:
            return accounts[0]
    
    def _compute_currency(self):
        for caisse in self:
            caisse.currency_id = caisse.journal_id.currency_id or caisse.company_id.currency_id

    name = fields.Char('Réference', states={'draft': [('readonly', False)]}, compute="compute_name", store=True)
    memo = fields.Text(string='Mémo', copy=False)
    date_caisse = fields.Date(string="Date caisse", default=time.strftime('%Y-%m-%d'), copy=False)
    date = fields.Date("Date d'ouverture", required=True, states={'confirm': [('readonly', True)]},select=True, copy=False , default=fields.Date.today(), store=True)
    close_date_caisse = fields.Datetime(string="Date de Fermeture", readonly=True, copy=False)
    date_cloture = fields.Date('Fermé le ',  select=True, copy=False )
    compte_id = fields.Many2one('account.account', 'Compte', required=True, states={'draft':[('readonly',False)]}, default=_default_account)
    journal_id =fields.Many2one('account.journal', 'Journal',default=_default_journal,  required=True,readonly=True, states={'draft':[('readonly',False)]})#, default=_d_journal_id

    solde_ouvr = fields.Float("Solde d'ouverture", digits_compute=dp.get_precision('Account') )
    solde_tans_recette = fields.Float('Transaction recette', digits_compute=dp.get_precision('Account'),states={'confirm':[('readonly',True)]} , compute='set_total')
    solde_tans_depense = fields.Float('Transaction depense', digits_compute=dp.get_precision('Account'),states={'confirm':[('readonly',True)]} , compute='set_total')
    total = fields.Float('Total théorique', digits_compute=dp.get_precision('Account'), readonly=True , compute='set_total' )
    solde_recette=fields.Float('Total Recette', digits_compute=dp.get_precision('Account'), readonly=True , compute='set_total' )
    solde_depense=fields.Float('Total Depense', digits_compute=dp.get_precision('Account'), readonly=True , compute='set_total' )
    solde_fin_reel = fields.Float('Solde de cloture reel', digits_compute=dp.get_precision('Account'),states={'confirm': [('readonly', True)]}, help="Computed using the cash control lines")
    line_ids = fields.One2many('ligne.caisse','ligne_id', 'lignes', copy=True)#, states={'confirm':[('readonly', True)]}
    d_ids = fields.One2many('ligne.caisse','d_id', 'lignes', copy=True)#, states={'confirm':[('readonly', True)]}
    caisse_line_ids = fields.One2many('ligne.caisse','caisse_parent', 'Transactions', copy=True)#, states={'confirm':[('readonly', True)]}
    demande_ids = fields.One2many('ligne.demande','demande_id', 'lignes', copy=True)#, states={'confirm':[('readonly', True)]}
    demande_env_ids = fields.One2many('ligne.demande','caisse_dem', 'lignes', copy=True)#, states={'confirm':[('readonly', True)]}
    caisse_prec = fields.Many2one('caisse', 'Caisse précédente')
    precedent_cash = fields.Boolean("Caisse précédente obligatoire")
    get_balance_end_real = fields.Boolean(string="Réintroduire le Solde Physique (Réel)")
    show_confg_initial_balance = fields.Boolean(string="Configuration de la balance initiale")
    

    move_line_ids = fields.One2many('account.move.line', 'statement_id','Entry lines', states={'confirm':[('readonly',True)]})
    state = fields.Selection([('draft', 'Nouveau'),
                                   ('open','Ouverte'), 
                                   ('confirm', 'Fermé')],
                                   'Status', required=True, readonly="1",
                                   copy=False,default='draft'
                                  )
    user_id= fields.Many2one('res.users','Responsable', help="l'utilisateur qui a ouvert la caisse", default=set_user)
    currency_id = fields.Many2one('res.currency' , string='Currency', default=_compute_currency )
    type_caisse = fields.Many2one('type.caisse','Type de caisse')
    type_c = fields.Selection(
         [
          ('mensuel','Mensuelle'),
          ('daily','Journalière'),],'Type',) #('annuel', 'Annuelle'),
    caisse_annuelle_ids = fields.One2many('ligne.demande', 'caisse_annuelle', 'caisse_annuelle_ids')

    @api.constrains('date','date_caisse')
    def check_date_caisse(self):
        caisses_count = self.search([('type_c','=',self.type_c),('type_caisse','=',self.type_caisse.id)
                                     ,('date','=',self.date),('id','!=',self.id)])
        if caisses_count:
            raise ValidationError("Vous ne pouvez pas ouvrir deux caisses avec la même date !") 
    
    @api.onchange('type_caisse')
    def _onchange_type_caisse(self):
        if self.precedent_cash and self.type_caisse :
            sorted_records = self.search([('type_caisse', '=', self.type_caisse.name),('state','=','confirm')])
            self.cumul_ecart_store =   sum(sorted_records.mapped('end_ecart_variable'))
            self.caisse_prec = self.type_caisse.last_caisse_id.id
            if self.get_balance_end_real:
                self.solde_ouvr = self.caisse_prec.balance_end_real
                self.balance_start = self.caisse_prec.balance_end_real
            else:
                self.solde_ouvr = self.caisse_prec.total
                self.balance_start = self.caisse_prec.total
        else:
            self.caisse_prec = False
    

    def default_year(self):
        return datetime.now().year

    # Compter le solde physique
    cashbox_caisse_start_id = fields.Many2one('account.bank.statement.cashbox', string="Solde initial réel")
    cashbox_caisse_end_id = fields.Many2one('account.bank.statement.cashbox', string="Solde final réel")
    balance_start = fields.Float(string='Balance initiale', states={'open': [('readonly', True)]},  store=True, tracking=True) #compute='_compute_starting_balance', readonly=False,
    balance_end_real = fields.Float('Physique de caisse', states={'open': [('readonly', True)]},  store=True, tracking=True) #compute='_compute_ending_balance', readonly=False,
    start_ecart = fields.Float(string='Ecart initial', compute="compute_ecart")
    end_ecart = fields.Float(string='Ecart sur caisse', compute="compute_ecart", store=True,)
    end_ecart2 = fields.Float(string='Ecart sur caisse', compute="compute_ecart2")
    end_ecart_variable = fields.Float(string='Ecart traité',)
    cumul_ecart = fields.Float(string="Cumule d'ecart", compute="compute_cumul_ecart")
    prec_ecart = fields.Float(string='Ecart précédent', related="caisse_prec.end_ecart")
    balance_state = fields.Selection([('draft', 'Attente de traitement'),
                                   ('correct','Correcte'), 
                                   ('incorrect', 'Incorrecte')],
                                   'Status de balance', compute="_compute_balance_state",
                                   copy=False,default='draft')
    caisse_ecart_state = fields.Selection([('no_ecart','Sans ecart'),
                                   ('with_ecart','Ecart non traité'), 
                                   ('with_ecart_t','Ecart traité'),],
                                   'Status des ecarts', compute="_compute_balance_state",
                                   copy=False, store=True, default='no_ecart')
    caisse_ecart_state2 = fields.Boolean("Status des ecarts",default=False)
    close_force = fields.Boolean("Forcer la cloture de caisse")
    close_caisse = fields.Boolean("Forcer la cloture de caisse", compute="_compute_close_caisse")
    show_start_ecart = fields.Boolean("Afficher l'écart initial", compute="_compute_show_start_ecart")
    cumul_ecart_store = fields.Float("Ecart total")

    def get_detail_caisse(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'caisse',
            'target': self,
            'res_id': self.id,
        }
        
    def compute_cumul_ecart(self):
        caisse_type = []
        for record in self:
            if record.type_caisse not in caisse_type:
                caisse_type.append(record.type_caisse)
                # Order records by some field; this is an example and should be adjusted to your specific needs
                sorted_records = self.search([('type_caisse', '=', record.type_caisse.name)], order='id')
                cumul = 0.0
                for r in sorted_records:
                    cumul += r.end_ecart_variable
                    r.cumul_ecart = cumul
            
    @api.depends('start_ecart')
    def _compute_show_start_ecart(self):
        for c in self:
            if c.start_ecart > 0 :
                c.show_start_ecart = True
            else:
                c.show_start_ecart = False

    def _compute_cumul_state(self,caisse,open_caisse):
        for c in caisse:
            c.caisse_ecart_state= 'with_ecart_t'
            c.balance_state = 'incorrect'
            c.caisse_ecart_state2=True
            c.end_ecart_variable=0
        sorted_records = self.search([('type_caisse', '=', self.type_caisse.name),('state','=','confirm')])
        open_caisse.cumul_ecart_store =   sum(sorted_records.mapped('end_ecart_variable'))
        
    @api.depends('balance_end_real', 'total','end_ecart_variable','caisse_ecart_state2')
    def _compute_balance_state(self):
        for c in self:
            if self._context.get('get_cumul') or c.caisse_ecart_state== 'with_ecart_t':
                c.caisse_ecart_state= 'with_ecart_t'
                c.balance_state = 'incorrect'
                c.caisse_ecart_state2=True
                c.end_ecart_variable=0
                continue
            if not c.balance_end_real:
                c.balance_state = 'draft'
            else:
                if c.balance_end_real != c.total and c.end_ecart_variable !=0:
                    c.balance_state = 'incorrect'
                    c.caisse_ecart_state= 'with_ecart'
                else:
                    c.balance_state = 'correct'
                    if c.caisse_ecart_state == 'with_ecart':
                        c.caisse_ecart_state= 'with_ecart_t'
                        
    
    @api.depends('balance_state', 'close_force')
    def _compute_close_caisse(self):
        for c in self:
            c.close_caisse = False
            if c.balance_state == "correct":
                c.close_caisse = True
            else:
                if c.close_force == True:
                    c.close_caisse = True
             
    def open_cashbox_id(self):
        self.ensure_one()
        context = dict(self.env.context or {})
        if context.get('balance'):
            context['caisse_id'] = self.id
            if context['balance'] == 'start':
                cashbox_id = self.cashbox_caisse_start_id.id
            elif context['balance'] == 'close':
                cashbox_id = self.cashbox_caisse_end_id.id
            elif context['balance'] == 'solde_ouvr':
                cashbox_id = self.cashbox_caisse_start_id.id
            else:
                cashbox_id = False
            action = {
                'name': _('Cash Control'),
                'view_mode': 'form',
                'res_model': 'account.bank.statement.cashbox',
                'view_id': self.env.ref('account_bnk_stm_cash_box.view_account_bnk_stmt_cashbox_footer').id,
                'type': 'ir.actions.act_window',
                'res_id': cashbox_id,
                'context': context,
                'target': 'new'
            }
            return action

    def _compute_starting_balance(self):
        # When a bank statement is inserted out-of-order several fields needs to be recomputed.
        # As the records to recompute are ordered by id, it may occur that the first record
        # to recompute start a recursive recomputation of field balance_end_real
        # To avoid this we sort the records by date
        for statement in self.sorted(key=lambda s: s.date):
            if statement.previous_statement_id.balance_end_real != statement.balance_start:
                statement.balance_start = statement.previous_statement_id.balance_end_real
            else:
                # Need default value
                statement.balance_start = statement.balance_start or 0.0
                
    def compute_ecart2(self):
        for s in self:
            s.end_ecart2=s.end_ecart
    
    @api.depends('balance_start', 'balance_end_real', 'solde_ouvr', 'total')
    def compute_ecart(self):
        for caisse in self:
            caisse.start_ecart = caisse.balance_start - caisse.solde_ouvr
            if caisse.state !='confirm':
                caisse.end_ecart = caisse.balance_end_real - caisse.total
                # if caisse.caisse_prec:
                #     caisse.end_ecart += caisse.prec_ecart
                caisse.end_ecart_variable = caisse.end_ecart
            sorted_records = self.search([('type_caisse', '=', caisse.type_caisse.name),('state','=','confirm')])
            open_caisse = self.env['caisse'].search([('type_caisse','=',caisse.type_caisse.name),("state", "=", 'open')])
            open_caisse.cumul_ecart_store =   sum(sorted_records.mapped('end_ecart_variable'))
    
    @api.constrains('annee', 'mois','date','date_caisse')
    def _check_annee(self):
        formt = re.compile("\d{4}")
        for s in self:
            if not formt.match(s.annee):
                raise ValidationError(('Le format de l\'année doit correspondre a xxxx (ex : 2023)'))
            if s.date:
                if s.type_c == 'daily' and s.date != s.date_caisse:
                    raise ValidationError(('Le Date doit correspondre a la date de la caisse'))
                elif s.type_c == 'mensuel' and dict(s._fields['mois'].selection).get(str(s.date.month))!=dict(s._fields['mois'].selection).get(s.mois)\
                                                                                        or int(s.annee) != s.date.year:
                    raise ValidationError(("Le Date doit correspondre au Mois et l'année"))
                

    annee = fields.Char('Année', default=default_year)

    def get_mois(self):
        # now = time.strftime('%m')
        return str(datetime.now().month)

    mois = fields.Selection([('1', 'Janvier'),
                                   ('2','Février'), 
                                   ('3', 'Mars'),
                                   ('4', 'Avril'),
                                   ('5', 'Mai'),
                                   ('6', 'Juin'),
                                   ('7', 'Juillet'),
                                   ('8', 'Août'),
                                   ('9', 'Septembre'),
                                   ('10', 'Octobre'),
                                   ('11', 'Novembre'),
                                   ('12', 'Décembre'),], 'Mois',default=get_mois)

    #génération automatique du nom de la caisse

    @api.depends("annee", "mois", "type_caisse","type_c")
    def compute_name(self):
        dict_mois = {'1': 'Janvier','2':u'Février','3': 'Mars','4': 'Avril','5': 'Mai','6': 'Juin',
                '7': 'Juillet','8': u'Août', '9': 'Septembre',   '10': 'Octobre','11': 'Novembre',            
                '12': u'Décembre'}
        for s in self:
            if s.type_c == 'mensuel':
                if s.mois and s.type_caisse:
                    s.name = s.type_caisse.name +' '+ dict_mois[s.mois] +' '+ s.annee
            if s.type_c == 'daily' and s.type_caisse:
                    s.name = s.type_caisse.name +' '+ datetime.strftime(s.date_caisse, "%d/%m/%Y")

            # if s.type_c == 'annuel' and s.type_caisse:
            #         s.name = s.type_caisse.name +' '+ s.annee

    

    

    def unlink(self):
        if self.state == 'confirm':
            raise ValidationError("Vous ne pouvez pas supprimer une caisse fermée !")
        return super(caisse,self).unlink()

    #récupération automatique du solde d'ouverture de la caisse de la caisse précédente
    # @api.onchange('caisse_prec')        
    # def sold_ouverture(self):
    #     total_prec = self.caisse_prec.balance_end_real
    #     self.solde_ouvr = total_prec

    #mettre par défaut le premier du mois quand on selectionne le mois de la caisse
    @api.onchange('mois')
    def onchange_mois(self):
        if self.type_c == "mensuel":
            if self.mois == "jan":
                self.date = self.annee+"-01-01"
            if self.mois == "fev":
                self.date = self.annee+"-02-01"
            if self.mois == "mars":
                self.date = self.annee+"-03-01"
            if self.mois == "avr":
                self.date = self.annee+"-04-01"
            if self.mois == "mai":
                self.date = self.annee+"-05-01"
            if self.mois == "juin":
                self.date = self.annee+"-06-01"
            if self.mois == "juil":
                self.date = self.annee+"-07-01"
            if self.mois == "out":
                self.date = self.annee+"-08-01"
            if self.mois == "sep":
                self.date = self.annee+"-09-01"
            if self.mois == "octo":
                self.date = self.annee+"-10-01"
            if self.mois == "nov":
                self.date = self.annee+"-11-01"
            if self.mois == "dec":
                self.date = self.annee+"-12-01"

    #vérification du mois du rapport de la caisse et récuperer ce recettes et dépenses
    def verif_mois(self, date_d, date_f):
        liste = []
        for rec in self.line_ids:
            # not rec.affiche_rapport and 
            if fields.Datetime.from_string(rec.date) >= date_d and fields.Datetime.from_string(rec.date) <= date_f :
                liste.append({'ref':rec.name,
                 'date': rec.date,
                 'recette': rec.montant,
                 'depence':'',
                 'designation':rec.designation,})
        for dep in self.d_ids:
            # not dep.affiche_rapport and 
            if fields.Datetime.from_string(dep.date) >= date_d and fields.Datetime.from_string(dep.date) <= date_f :
                liste.append({'ref':dep.name,
                 'date': dep.date,
                 'recette':'' ,
                 'depence':dep.montant,
                 'designation':dep.designation,})

        return sorted(liste, key=itemgetter('date'))


    def get_recettes_depences(self):
        date =(datetime.strptime(str(self.date),'%Y-%m-%d'))
        annee = date.year
        liste = []
        janvier = self.verif_mois(datetime.strptime(str(annee)+'-01-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-01-31','%Y-%m-%d'))
        liste.append(janvier)
        #vérification des années bissextiles pour traiter le cas de février
        if annee % 4 == 0:
            fev = self.verif_mois(datetime.strptime(str(annee)+'-02-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-02-29','%Y-%m-%d'))
        else:
            fev= self.verif_mois(datetime.strptime(str(annee)+'-02-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-02-28','%Y-%m-%d'))
        liste.append(fev)
        mars = self.verif_mois(datetime.strptime(str(annee)+'-03-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-03-31','%Y-%m-%d'))
        liste.append(mars)
        avr = self.verif_mois(datetime.strptime(str(annee)+'-04-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-04-30','%Y-%m-%d'))
        liste.append(avr)
        mai = self.verif_mois(datetime.strptime(str(annee)+'-05-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-05-31','%Y-%m-%d'))
        liste.append(mai)
        juin = self.verif_mois(datetime.strptime(str(annee)+'-06-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-06-30','%Y-%m-%d'))
        liste.append(juin)
        juil = self.verif_mois(datetime.strptime(str(annee)+'-07-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-07-31','%Y-%m-%d'))
        liste.append(juil)
        out = self.verif_mois(datetime.strptime(str(annee)+'-08-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-08-31','%Y-%m-%d'))
        liste.append(out)
        sep = self.verif_mois(datetime.strptime(str(annee)+'-09-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-09-30','%Y-%m-%d'))
        liste.append(sep)
        octo = self.verif_mois(datetime.strptime(str(annee)+'-10-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-10-31','%Y-%m-%d'))
        liste.append(octo)
        nov = self.verif_mois(datetime.strptime(str(annee)+'-11-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-11-30','%Y-%m-%d'))
        liste.append(nov)
        dec = self.verif_mois(datetime.strptime(str(annee)+'-12-01','%Y-%m-%d'), datetime.strptime(str(annee)+'-12-31','%Y-%m-%d'))
        liste.append(dec)
        liste.append(annee)
        return liste

    #calcul des recettes dans le rapport

    def compute_total_rec(self):
        date =(datetime.strptime(str(self.date),'%Y-%m-%d'))
        annee = date.year
        liste = []
        
        rec1, rec2, rec3, rec4, rec5, rec6, rec7, rec8, rec9, rec10, rec11, rec12  = 0,0,0,0,0,0,0,0,0,0,0,0 
        for line in self.line_ids:
            # if not line.affiche_rapport:
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-01-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-01-31','%Y-%m-%d') :
                        rec1 += line.montant
                if annee % 4 == 0:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-29','%Y-%m-%d') :
                        rec2 += line.montant
                else:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-28','%Y-%m-%d') :
                        rec2 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-03-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-03-31','%Y-%m-%d') :
                        rec3 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-04-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-04-30','%Y-%m-%d') :
                        rec4 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-05-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-05-31','%Y-%m-%d') :
                        rec5 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-06-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-06-30','%Y-%m-%d') :
                        rec6 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-07-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-07-31','%Y-%m-%d') :
                        rec7 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-08-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-08-31','%Y-%m-%d') :
                        rec8 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-09-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-09-30','%Y-%m-%d') :
                        rec9 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-10-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-10-31','%Y-%m-%d') :
                        rec10 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-11-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-11-30','%Y-%m-%d') :
                        rec11 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-12-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-12-31','%Y-%m-%d') :
                        rec12 += line.montant
        liste.append(rec1)
        liste.append(rec2)
        liste.append(rec3)
        liste.append(rec4)
        liste.append(rec5)
        liste.append(rec6)
        liste.append(rec7)
        liste.append(rec8)
        liste.append(rec9)
        liste.append(rec10)
        liste.append(rec11)
        liste.append(rec12)
        return liste
    

    #calcul des depenses

    def compute_total_dep(self):
        date =(datetime.strptime(str(self.date),'%Y-%m-%d'))
        annee = date.year
        liste = []
        dep1, dep2, dep3, dep4, dep5, dep6, dep7, dep8, dep9, dep10, dep11, dep12  = 0,0,0,0,0,0,0,0,0,0,0,0 
        for line in self.d_ids:
            # if not line.affiche_rapport:
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-01-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-01-31','%Y-%m-%d') :
                        dep1 += line.montant
                if annee % 4 == 0:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-29','%Y-%m-%d') :
                        dep2 += line.montant
                else:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-28','%Y-%m-%d') :
                        dep2 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-03-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-03-31','%Y-%m-%d') :
                        dep3 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-04-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-04-30','%Y-%m-%d') :
                        dep4 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-05-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-05-31','%Y-%m-%d') :
                        dep5 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-06-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-06-30','%Y-%m-%d') :
                        dep6 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-07-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-07-31','%Y-%m-%d') :
                        dep7 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-08-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-08-31','%Y-%m-%d') :
                        dep8 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-09-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-09-30','%Y-%m-%d') :
                        dep9 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-10-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-10-31','%Y-%m-%d') :
                        dep10 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-11-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-11-30','%Y-%m-%d') :
                        dep11 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-12-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-12-31','%Y-%m-%d') :
                        dep12 += line.montant
        liste.append(dep1)
        liste.append(dep2)
        liste.append(dep3)
        liste.append(dep4)
        liste.append(dep5)
        liste.append(dep6)
        liste.append(dep7)
        liste.append(dep8)
        liste.append(dep9)
        liste.append(dep10)
        liste.append(dep11)
        liste.append(dep12)
        return liste
    
    #calcul des soldes d'ouvertures des mois dansle rapport 

    def compute_solde_ouverture(self):
        date =(datetime.strptime(str(self.date),'%Y-%m-%d'))
        annee = date.year
        liste = []
        solde_f = 0
        sld_ouv1, sld_ouv2, sld_ouv3, sld_ouv4, sld_ouv5, sld_ouv6, sld_ouv7, sld_ouv8, sld_ouv9, sld_ouv10, sld_ouv11, sld_ouv12  = 0,0,0,0,0,0,0,0,0,0,0,0 
        rec1, rec2, rec3, rec4, rec5, rec6, rec7, rec8, rec9, rec10, rec11, rec12  = 0,0,0,0,0,0,0,0,0,0,0,0 
        dep1, dep2, dep3, dep4, dep5, dep6, dep7, dep8, dep9, dep10, dep11, dep12  = 0,0,0,0,0,0,0,0,0,0,0,0 
        for line in self.d_ids:
            # if not line.affiche_rapport:
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-01-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-01-31','%Y-%m-%d') :
                        dep1 += line.montant
                if annee % 4 == 0:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-29','%Y-%m-%d') :
                        dep2 += line.montant
                else:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-28','%Y-%m-%d') :
                        dep2 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-03-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-03-31','%Y-%m-%d') :
                        dep3 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-04-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-04-30','%Y-%m-%d') :
                        dep4 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-05-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-05-31','%Y-%m-%d') :
                        dep5 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-06-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-06-30','%Y-%m-%d') :
                        dep6 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-07-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-07-31','%Y-%m-%d') :
                        dep7 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-08-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-08-31','%Y-%m-%d') :
                        dep8 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-09-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-09-30','%Y-%m-%d') :
                        dep9 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-10-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-10-31','%Y-%m-%d') :
                        dep10 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-11-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-11-30','%Y-%m-%d') :
                        dep11 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-12-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-12-31','%Y-%m-%d') :
                        dep12 += line.montant
        for line in self.line_ids:
            # if not line.affiche_rapport:
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-01-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-01-31','%Y-%m-%d') :
                        rec1 += line.montant
                if annee % 4 == 0:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-29','%Y-%m-%d') :
                        rec2 += line.montant
                else:
                    if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-02-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-02-28','%Y-%m-%d') :
                        rec2 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-03-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-03-31','%Y-%m-%d') :
                        rec3 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-04-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-04-30','%Y-%m-%d') :
                        rec4 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-05-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-05-31','%Y-%m-%d') :
                        rec5 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-06-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-06-30','%Y-%m-%d') :
                        rec6 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-07-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-07-31','%Y-%m-%d') :
                        rec7 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-08-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-08-31','%Y-%m-%d') :
                        rec8 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-09-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-09-30','%Y-%m-%d') :
                        rec9 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-10-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-10-31','%Y-%m-%d') :
                        rec10 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-11-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-11-30','%Y-%m-%d') :
                        rec11 += line.montant
                if fields.Datetime.from_string(line.date) >= datetime.strptime(str(annee)+'-12-01','%Y-%m-%d') and fields.Datetime.from_string(line.date) <= datetime.strptime(str(annee)+'-12-31','%Y-%m-%d') :
                        rec12 += line.montant

        caisse_jan = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','jan')]).solde_ouvr
        caisse_2 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','fev')]).solde_ouvr
        caisse_3 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','mars')]).solde_ouvr
        caisse_4 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','avr')]).solde_ouvr
        caisse_5 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','mai')]).solde_ouvr
        caisse_6 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','juin')]).solde_ouvr
        caisse_7 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','juil')]).solde_ouvr
        caisse_8 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','out')]).solde_ouvr
        caisse_9 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','sep')]).solde_ouvr
        caisse_10 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','octo')]).solde_ouvr
        caisse_11 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','nov')]).solde_ouvr
        caisse_12 = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',annee),('type_caisse','=',self.type_caisse.id),('mois','=','dec')]).solde_ouvr
        
        if caisse_jan:
            sld_ouv1 = caisse_jan
            sld_ouv2 = rec1 - dep1 + sld_ouv1
            sld_ouv3 = rec2 - dep2 + sld_ouv2
            sld_ouv4 = rec3 - dep3 + sld_ouv3
            sld_ouv5 = rec4 - dep4 + sld_ouv4
            sld_ouv6 = rec5 - dep5 + sld_ouv5
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_2:
            sld_ouv2 = caisse_2
            sld_ouv3 = rec2 - dep2 + sld_ouv2
            sld_ouv4 = rec3 - dep3 + sld_ouv3
            sld_ouv5 = rec4 - dep4 + sld_ouv4
            sld_ouv6 = rec5 - dep5 + sld_ouv5
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_3:
            sld_ouv3 = caisse_3
            sld_ouv4 = rec3 - dep3 + sld_ouv3
            sld_ouv5 = rec4 - dep4 + sld_ouv4
            sld_ouv6 = rec5 - dep5 + sld_ouv5
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_4:
            sld_ouv4 = caisse_4
            sld_ouv5 = rec4 - dep4 + sld_ouv4
            sld_ouv6 = rec5 - dep5 + sld_ouv5
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_5:
            sld_ouv5 = caisse_5
            sld_ouv6 = rec5 - dep5 + sld_ouv5
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 
        elif caisse_6:
            sld_ouv6 = caisse_6
            sld_ouv7 = rec6 - dep6 + sld_ouv6
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_7:
            sld_ouv7 = caisse_7
            sld_ouv8 = rec7 - dep7 + sld_ouv7
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_8:
            sld_ouv8 = caisse_8
            sld_ouv9 = rec8 - dep8 + sld_ouv8
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_9:
            sld_ouv9 = caisse_9
            sld_ouv10 = rec9 - dep9 + sld_ouv9
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_10:
            sld_ouv10 = caisse_10
            sld_ouv11 = rec10 - dep10 + sld_ouv10
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_11:
            sld_ouv11 = caisse_11
            sld_ouv12 = rec11 - dep11 + sld_ouv11
            solde_f = sld_ouv12 + rec12 - dep12 

        elif caisse_12:
            sld_ouv12 = caisse_12
            solde_f = sld_ouv12 + rec12 - dep12 

        #solde_f_char = amount_to_text_fr(solde_f,'Dinars').upper()
        solde_f_char = self.env.user.company_id.currency_id.amount_to_text(solde_f)
        liste.append(sld_ouv1)
        liste.append(sld_ouv2)
        liste.append(sld_ouv3)
        liste.append(sld_ouv4)
        liste.append(sld_ouv5)
        liste.append(sld_ouv6)
        liste.append(sld_ouv7)
        liste.append(sld_ouv8)
        liste.append(sld_ouv9)
        liste.append(sld_ouv10)
        liste.append(sld_ouv11)
        liste.append(sld_ouv12)
        liste.append(solde_f)
        liste.append(solde_f_char)
        return liste

    #ouvrire les caisse et empêcher d'ouvrire deux caisses du même type au même temps

    def open(self):
        nb_caisses_an = 0
        #fermer la caisse précédente avant d'ouvrir la nouvelle
        caisses_ouv = self.search([('state','=','open'),('type_c','=',self.type_c),('type_caisse','=',self.type_caisse.id)])
        # for c in caisses_ouv:
            # if (self.type_c == 'mensuel' and self.annee == c.annee and self.mois == c.mois) or (self.type_c == 'daily' and self.date_caisse == c.date_caisse) :
        if caisses_ouv:
            raise ValidationError("Vous devez d'abord fermer la caisse précédente, ensuite vous pourrez ouvrir cette caisse !!")
                # break
        caisses_count = self.search([('state','!=','draft'),('type_c','=',self.type_c),('type_caisse','=',self.type_caisse.id)
                                     ,('date','=',self.date),('id','!=',self.id)])
        if caisses_count:
            raise ValidationError("Vous ne pouvez pas ouvrir deux caisses avec la même date !")
        self.state='open'
    

    #calvul des taux des lignes
    @api.depends('line_ids','d_ids')
    def set_total(self):
        for ca in self:
            solde_recette = 0
            solde_depense = 0
            for s_id in ca.line_ids:
                if s_id.type_entre == 'recette':
                    solde_recette += s_id.montant
            for line in ca.d_ids:
                if line.type_entre == 'depense':
                    solde_depense += line.montant
            ca.total = solde_recette - solde_depense + ca.solde_ouvr
            ca.solde_recette=solde_recette
            ca.solde_depense=solde_depense


    total_char = fields.Char(compute='_compte_total' , string="Total")

    @api.depends('total')
    def _compte_total(self):
        for rec in self:
            rec.total_char = self.env.user.company_id.currency_id.amount_to_text(rec.total)

class Caisse_ligne(models.Model):
    _name = "ligne.caisse"
    _order = 'date asc'

    name = fields.Char('Référence',)
    date = fields.Date('Date', required=True ,)
    montant = fields.Monetary('Montant', digits_compute=dp.get_precision('Account'))
    montant_d = fields.Monetary('Montant', digits_compute=dp.get_precision('Account'),)
    source = fields.Many2one('caisse','Source')
    compte_source = fields.Many2one('account.account', 'Compte Source' )
    destination = fields.Many2one('caisse','Destination')
    compte_destination = fields.Many2one('account.account', 'Compte Destination')
    ligne_id = fields.Many2one('caisse',ondelete="cascade")
    d_id = fields.Many2one('caisse')
    caisse_parent = fields.Many2one('caisse')
    type_trans= fields.Boolean(default=False)
    designation = fields.Char('Désignation')
    type_payment = fields.Selection([('bank', 'Bank'),
                                   ('cash','Cash'),],
                                   'Type de paiement',)
    type_caisse = fields.Many2one('type.caisse','Type')
    demande_id = fields.Many2one('caisse')
    demande_env_id = fields.Many2one('caisse')
    caisse_annuelle = fields.Many2one('caisse', 'Caisse Annuelle')
    caisse_dem_annuelle = fields.Many2one('caisse', 'Demandé par(annuelle)')
    caisse_dem = fields.Many2one('caisse', 'Demandé par')
    demande = fields.Boolean('une demande', default=False)
    c_an_rec_dep = fields.Many2one('caisse', 'Caisse Annuelle rec dep')
    affiche_rapport = fields.Boolean("Ne pas afficher")
    type_entre = fields.Selection([('depense','Dépense'),('recette','Recette'),
                                ('avance','Avance'),('return_avance','Retour avance')],string="Type")
    montant_signe = fields.Monetary('Montant')
    motif_id =  fields.Many2one(string='Motif',comodel_name='fund.motif',)
    motif_family_id = fields.Many2one(string='Famille motif', comodel_name='fund.motif.family',store=True,) 
    fund_advance_id = fields.Many2one('fund.advance', string="Avance", )
    advance = fields.Boolean("Is advance")
    payment = fields.Boolean("Is payment")
    res_partner_id = fields.Many2one('res.partner', string='Partenaire',)
    collaborator_id = fields.Many2one('hr.employee', string='Collaborateur',)
    ordonator_id = fields.Many2one('res.partner', string='Ordonnateur',)
    demandeur_id = fields.Many2one('res.partner', string='Demandeur',)
    collaborator_ext_id = fields.Many2one('res.partner', string='Collaborateur externe',)
    beneficiary_id = fields.Many2one('res.partner', string='Bénéficiaire',)
    structure_id = fields.Many2one('hr.department', string='Structure',)
    transaction_state = fields.Selection([('justify', 'Justifié'),
                                   ('draft','Attente justification'),],
                                   'État de transaction', default='draft', compute="compute_trans_state")
    jointure = fields.Binary( string="Jointure")
    account_analytic_line_id = fields.Many2one(string='Ligne compte analytique', comodel_name='account.analytic.line',)
    payment_id = fields.Many2one(string='Paiement', comodel_name='account.payment',)
    ligne_demande_id = fields.Many2one('ligne.demande',string="Ligne demande")
    # calcul État de transaction si justifié ou non
    @api.depends('jointure')
    def compute_trans_state(self):
        for c in self:
            if c.jointure:
                c.transaction_state = 'justify' 
            else:
                c.transaction_state = 'draft'  


    # @api.depends('type_entre','montant')
    # def compute_montant_d(self):
    #     Exception('compute MD')
    #     for line in self:
    #         if line.type_entre == 'depense':
    #             line.montant_d = line.montant
             
    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency',default=get_currency)

    @api.onchange('montant')
    def onchange_montant(self):
         if self.montant:
              self.ligne_demande_id.amount_ok = self.montant
         
    @api.onchange('date')
    def onchange_date(self):
        if self.demande:
            return {
                'warning': {
                    'title': _("Avertissement"),  # Use _() for translation
                    'message': _("Veuillez modifier la date même dans les lignes qui référencent cette ligne !")
                }
            }

    @api.onchange('name')
    def onchange_name(self):
        if self.demande:
            return {
            'warning': {
                'title': "Avertissement",  
                'message': "Veuillez modifier la référence même dans les lignes qui référencent cette ligne !"
            }
        }

    @api.onchange('type_payment')
    def onchange_name(self):
        return {
            'warning': {
                'title': _("Avertissement"),  # _() enables translation
                'message': _("Veuillez modifier le numéro de compte comptable même dans les lignes qui référencent cette ligne !")
            }
        }
    
    def unlink(self):
        for line in self:
            # ampêcher la suppression des lignes créées a partir des avances 
            if line.advance:
                raise ValidationError(('Désolé, les lignes liées aux avances ne peuvent pas être supprimées.'))
            if line.payment:
                raise ValidationError(('Les transations liées aux paiements ne peuvent pas être supprimées.'))
            if line.account_analytic_line_id:
                raise ValidationError("Désolé, les lignes liées aux comptes analytique ne peuvent être supprimées sauf si vous supprimez la ligne dans le compte analytique!")        
        return super(Caisse_ligne,self).unlink()
    
    def write(self, vals):
        if 'montant' in vals:
            if vals['montant']:
                if self.account_analytic_line_id:
                    self.account_analytic_line_id.amount = vals['montant']
        return super(Caisse_ligne, self).write(vals)

################ Demandes de virement (transferts internes)#####################
class CaisseDemande(models.Model):
    _name = "ligne.demande"
    _order = 'date asc'


    name = fields.Char('Référence',)
    date = fields.Date('Date', required=True)
    montant = fields.Float('Montant', digits_compute=dp.get_precision('Montant'))
    amount_ok = fields.Float('Montant accordé', digits_compute=dp.get_precision('Montant accordé'), readonly=True, tracking=True 
    )
    source = fields.Many2one('caisse','Source')
    compte_source = fields.Many2one('account.account', 'Compte Source' )
    destination = fields.Many2one('caisse','Destination')
    compte_destination = fields.Many2one('account.account', 'Compte Destination')
    demande_id = fields.Many2one('caisse')
    demande_env_id = fields.Many2one('caisse')
    type_trans= fields.Boolean(default=False)
    designation = fields.Char('Désignation')
    state = fields.Selection([('demande', 'En attente'),
                                   ('valid','Validé'),
                                   ('annul', 'Refusé')],
                                   'Status', 
                                  )
    caisse_dem = fields.Many2one('caisse', 'Demandé par')
    type_caisse = fields.Many2one('type.caisse','Type',related="caisse_dem.type_caisse")
    designation_d = fields.Char('Désignation')
    caisse_annuelle = fields.Many2one('caisse', 'Caisse Annuelle destination')
    caisse_dem_annuelle = fields.Many2one('caisse', 'Demandé par(annuelle)')
    #num_compte_comptable = fields.Char("N° compte compta.",)
    type_payment = fields.Selection([('bank', 'Bank'),
                                   ('cash','Cash'),],
                                   'Type de paiement',)
    type_c = fields.Selection([('annuel', 'Annuelle'),
                                   ('mensuel','Mensuelle'),],
                                   'Type', related="caisse_dem.type_c", 
                                  )
    motif_id =  fields.Many2one(string='Motif',comodel_name='fund.motif',)
    motif_family_id = fields.Many2one(string='Famille motif', comodel_name='fund.motif.family',store=True,)
    res_partner_id = fields.Many2one('res.partner', string='Partenaire',)
    collaborator_id = fields.Many2one('hr.employee', string='Collaborateur',)
    ordonator_id = fields.Many2one('res.partner', string='Ordonnateur',)
    demandeur_id = fields.Many2one('res.partner', string='Demandeur',)
    collaborator_ext_id = fields.Many2one('res.partner', string='Collaborateur externe',)
    beneficiary_id = fields.Many2one('res.partner', string='Bénéficiaire',)
    structure_id = fields.Many2one('hr.department', string='Structure',)

    
    @api.onchange('date')
    def onchange_date(self):
        return {
            'warning': {
                'title': "Avertissement",  
                'message': "Veuillez modifier la date même dans les lignes qui référencent cette ligne !"
            }
        }

        return res

    @api.onchange('name')
    def onchange_name(self):
        return {
            'warning': {
                'title': "Avertissement",
                'message': "Veuillez modifier la référence même dans les lignes qui référencent cette ligne !"
            }
        }

    @api.onchange('type_payment')
    def onchange_type_payment(self):
        return {
            'warning': {
                'title': "Avertissement",
                'message': "Veuillez modifier le type de paiement même dans les lignes qui référencent cette ligne !"
            }
        }


    #refus des demandes de virement
    def annuler(self):
        if self.state == 'demande' and self.state != 'valid':
            self.state = 'annul'
            for line in self.caisse_annuelle.demande_ids:
                if line.name == self.name:
                    line.state = 'annul'


    #fonction qui valide les demandes de virement
    def valider(self):
        if self.demande_id.total < self.amount_ok:
            raise Exception(self.demande_id.total, self.amount_ok)
            raise ValidationError("Le montant de cette transaction est supérieur au solde de la caisse")
        else:
            if self.state == 'demande' and self.state != 'annul':
                tran_d = self.env['ligne.caisse'].create({
                'date':self.date,
                'type_payment': self.type_payment,        
                'name' :self.name,          
                'designation' :self.designation,                            
                'montant':self.amount_ok,
                'source':self.caisse_dem.id ,
                'destination':self.destination.id , 
                'demande':True ,
                'caisse_annuelle':self.caisse_annuelle.id , 
                'caisse_dem_annuelle':self.caisse_dem_annuelle.id , 
                'd_id' : self.demande_id.id ,
                'caisse_parent' : self.demande_id.id ,
                'type_entre' : 'depense',
                'montant_signe' : -self.amount_ok,
                'type_caisse' : self.demande_id.type_caisse.id,
                'ligne_demande_id': self.id,
                })

                tran = self.env['ligne.caisse'].create({
                'date':self.date,
                'type_payment': self.type_payment,           
                'name' :self.name,          
                'designation' :self.designation_d,                            
                'montant':self.amount_ok,
                'montant_d':self.amount_ok,
                'source':self.caisse_dem.id ,
                'destination':self.destination.id , 
                'demande':True ,
                'caisse_annuelle':self.caisse_annuelle.id , 
                'caisse_dem_annuelle':self.caisse_dem_annuelle.id , 
                'ligne_id' : self.caisse_dem.id ,
                'caisse_parent' : self.caisse_dem.id ,
                'type_entre' : 'recette',
                'montant_signe' : self.amount_ok,
                'type_caisse' : self.caisse_dem.type_caisse.id,
                'ligne_demande_id': self.id,
                })

            self.state = 'valid'

            #mettre a jours la caisse directement apres valider une demande 
            result = self.env.ref('caisse.caisse_mensuel_action').read()[0]#notre action créé
            result = result
            res = self.env.ref('caisse.view_caisse_mens_form')#notre vue crée
            result['views'] = [(res.id, 'form')]
            pick_ids = self.demande_id.id #l'objet généré
            result['res_id'] = pick_ids
            result['type'] = 'ir.actions.act_window';
            return result
    

class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'

    def default_caisse_ids(self):
        if self.env.context.get('caisse_id'):
             return [(6, 0, [self.env.context.get('caisse_id')])]

    start_caisse_ids = fields.One2many('caisse', 'cashbox_caisse_start_id',)
    end_caisse_ids = fields.One2many('caisse', 'cashbox_caisse_end_id',)

    @api.model
    def default_get(self, fields):
        vals = super(AccountBankStmtCashWizard, self).default_get(fields)
        balance = self.env.context.get('balance')
        caisse_id = self.env.context.get('caisse_id')
        
        if 'start_caisse_ids' in fields and not vals.get('start_caisse_ids') and caisse_id and balance == 'start':
            vals['start_caisse_ids'] = [(6, 0, [caisse_id])]
        if 'end_caisse_ids' in fields and not vals.get('end_caisse_ids') and caisse_id and balance == 'close':
            vals['end_caisse_ids'] = [(6, 0, [caisse_id])]
        return vals
    
    @api.depends('start_bank_stmt_ids', 'end_bank_stmt_ids','start_caisse_ids','end_caisse_ids')
    def _compute_currency(self):
        for cashbox in self:
            cashbox.currency_id = False
            if cashbox.end_bank_stmt_ids:
                cashbox.currency_id = cashbox.end_bank_stmt_ids[0].currency_id
            if cashbox.start_bank_stmt_ids:
                cashbox.currency_id = cashbox.start_bank_stmt_ids[0].currency_id

            if cashbox.end_caisse_ids:
                cashbox.currency_id = cashbox.end_caisse_ids[0].currency_id.id
            if cashbox.start_caisse_ids:
                cashbox.currency_id = cashbox.start_caisse_ids[0].currency_id.id

    def _validate_cashbox(self):
        for cashbox in self:
            if cashbox.start_bank_stmt_ids:
                cashbox.start_bank_stmt_ids.write({'balance_start': cashbox.total})
            if cashbox.end_bank_stmt_ids:
                cashbox.end_bank_stmt_ids.write({'balance_end_real': cashbox.total})

            if cashbox.start_caisse_ids:
                cashbox.start_caisse_ids.write({'balance_start': cashbox.total})
            if cashbox.end_caisse_ids:
                cashbox.end_caisse_ids.write({'balance_end_real': cashbox.total})
            if self._context.get('balance', False)=='solde_ouvr':
                self.env['caisse'].browse(self._context.get('caisse_id', False)).write({'solde_ouvr': cashbox.total})
                

    # gestion billets\pièces dans compter
    # récupération des lignes de pièces
    def default_pieces(self):
        currency_id = self.env.user.company_id.currency_id
        liste_pieces = self.env['account.cashbox.line']
        if currency_id.cashbox_lines_coin_ids:
            for coin in currency_id.cashbox_lines_coin_ids:
                account_cashbox_line = liste_pieces.create({
                    'cashbox_coin_id': self.id,
                    'coin_value': coin.coin_value,
                })
                liste_pieces += account_cashbox_line
            return [(6, False, liste_pieces.ids)]
    cashbox_lines_coin_ids = fields.One2many('account.cashbox.line', 'cashbox_coin_id', string='Pièces', default=default_pieces)

    # récupération des lignes de billets
    def default_billets(self):
        currency_id = self.env.user.company_id.currency_id
        liste_billets = self.env['account.cashbox.line']
        if currency_id.cashbox_lines_ids:
            for bill in currency_id.cashbox_lines_ids:
                account_cashbox_line = liste_billets.create({
                    'cashbox_id': self.id,
                    'coin_value': bill.coin_value,
                })
                liste_billets += account_cashbox_line
            return [(6, False, liste_billets.ids)]
    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'cashbox_id', string='Pièces', default=default_billets)

    # Calcul total billets et pièces
    @api.depends('cashbox_lines_ids', 'cashbox_lines_coin_ids','cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number')
    def _compute_total(self):
        for cashbox in self:
            cashbox.total = sum([line.subtotal for line in cashbox.cashbox_lines_ids]) + sum([line.subtotal for line in cashbox.cashbox_lines_coin_ids])

# *********************************** lignes de wizard de billets/pièces **************************************
class AccountCashboxLine(models.Model):
    """
    Account Bank Statement popup that allows entering cash details.
    """
    _inherit = 'account.cashbox.line'
    _order = 'sequence'
    
    cashbox_coin_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox coin")
    res_currency_id = fields.Many2one('res.currency', string="Blillets")
    res_currency_coin_id = fields.Many2one('res.currency', string="Pièces")
    sequence = fields.Integer('Sequence')