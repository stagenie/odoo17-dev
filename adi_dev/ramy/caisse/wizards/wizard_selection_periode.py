# -*- coding: utf-8 -*-
from odoo import models, fields, api
import time

class wizard_selection_periode(models.TransientModel):
    _name = 'wizard.selection.periode'

    date_from = fields.Date('Date début',required=True, default=time.strftime('%Y-01-01'))
    date_to = fields.Date('Date fin',required=True, default=time.strftime('%Y-12-31'))

    type_caisse_id = fields.Many2one('type.caisse', string='Caisse')

    def imprimer(self):
        data = {}   
        data['form'] = self.read(['date_from','date_to','type_caisse_id'])[0]

        # return self.env.ref('caisse.caisse').report_action(self,data=data) 
        return self.env.ref('caisse.action_report_caisse').report_action(self,data=data) 