# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from datetime import datetime

class caisse_date_fin(models.TransientModel):
	_name="caisse.date.fin"


	#mettre par défaut le dernier jour du mois dans la date de fermeture
	def default_date_fin(self):
		caisse = self.env['caisse'].browse(self.env.context.get('active_id',False))
		d=caisse.date
		t= datetime.now()
		return datetime(d.year, d.month, d.day, t.hour-1, t.minute, t.second)
		
	date_fin = fields.Datetime('Date fermeture de la caisse',default=default_date_fin)

	@api.onchange('date_fin')
	def _onchange_date_fin(self):
		caisse = self.env['caisse'].browse(self.env.context.get('active_id',False))
		for rec in self:
			if rec.date_fin and rec.date_fin.date() < caisse.date:
				raise ValidationError(('Le Date de fin ne doit pas etre superieur a la date de la caisse')) 
            
         


	def fermer(self):
		if 'active_model' in self._context and self._context['active_model'] == 'caisse':
			res = self.env['caisse'].browse(self._context['active_id'])
			if res:
				if res.total < 0 :
					raise ValidationError("Vous ne pouvez pas fermer une caisse si son solde total est négatif ! ")
				res.date_cloture = self.date_fin
 
				piece_ids = self.env['account.move'].search([])
				for p in piece_ids :			
					if p.name == res.name and p.date == res.date and p.period_id.id==res.period_id.id:
						p.state='posted'

				#génération automatique de la caisse annuelle contenant toutes les lignes
				if res.mois =='dec':
					caisse_an = self.env['caisse'].create({'annee':res.annee,
						'type_caisse':res.type_caisse.id,
						'type_c':'annuel',
						'user_id':res.user_id.id,
						'compte_id':res.compte_id.id,
						'journal_id':res.journal_id.id,
						'date':datetime.strptime(str(res.annee)+'-01-01','%Y-%m-%d'),
						'date_cloture':datetime.strptime(str(res.annee)+'-12-31','%Y-%m-%d'),
						'state':'confirm',
						 })
					caisse_mens = self.env['caisse'].search([('type_c','=','mensuel'),('annee','=',res.annee),('type_caisse','=',res.type_caisse.id)])
					
					for c_mens in caisse_mens:
						if c_mens.line_ids:
							for ligne_rec in c_mens.line_ids:
								recettes = self.env['ligne.caisse'].create({
									'date':ligne_rec.date,
									#'num_compte_comptable':ligne_rec.num_compte_comptable,
									'name':ligne_rec.name,
									'montant':ligne_rec.montant,
									'source':ligne_rec.source.id,
									'destination':ligne_rec.destination.id,
									'caisse_dem':ligne_rec.caisse_dem.id,
									'designation':ligne_rec.designation,
									'affiche_rapport':ligne_rec.affiche_rapport,
									'ligne_id':caisse_an.id,
									 })
						if c_mens.d_ids:
							for ligne_dep in c_mens.d_ids:
								depenses = self.env['ligne.caisse'].create({
									'date':ligne_dep.date,
									#'num_compte_comptable':ligne_dep.num_compte_comptable,
									'name':ligne_dep.name,
									'montant_d':ligne_dep.montant_d,
									'source':ligne_dep.source.id,
									'destination':ligne_dep.destination.id,
									'caisse_dem':ligne_dep.caisse_dem.id,
									'designation':ligne_dep.designation,
									'affiche_rapport':ligne_dep.affiche_rapport,
									'd_id':caisse_an.id,
									 })
				# for demande in res.demande_ids:
				# 	if demande.state == 'demande':	
				# 		raise Warning("Vous avez des demande de virement non traités! si vous continuez les demandes vont être refusées")
				for demande in res.demande_ids:
					if demande.state == 'demande':	
						demande.annuler()	
				# for line in res.caisse_line_ids:
				# 	if line.advance or line.fund_advance_id:
				# 		line.fund_advance_id.state = 'close'
				res.type_caisse.last_caisse_id = res.id
				res.write({'state':'confirm',
                           'close_date_caisse':self.date_fin})
