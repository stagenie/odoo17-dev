# -*- coding: utf-8 -*-
from odoo import models, fields, api


class GecafleVenteDesigner(models.Model):
    """Extension du modèle gecafle.vente pour le designer"""
    _inherit = 'gecafle.vente'

    def _use_original_format(self):
        """Vérifie si on doit utiliser le format original"""
        try:
            return self.company_id.use_original_format
        except Exception:
            return True  # Par défaut, format original

    def _get_use_direct_print(self):
        """Retourne la valeur de use_direct_print avec valeur par défaut True"""
        try:
            return self.company_id.use_direct_print
        except Exception:
            return True

    def _get_default_template(self):
        """Retourne le modèle par défaut pour cette vente"""
        # D'abord vérifier le template défini sur la société
        try:
            if self.company_id.default_bon_vente_template_id:
                return self.company_id.default_bon_vente_template_id
        except Exception:
            pass
        # Sinon chercher un template par défaut
        return self.env['bon.vente.template.config'].get_default_template(self.company_id.id)

    def action_open_print_wizard(self):
        """
        Logique d'impression:
        1. Si use_original_format = True → Format original
        2. Sinon (Designer):
           - use_direct_print = True → Impression directe avec template par défaut
           - use_direct_print = False → Ouvre le wizard
        """
        self.ensure_one()

        # 1. Format original si activé
        if self._use_original_format():
            return self.env.ref(
                'adi_gecafle_ventes.action_report_gecafle_bon_vente'
            ).report_action(self)

        # 2. Mode Designer
        if self._get_use_direct_print():
            # Impression directe avec le modèle par défaut
            default_template = self._get_default_template()
            if default_template:
                data = {
                    'vente_id': self.id,
                    'template_id': default_template.id,
                    'is_duplicata': False,
                }
                return self.env.ref(
                    'adi_gecafle_bon_vente_designer.action_report_bon_vente_designer'
                ).report_action(self, data=data)

        # Ouvrir le wizard de sélection
        return {
            'name': 'Imprimer Bon de Vente',
            'type': 'ir.actions.act_window',
            'res_model': 'print.bon.vente.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vente_id': self.id,
                'default_is_duplicata': False,
            }
        }

    def action_open_print_wizard_duplicata(self):
        """
        Logique d'impression duplicata:
        1. Si use_original_format = True → Format original duplicata
        2. Sinon (Designer):
           - use_direct_print = True → Impression directe avec template par défaut
           - use_direct_print = False → Ouvre le wizard
        """
        self.ensure_one()

        # 1. Format original si activé
        if self._use_original_format():
            return self.env.ref(
                'adi_gecafle_ventes.action_report_gecafle_bon_vente_duplicata'
            ).report_action(self)

        # 2. Mode Designer
        if self._get_use_direct_print():
            # Impression directe avec le modèle par défaut
            default_template = self._get_default_template()
            if default_template:
                data = {
                    'vente_id': self.id,
                    'template_id': default_template.id,
                    'is_duplicata': True,
                }
                return self.env.ref(
                    'adi_gecafle_bon_vente_designer.action_report_bon_vente_designer'
                ).report_action(self, data=data)

        # Ouvrir le wizard de sélection
        return {
            'name': 'Imprimer Duplicata',
            'type': 'ir.actions.act_window',
            'res_model': 'print.bon.vente.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vente_id': self.id,
                'default_is_duplicata': True,
            }
        }

    def get_template_config(self, template_id=None):
        """Retourne la configuration du template à utiliser"""
        self.ensure_one()
        if template_id:
            return self.env['bon.vente.template.config'].browse(template_id)
        # Vérifier d'abord le template par défaut de la société
        try:
            if self.company_id.default_bon_vente_template_id:
                return self.company_id.default_bon_vente_template_id
        except Exception:
            pass
        return self.env['bon.vente.template.config'].get_default_template(self.company_id.id)
