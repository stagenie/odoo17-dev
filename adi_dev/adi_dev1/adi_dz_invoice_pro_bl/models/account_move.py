# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AcountMove(models.Model):
    _inherit = "account.move"

    num_fact = fields.Char( string="Num de Facture")
    num_bl = fields.Char( string="Num de  BL")
    num_pro = fields.Char( string="Num Proforma")


    def _get_name_invoice_report_adi_pro(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'adi_dz_invoice_pro_bl.adi_report_invoice_document'

    def _get_name_invoice_report_adi_item_pro(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'adi_dz_invoice_pro_bl.adi_report_invoice_document_item'

    def _get_name_invoice_report_adi_item_pro_nv(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'adi_dz_invoice_pro_bl.adi_report_invoice_document_item_nv'

class AcountReporte(models.Model):
    _inherit = "account.report"


