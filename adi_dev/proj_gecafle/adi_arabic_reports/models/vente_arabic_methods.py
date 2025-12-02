# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class GecafleVenteArabic(models.Model):
    _inherit = 'gecafle.vente'

    def action_print_bon_vente_ar(self):
        """Imprime le bon de vente en arabe (normal)"""
        self.ensure_one()

        # Utiliser l'action normale qui appelle report_bon_vente_normal_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_vente_ar').report_action(self)

    def action_print_bon_de_pese_ar(self):
        """Imprime le bon de Pesé en arabe (normal)"""
        self.ensure_one()
        # Utiliser l'action normale qui appelle report_bon_vente_normal_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_pese_ar').report_action(self)

    def action_print_bon_vente_duplicata_ar(self):
        """Imprime le duplicata du bon de vente en arabe"""
        self.ensure_one()


        # Utiliser l'action duplicata dédiée qui appelle report_bon_vente_duplicata_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_vente_duplicata_ar').report_action(self)


class GecafleReceptionArabic(models.Model):
    _inherit = 'gecafle.reception'

    def action_print_bon_reception_ar(self):
        """Imprime le bon de réception en arabe (normal)"""
        self.ensure_one()

        # Utiliser l'action normale qui appelle report_bon_reception_normal_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_reception_ar').report_action(self)

    def action_print_bon_reception_duplicata_ar(self):
        """Imprime le duplicata du bon de réception en arabe"""
        self.ensure_one()



        # Utiliser l'action duplicata dédiée qui appelle report_bon_reception_duplicata_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_reception_duplicata_ar').report_action(self)

    def action_print_bon_reception_ticket_ar(self):
        """Imprime le bon de réception en format ticket (80mm)"""
        self.ensure_one()

        # Utiliser l'action ticket qui appelle report_bon_reception_ticket_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_reception_ticket_ar').report_action(self)

    def action_print_bon_reception_ticket_duplicata_ar(self):
        """Imprime le duplicata du bon de réception en format ticket (80mm)"""
        self.ensure_one()

        # Utiliser l'action ticket duplicata qui appelle report_bon_reception_ticket_duplicata_ar
        return self.env.ref('adi_arabic_reports.action_report_bon_reception_ticket_duplicata_ar').report_action(self)


class AccountMoveArabic(models.Model):
    _inherit = 'account.move'

    def action_print_bon_vente_ar(self):
        """Imprime le bon de vente en arabe depuis la facture"""
        self.ensure_one()
        if not self.gecafle_vente_id:
            raise UserError(_("Cette facture n'est pas liée à un bon de vente."))


        return self.gecafle_vente_id.action_print_bon_vente_ar()

    def action_print_bon_vente_duplicata_ar(self):
        """Imprime le duplicata du bon de vente en arabe depuis la facture"""
        self.ensure_one()
        if not self.gecafle_vente_id:
            raise UserError(_("Cette facture n'est pas liée à un bon de vente."))

        return self.gecafle_vente_id.action_print_bon_vente_duplicata_ar()
