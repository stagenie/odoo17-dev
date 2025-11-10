# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BordereauPrintWizard(models.TransientModel):
    _name = 'gecafle.bordereau.print.wizard'
    _description = 'Options d\'impression du bordereau'

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True,
        readonly=True
    )

    # Option modifiée : regroupement visuel au lieu de fusion
    group_by_product = fields.Boolean(
        string="Regrouper visuellement par produit",
        default=True,
        help="Affiche les produits identiques ensemble, triés par prix décroissant dans chaque groupe"
    )

    report_language = fields.Selection([
        ('fr', 'Français'),
        ('ar', 'Arabe - العربية')
    ], string="Langue du rapport", default='fr', required=True)

    def action_print_bordereau(self):
        """Lance l'impression avec les options sélectionnées"""
        self.ensure_one()

        if not self.recap_id:
            raise UserError(_("Aucun récapitulatif sélectionné"))

        # Déterminer quelle action utiliser selon les options
        # 4 cas possibles : (regroupé/non-regroupé) x (fr/ar)

        if self.report_language == 'ar':
            if self.group_by_product:
                action_ref = 'adi_gecafle_reception_extended.action_report_bordereau_grouped_ar'
            else:
                action_ref = 'adi_gecafle_reception_extended.action_report_bordereau_simple_ar'
        else:  # français
            if self.group_by_product:
                action_ref = 'adi_gecafle_reception_extended.action_report_bordereau_grouped_fr'
            else:
                action_ref = 'adi_gecafle_reception_extended.action_report_bordereau_simple_fr'

        _logger.info("Impression avec action: %s", action_ref)

        return self.env.ref(action_ref).report_action(self.recap_id)
