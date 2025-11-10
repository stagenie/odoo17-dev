# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class GecafleRecapPrintWizard(models.TransientModel):
    _name = 'gecafle.recap.print.wizard'
    _description = "Options d'impression du récapitulatif"

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True
    )

    sort_by_quality = fields.Boolean(
        string="Trier par qualité",
        default=True,
        help="Trier les lignes par qualité (de la meilleure à la plus basse)"
    )

    show_commission_pct = fields.Boolean(
        string="Afficher le pourcentage de commission",
        default=False,
        help="Afficher les pourcentages de commission appliqués au producteur"
    )

    def action_print_report(self):
        """Lance l'impression du rapport avec les options sélectionnées"""
        self.ensure_one()

        # Récupérer les lignes ordonnées si demandé
        recap_lines = self.recap_id.recap_line_ids
        if self.sort_by_quality:
            recap_lines = self.recap_id.recap_line_ids.sorted(
                key=lambda r: r.qualite_id.classification if r.qualite_id and hasattr(r.qualite_id, 'classification') else 99
            )

        # Retourner l'action du rapport
        return {
            'type': 'ir.actions.report',
            'report_name': 'adi_gecafle_ventes.report_reception_recap',
            'report_type': 'qweb-pdf',
            'data': {
                'show_commission_pct': self.show_commission_pct,
                'ordered_lines': recap_lines.ids
            },
            'context': {
                'active_model': 'gecafle.reception.recap',
                'active_id': self.recap_id.id,
            }
        }
