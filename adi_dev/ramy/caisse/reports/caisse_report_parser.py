# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
import time
from datetime import datetime

class ReportCaisse(models.AbstractModel):
	_name="report.caisse.report_caisse"



	def get_mois(self,date_from,date_to,cs):
		res =[]
		janvier = []
		fev = []
		mars = []
		avr = []
		mai = []
		juin = []
		juil = []
		out = []
		sep = []
		octo = []
		nov = []
		dec = []
		annee = []

		total_rec_1 = total_rec_2 = total_rec_3 = total_rec_4 = total_rec_5 = total_rec_6 = total_rec_7 = total_rec_8 = total_rec_9 = total_rec_10 = total_rec_11 = total_rec_12 = 0.00

		total_dep_1 = total_dep_2 = total_dep_3 = total_dep_4 = total_dep_5 = total_dep_6 = total_dep_7 = total_dep_8 = total_dep_9 = total_dep_10 = total_dep_11 = total_dep_12 = 0.00

		so_janvier = so_fev = so_mars = so_avr = so_mai = so_juin = so_juil = so_out = so_sep = so_octo = so_nov = so_dec = 0

		solde_ouvert_t = 0.00
		solde_ouvert_t_ch = ""

		caisses = self.env['caisse'].search([('type_caisse','=',cs),('date','>=',date_from),('date_cloture','<=',date_to)])
		for x in caisses: 
			if len(x.get_recettes_depences()[0])>0:
				janvier = x.get_recettes_depences()[0]
			if len(x.get_recettes_depences()[1])>0:
				fev = x.get_recettes_depences()[1]
			if len(x.get_recettes_depences()[2])>0:
				mars = x.get_recettes_depences()[2]
			if len(x.get_recettes_depences()[3])>0:
				avr = x.get_recettes_depences()[3]
			if len(x.get_recettes_depences()[4])>0:
				mai = x.get_recettes_depences()[4]
			if len(x.get_recettes_depences()[5])>0:
				juin = x.get_recettes_depences()[5]
			if len(x.get_recettes_depences()[6])>0:
				juil = x.get_recettes_depences()[6]
			if len(x.get_recettes_depences()[7])>0:
				out = x.get_recettes_depences()[7]
			if len(x.get_recettes_depences()[8])>0:
				sep = x.get_recettes_depences()[8]
			if len(x.get_recettes_depences()[9])>0:
				octo = x.get_recettes_depences()[9]
			if len(x.get_recettes_depences()[10])>0:
				nov = x.get_recettes_depences()[10]
			if len(x.get_recettes_depences()[11])>0:
				dec = x.get_recettes_depences()[11]

			#solde d'ouverteur

			if x.compute_solde_ouverture()[0]>0:
				so_janvier = x.compute_solde_ouverture()[0]
			if x.compute_solde_ouverture()[1]>0:
				so_fev = x.compute_solde_ouverture()[1]
			if x.compute_solde_ouverture()[2]>0:
				so_mars = x.compute_solde_ouverture()[2]
			if x.compute_solde_ouverture()[3]>0:
				so_avr = x.compute_solde_ouverture()[3]
			if x.compute_solde_ouverture()[4]>0:
				so_mai = x.compute_solde_ouverture()[4]
			if x.compute_solde_ouverture()[5]>0:
				so_juin = x.compute_solde_ouverture()[5]
			if x.compute_solde_ouverture()[6]>0:
				so_juil = x.compute_solde_ouverture()[6]
			if x.compute_solde_ouverture()[7]>0:
				so_out = x.compute_solde_ouverture()[7]
			if x.compute_solde_ouverture()[8]>0:
				so_sep = x.compute_solde_ouverture()[8]
			if x.compute_solde_ouverture()[9]>0:
				so_octo = x.compute_solde_ouverture()[9]
			if x.compute_solde_ouverture()[10]>0:
				so_nov = x.compute_solde_ouverture()[10]
			if x.compute_solde_ouverture()[11]>0:
				so_dec = x.compute_solde_ouverture()[11]
			if x.compute_solde_ouverture()[12]>0:
				solde_ouvert_t = x.compute_solde_ouverture()[12]
			if len(x.compute_solde_ouverture()[13])>0:
				solde_ouvert_t_ch = x.compute_solde_ouverture()[13]

			#Totale recette

			if x.compute_total_rec()[0]>0:
				total_rec_1 = x.compute_total_rec()[0]
			if x.compute_total_rec()[1]>0:
				total_rec_2 = x.compute_total_rec()[1]
			if x.compute_total_rec()[2]>0:
				total_rec_3 = x.compute_total_rec()[2]
			if x.compute_total_rec()[3]>0:
				total_rec_4 = x.compute_total_rec()[3]
			if x.compute_total_rec()[4]>0:
				total_rec_5 = x.compute_total_rec()[4]
			if x.compute_total_rec()[5]>0:
				total_rec_6 = x.compute_total_rec()[5]
			if x.compute_total_rec()[6]>0:
				total_rec_7 = x.compute_total_rec()[6]
			if x.compute_total_rec()[7]>0:
				total_rec_8 = x.compute_total_rec()[7]
			if x.compute_total_rec()[8]>0:
				total_rec_9 = x.compute_total_rec()[8]
			if x.compute_total_rec()[9]>0:
				total_rec_10 = x.compute_total_rec()[9]
			if x.compute_total_rec()[10]>0:
				total_rec_11 = x.compute_total_rec()[10]
			if x.compute_total_rec()[11]>0:
				total_rec_12 = x.compute_total_rec()[11]

			#Totale depence

			if x.compute_total_dep()[0]>0:
				total_dep_1 = x.compute_total_dep()[0]
			if x.compute_total_dep()[1]>0:
				total_dep_2 = x.compute_total_dep()[1]
			if x.compute_total_dep()[2]>0:
				total_dep_3 = x.compute_total_dep()[2]
			if x.compute_total_dep()[3]>0:
				total_dep_4 = x.compute_total_dep()[3]
			if x.compute_total_dep()[4]>0:
				total_dep_5 = x.compute_total_dep()[4]
			if x.compute_total_dep()[5]>0:
				total_dep_6 = x.compute_total_dep()[5]
			if x.compute_total_dep()[6]>0:
				total_dep_7 = x.compute_total_dep()[6]
			if x.compute_total_dep()[7]>0:
				total_dep_8 = x.compute_total_dep()[7]
			if x.compute_total_dep()[8]>0:
				total_dep_9 = x.compute_total_dep()[8]
			if x.compute_total_dep()[9]>0:
				total_dep_10 = x.compute_total_dep()[9]
			if x.compute_total_dep()[10]>0:
				total_dep_11 = x.compute_total_dep()[10]
			if x.compute_total_dep()[11]>0:
				total_dep_12 = x.compute_total_dep()[11]

			annee = x.get_recettes_depences()[12]
		#raise Exception(avr)
		res.append({'caisse':caisses[0],
					'annee':annee,
					'janvier':janvier,
					'fev':fev,
					'mars':mars,
					'avr':avr,
					'mai':mai,
					'juin':juin,
					'juil':juil,
					'out':out,
					'sep':sep,
					'octo':octo,
					'nov':nov,
					'dec':dec,
					'so_janvier':so_janvier,
					'so_fev':so_fev,
					'so_mars':so_mars,
					'so_avr':so_avr,
					'so_mai':so_mai,
					'so_juin':so_juin,
					'so_juil':so_juil,
					'so_out':so_out,
					'so_sep':so_sep,
					'so_octo':so_octo,
					'so_nov':so_nov,
					'so_dec':so_dec,
					'total_rec_1':total_rec_1,
					'total_rec_2':total_rec_2,
					'total_rec_3':total_rec_3,
					'total_rec_4':total_rec_4,
					'total_rec_5':total_rec_5,
					'total_rec_6':total_rec_6,
					'total_rec_7':total_rec_7,
					'total_rec_8':total_rec_8,
					'total_rec_9':total_rec_9,
					'total_rec_10':total_rec_10,
					'total_rec_11':total_rec_11,
					'total_rec_12':total_rec_12,
					'total_dep_1':total_dep_1,
					'total_dep_2':total_dep_2,
					'total_dep_3':total_dep_3,
					'total_dep_4':total_dep_4,
					'total_dep_5':total_dep_5,
					'total_dep_6':total_dep_6,
					'total_dep_7':total_dep_7,
					'total_dep_8':total_dep_8,
					'total_dep_9':total_dep_9,
					'total_dep_10':total_dep_10,
					'total_dep_11':total_dep_11,
					'total_dep_12':total_dep_12,
					'solde_ouvert_t':solde_ouvert_t,
					'solde_ouvert_t_ch':solde_ouvert_t_ch,
					'ss':caisses[0].compute_total_dep(),
					})
		return res

	def verif_mois_existe(self,date_from,date_to, mois):
		mois1 = datetime.strptime(date_from, '%Y-%m-%d').month
		mois2 = datetime.strptime(date_to, '%Y-%m-%d').month
		if mois >= mois1 and mois <=mois2:
			return True
		else:
			return False


	@api.model
	def _get_report_values(self, docids, data=None):
		model = self.env.context.get('active_model')
		docs = self.env[model].browse(self.env.context.get('active_id'))

		return {
			'doc_ids': self.ids,
			'doc_model': model,
			'data': data['form'],
			'docs': docs,
			'time': time,
			'get_mois' : self.get_mois,
			'verif_mois_existe' : self.verif_mois_existe,
		}
