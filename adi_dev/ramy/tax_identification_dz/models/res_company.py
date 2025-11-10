from odoo import models, api, fields


class ResCompany(models.Model):
	_inherit = 'res.company'

	tin = fields.Char('TIN',size=18,help="Numéro d'Identification National")
	nif = fields.Char('NIF',size=15,help="Numéro d'identification fiscal")
	num_article = fields.Char("Numéro d'article",size=11,help="Numéro d'article")
	nis = fields.Char("NIS",size=15,help="Numéro d'identification statistique")
	commerce_register_date =  fields.Date("Modifié le")
	banc_account_num =  fields.Char('N° Compte bancaire', size = 20)
	capital = fields.Monetary('Capital')
	company_social_raison_id = fields.Many2one(string='Raison sociale',comodel_name='company.social.reason', ondelete='restrict')
	office = fields.Char('Office')
	fax = fields.Char('Fax')




class ResPartnerBank(models.Model):
	_inherit = 'res.partner.bank'


	partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)])
