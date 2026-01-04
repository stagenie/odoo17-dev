# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ReportBonVenteDesigner(models.AbstractModel):
    """Modèle de rapport pour préparer les données du designer"""
    _name = 'report.adi_gecafle_bon_vente_designer.report_bon_vente_designer'
    _description = 'Rapport Bon de Vente Designer'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prépare les valeurs pour le rapport QWeb"""
        # Si docids est vide, essayer de récupérer depuis data
        if not docids and data:
            vente_id = data.get('vente_id')
            if vente_id:
                docids = [vente_id] if isinstance(vente_id, int) else vente_id
                _logger.info("docids récupérés depuis data: %s", docids)

        docs = self.env['gecafle.vente'].browse(docids)

        if not docs:
            _logger.warning("No documents found for docids: %s", docids)
            return {'doc_ids': [], 'docs': [], 'doc_model': 'gecafle.vente'}

        _logger.info("=== DESIGNER REPORT ===")
        _logger.info("docids: %s", docids)
        _logger.info("docs found: %s", docs.mapped('name'))

        # Récupérer le template_id depuis les données
        template_id = data.get('template_id') if data else False
        is_duplicata = data.get('is_duplicata', False) if data else False

        _logger.info("template_id from data: %s", template_id)

        # Récupérer la configuration du template
        template_config = None
        if template_id:
            template_config = self.env['bon.vente.template.config'].browse(template_id)
            if not template_config.exists():
                template_config = None
                _logger.warning("Template %s not found!", template_id)
            else:
                _logger.info("Template found: %s", template_config.name)

        if not template_config:
            # Prendre le template par défaut
            company = docs[0].company_id if docs else self.env.company
            template_config = self.env['bon.vente.template.config'].get_default_template(company.id)
            if template_config:
                _logger.info("Using default template for company %s: %s", company.id, template_config.name)
            else:
                _logger.warning("No default template found for company %s", company.id)

        # Préparer les valeurs par défaut
        header_style = 'classic'
        body_style = 'standard'
        primary_color = '#1a5276'
        secondary_color = '#2980b9'
        accent_color = '#e74c3c'
        use_logo = True
        logo_position = 'left'
        show_border = False
        border_style = 'simple'
        show_duplicata_watermark = True
        header_info = {}

        # Si on a un template, utiliser ses valeurs
        if template_config:
            header_style = template_config.header_style or 'classic'
            body_style = template_config.body_style or 'standard'
            primary_color = template_config.primary_color or '#1a5276'
            secondary_color = template_config.secondary_color or '#2980b9'
            accent_color = template_config.accent_color or '#e74c3c'
            use_logo = template_config.use_logo
            logo_position = template_config.logo_position or 'left'
            show_border = template_config.show_border
            border_style = template_config.border_style or 'simple'
            show_duplicata_watermark = template_config.show_duplicata_watermark

            try:
                header_info = template_config.get_header_info()
            except Exception as e:
                _logger.error("Error getting header info: %s", e)
                header_info = self._get_default_header_info(docs[0].company_id)
        else:
            # Utiliser les infos de la société par défaut
            header_info = self._get_default_header_info(docs[0].company_id if docs else self.env.company)

        _logger.info("Final values: header_style=%s, body_style=%s", header_style, body_style)
        _logger.info("Colors: primary=%s, secondary=%s, accent=%s", primary_color, secondary_color, accent_color)

        return {
            'doc_ids': docids,
            'doc_model': 'gecafle.vente',
            'docs': docs,
            'data': data or {},
            'template_config': template_config,
            'is_duplicata': is_duplicata,
            'header_info': header_info,
            # Passer les valeurs directement pour éviter les problèmes avec .new()
            'primary_color': primary_color,
            'secondary_color': secondary_color,
            'accent_color': accent_color,
            'header_style': header_style,
            'body_style': body_style,
            'use_logo': use_logo,
            'logo_position': logo_position,
            'show_border': show_border,
            'border_style': border_style,
            'show_duplicata_watermark': show_duplicata_watermark,
        }

    def _get_default_header_info(self, company):
        """Retourne les infos d'en-tête par défaut depuis la société"""
        return {
            'title': company.name or '',
            'subtitle': '',
            'address_line1': company.street or '',
            'address_line2': f"{company.zip or ''} {company.city or ''}, {company.country_id.name or ''}".strip(', '),
            'phone1': company.phone or '',
            'phone2': '',
            'mobile': getattr(company, 'mobile', '') or '',
            'fax': '',
            'email': company.email or '',
            'website': company.website or '',
            'rc': '',
            'nif': company.vat or '',
            'nis': '',
            'ai': '',
            'logo': company.logo,
        }
