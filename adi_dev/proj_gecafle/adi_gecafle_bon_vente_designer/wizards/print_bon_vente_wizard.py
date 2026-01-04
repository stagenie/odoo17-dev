# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PrintBonVenteWizard(models.TransientModel):
    """Wizard de sélection du modèle d'impression"""
    _name = 'print.bon.vente.wizard'
    _description = 'Wizard Impression Bon de Vente'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Bon de Vente",
        required=True
    )
    is_duplicata = fields.Boolean(
        string="Duplicata",
        default=False
    )
    template_id = fields.Many2one(
        'bon.vente.template.config',
        string="Modèle de rapport",
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
        help="Sélectionnez le modèle de rapport à utiliser"
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        related='vente_id.company_id',
        readonly=True
    )
    set_as_default = fields.Boolean(
        string="Définir comme modèle par défaut",
        default=False,
        help="Si coché, ce modèle sera utilisé par défaut pour les prochaines impressions"
    )

    # Aperçu des styles
    header_style = fields.Selection(
        related='template_id.header_style',
        readonly=True
    )
    body_style = fields.Selection(
        related='template_id.body_style',
        readonly=True
    )
    primary_color = fields.Char(
        related='template_id.primary_color',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Pré-sélectionner le template par défaut
        if 'template_id' in fields_list and not res.get('template_id'):
            vente_id = res.get('vente_id') or self._context.get('default_vente_id')
            if vente_id:
                vente = self.env['gecafle.vente'].browse(vente_id)
                default_template = self.env['bon.vente.template.config'].get_default_template(
                    vente.company_id.id
                )
                if default_template:
                    res['template_id'] = default_template.id
        return res

    def action_print(self):
        """Imprime le bon de vente avec le modèle sélectionné"""
        self.ensure_one()

        # Définir comme défaut si demandé
        if self.set_as_default and self.template_id:
            self.template_id.set_as_default()

        # Préparer les données pour le rapport
        data = {
            'vente_id': self.vente_id.id,
            'template_id': self.template_id.id if self.template_id else False,
            'is_duplicata': self.is_duplicata,
        }

        # Retourner l'action d'impression
        report_action = self.env.ref(
            'adi_gecafle_bon_vente_designer.action_report_bon_vente_designer'
        ).report_action(self.vente_id, data=data)

        return report_action

    def action_print_original(self):
        """Imprime avec le rapport original (ancien format)"""
        self.ensure_one()
        if self.is_duplicata:
            return self.env.ref(
                'adi_gecafle_ventes.action_report_gecafle_bon_vente_duplicata'
            ).report_action(self.vente_id)
        return self.env.ref(
            'adi_gecafle_ventes.action_report_gecafle_bon_vente'
        ).report_action(self.vente_id)

    def action_preview(self):
        """Aperçu du rapport avec le modèle sélectionné (ouvre dans un nouvel onglet)"""
        self.ensure_one()
        if not self.template_id:
            return {'type': 'ir.actions.act_window_close'}

        # Préparer les données pour le rapport
        data = {
            'vente_id': self.vente_id.id,
            'template_id': self.template_id.id,
            'is_duplicata': self.is_duplicata,
        }

        # Retourner l'action d'aperçu (rapport en mode URL)
        report = self.env.ref('adi_gecafle_bon_vente_designer.action_report_bon_vente_designer')
        report_action = report.report_action(self.vente_id, data=data)
        report_action['close_on_report_download'] = False
        return report_action
