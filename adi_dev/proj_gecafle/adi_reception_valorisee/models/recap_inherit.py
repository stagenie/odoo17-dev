# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleReceptionRecap(models.Model):
    _inherit = 'gecafle.reception.recap'

    @api.depends('reception_id.is_achat_valorise')
    def _compute_can_create_invoice(self):
        """Détermine si on peut créer une facture producteur depuis le récap"""
        for record in self:
            # Ne pas permettre si la réception est un achat valorisé
            record.can_create_invoice = not record.reception_id.is_achat_valorise

    can_create_invoice = fields.Boolean(
        compute='_compute_can_create_invoice',
        string="Peut créer facture"
    )

    reception_is_valorisee = fields.Boolean(
        string="Réception valorisée",
        compute='_compute_reception_is_valorisee',
        store=True
    )

    @api.depends('reception_id')
    def _compute_reception_is_valorisee(self):
        for record in self:
            record.reception_is_valorisee = record.reception_id.is_achat_valorise if record.reception_id else False

    def action_create_vendor_invoice(self):
        """Surcharge pour bloquer la création depuis une réception valorisée"""
        self.ensure_one()

        # Vérifier si la réception est valorisée
        if self.reception_is_valorisee:
            raise UserError(_(
                "Impossible de créer une facture producteur depuis ce récapitulatif.\n"
                "La réception %s est de type 'Achat Valorisé'.\n"
                "La facture doit être créée directement depuis la réception."
            ) % self.reception_id.name)

        # Appeler la méthode parent si tout est OK
        return super().action_create_vendor_invoice()
