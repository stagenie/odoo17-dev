# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
import odoo.addons.decimal_precision as dp

class type_caisse(models.Model):
	_name = "type.caisse"

	name = fields.Char('Nom')
	code = fields.Char('Code')
	is_from = fields.Boolean('Atoriser depuis')
	is_to = fields.Boolean('Atoriser vers')
	last_caisse_id = fields.Many2one('caisse', 'Dernière caisse fermée')
