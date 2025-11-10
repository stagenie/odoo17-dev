# -*- coding: utf-8 -*-
from odoo import fields, models, api


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    default_print_option = fields.Selection(
        selection=[
            ('print', 'Imprimer'),
            ('download', 'Télécharger'),
            ('open', 'Ouvrir dans un nouvel onglet')
        ],
        string='Option d\'impression par défaut',
        help="Définit l'action par défaut lors de la génération d'un rapport PDF"
    )

    def _get_readable_fields(self):
        """Ajouter le champ aux champs lisibles pour l'API"""
        result = super()._get_readable_fields()
        result.add('default_print_option')
        return result

    def report_action(self, docids, data=None, config=True):
        """Surcharge pour ajouter l'option d'impression au contexte"""
        result = super().report_action(docids, data, config)
        # Ajouter uniquement pour les rapports PDF
        if self.report_type == 'qweb-pdf':
            result.update({
                'id': self.id,
                'default_print_option': self.default_print_option or False,
            })
        return result
