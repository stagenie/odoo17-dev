# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """Extension de res.company pour la configuration du designer"""
    _inherit = 'res.company'

    use_original_format = fields.Boolean(
        string="Utiliser le format original (par défaut)",
        default=True,
        help="Si coché : utilise le format original du bon de vente. "
             "Si décoché : utilise les modèles Designer personnalisés."
    )
    use_direct_print = fields.Boolean(
        string="Impression directe (sans wizard)",
        default=True,
        help="Si activé : impression directe sans afficher le wizard de sélection. "
             "Si désactivé : un wizard s'affiche pour choisir le modèle."
    )
    default_bon_vente_template_id = fields.Many2one(
        'bon.vente.template.config',
        string="Modèle Designer par défaut",
        help="Modèle Designer utilisé pour l'impression directe"
    )

    def action_open_template_config(self):
        """Ouvre la configuration des modèles de bon de vente pour cette société"""
        self.ensure_one()
        return {
            'name': 'Modèles Bon de Vente',
            'type': 'ir.actions.act_window',
            'res_model': 'bon.vente.template.config',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_preview_default_template(self):
        """Ouvre l'aperçu du modèle par défaut"""
        self.ensure_one()
        if not self.default_bon_vente_template_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucun modèle par défaut',
                    'message': 'Veuillez d\'abord sélectionner un modèle par défaut.',
                    'type': 'warning',
                }
            }
        return self.default_bon_vente_template_id.action_preview()

    def action_print_original_format(self):
        """Imprime la dernière vente avec le format original"""
        self.ensure_one()
        # Chercher la dernière vente de la société
        last_vente = self.env['gecafle.vente'].search([
            ('company_id', '=', self.id),
            ('state', '!=', 'annule')
        ], order='date_vente desc', limit=1)

        if not last_vente:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucune vente disponible',
                    'message': 'Créez d\'abord une vente pour pouvoir imprimer.',
                    'type': 'warning',
                }
            }

        # Imprimer avec le format original
        return self.env.ref(
            'adi_gecafle_ventes.action_report_gecafle_bon_vente'
        ).report_action(last_vente)
