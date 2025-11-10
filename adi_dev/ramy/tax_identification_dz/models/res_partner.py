# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResPartner(models.Model):
	_inherit = 'res.partner'

	id_international = fields.Char('ID International', help="Identificateur international")
	cni = fields.Char('CNI',size=18,help="Numéro de la carte nationale")
	tin = fields.Char('TIN',size=18,help="Numéro d'Identification National")
	nif = fields.Char('NIF',size=15,help="Numéro d'identification fiscal")
	num_article = fields.Char("Numéro d'article",size=11,help="Numéro d'article")
	nis = fields.Char("NIS",size=15,help="Numéro d'identification statistique")
	commerce_register =  fields.Char("N° de registre commerce")
	commerce_register_date =  fields.Date("Modifié le")
	ai = fields.Char("AI",help="AI")
	capital = fields.Float('Capital')
	stranger_supplier = fields.Boolean(string='Étranger',default=False)
	company_social_raison_id = fields.Many2one(string='Raison sociale',comodel_name='company.social.reason', ondelete='restrict')
	fax = fields.Char('Fax')
	supplier = fields.Boolean(string='Fournisseur')
	customer = fields.Boolean(string='Client')
	
	