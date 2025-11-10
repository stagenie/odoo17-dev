# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AcountMove(models.Model):
    _inherit = "account.move"     
    
    bank_sending = fields.Many2one('res.partner.bank', string='Compte Bancaire')
    

    def _get_name_invoice_report_adi(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'adi_dz_reports.adi_report_invoice_document'

    def _get_name_invoice_report_adi_item(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'adi_dz_reports.adi_report_invoice_document_item'

class AcountReporte(models.Model):
    _inherit = "account.report"


class AcountMoveLine(models.Model):
    _inherit = "account.move.line"     
    # Ajout des champs liés à SIEMTEC 
    item = fields.Char("Item")
    partnumber = fields.Char("Part Number")