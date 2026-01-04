# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BonVenteTemplateConfig(models.Model):
    """Configuration des templates de Bon de Vente"""
    _name = 'bon.vente.template.config'
    _description = 'Configuration Template Bon de Vente'
    _rec_name = 'name'

    name = fields.Char(
        string="Nom du modèle",
        required=True,
        help="Nom descriptif du modèle de rapport"
    )
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(
        string="Modèle par défaut",
        default=False,
        help="Si coché, ce modèle sera utilisé par défaut"
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True
    )

    # ========== STYLE EN-TÊTE ==========
    header_style = fields.Selection([
        ('classic', 'Classique Élégant'),
        ('modern', 'Moderne Corporate'),
        ('premium', 'Premium Luxe'),
    ], string="Style d'en-tête", default='classic', required=True)

    # ========== STYLE CORPS ==========
    body_style = fields.Selection([
        ('standard', 'Standard Amélioré'),
        ('modern', 'Moderne Card-Based'),
        ('premium', 'Premium Minimaliste'),
    ], string="Style du corps", default='standard', required=True)

    # ========== INFORMATIONS EN-TÊTE PERSONNALISABLES ==========
    use_custom_header = fields.Boolean(
        string="Personnaliser l'en-tête",
        default=False,
        help="Permet de saisir manuellement les informations d'en-tête"
    )
    custom_title = fields.Char(
        string="Titre de l'entreprise",
        help="Ex: SOCIÉTÉ GECAFLE SARL"
    )
    custom_subtitle = fields.Char(
        string="Sous-titre / Activité",
        help="Ex: Marché de Gros Fruits & Légumes"
    )
    custom_address_line1 = fields.Char(
        string="Adresse ligne 1",
        help="Ex: Zone Industrielle, Lot 42"
    )
    custom_address_line2 = fields.Char(
        string="Adresse ligne 2",
        help="Ex: 16000 Alger, Algérie"
    )
    custom_phone1 = fields.Char(
        string="Téléphone 1",
        help="Ex: 021 XX XX XX"
    )
    custom_phone2 = fields.Char(
        string="Téléphone 2",
        help="Ex: 023 XX XX XX"
    )
    custom_mobile = fields.Char(
        string="Mobile",
        help="Ex: 0XX XX XX XX"
    )
    custom_fax = fields.Char(
        string="Fax",
        help="Ex: 021 XX XX XX"
    )
    custom_email = fields.Char(
        string="Email",
        help="Ex: contact@gecafle.dz"
    )
    custom_website = fields.Char(
        string="Site Web",
        help="Ex: www.gecafle.dz"
    )
    custom_rc = fields.Char(
        string="N° RC",
        help="Numéro du Registre de Commerce"
    )
    custom_nif = fields.Char(
        string="NIF",
        help="Numéro d'Identification Fiscale"
    )
    custom_nis = fields.Char(
        string="NIS",
        help="Numéro d'Identification Statistique"
    )
    custom_ai = fields.Char(
        string="Article d'Imposition",
        help="Numéro d'Article d'Imposition"
    )

    # ========== LOGO ==========
    use_logo = fields.Boolean(
        string="Afficher le logo",
        default=True
    )
    custom_logo = fields.Binary(
        string="Logo personnalisé",
        help="Si vide, utilise le logo de la société"
    )
    logo_position = fields.Selection([
        ('left', 'Gauche'),
        ('center', 'Centre'),
        ('right', 'Droite'),
    ], string="Position du logo", default='left')

    # ========== COULEURS ==========
    primary_color = fields.Char(
        string="Couleur principale",
        default="#1a5276",
        help="Couleur principale du rapport (format HEX)"
    )
    secondary_color = fields.Char(
        string="Couleur secondaire",
        default="#2980b9",
        help="Couleur secondaire du rapport (format HEX)"
    )
    accent_color = fields.Char(
        string="Couleur d'accent",
        default="#e74c3c",
        help="Couleur d'accent pour les éléments importants"
    )

    # ========== OPTIONS D'AFFICHAGE ==========
    show_duplicata_watermark = fields.Boolean(
        string="Filigrane DUPLICATA",
        default=True,
        help="Affiche un filigrane sur les duplicatas"
    )
    show_border = fields.Boolean(
        string="Bordure du document",
        default=False,
        help="Ajoute une bordure autour du document"
    )
    border_style = fields.Selection([
        ('simple', 'Simple'),
        ('double', 'Double'),
        ('elegant', 'Élégante'),
    ], string="Style de bordure", default='simple')

    @api.model
    def get_default_template(self, company_id=None):
        """Retourne le template par défaut pour une société"""
        domain = [('is_default', '=', True)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        template = self.search(domain, limit=1)
        if not template:
            # Retourne le premier template actif
            domain = [('active', '=', True)]
            if company_id:
                domain.append(('company_id', '=', company_id))
            template = self.search(domain, limit=1)
        return template

    def set_as_default(self):
        """Définit ce template comme défaut"""
        self.ensure_one()
        # Désactiver les autres templates par défaut de la même société
        self.search([
            ('company_id', '=', self.company_id.id),
            ('is_default', '=', True),
            ('id', '!=', self.id)
        ]).write({'is_default': False})
        self.is_default = True

    def get_header_info(self):
        """Retourne les informations d'en-tête à utiliser"""
        self.ensure_one()
        company = self.company_id

        if self.use_custom_header:
            return {
                'title': self.custom_title or company.name,
                'subtitle': self.custom_subtitle or '',
                'address_line1': self.custom_address_line1 or company.street or '',
                'address_line2': self.custom_address_line2 or f"{company.zip or ''} {company.city or ''}, {company.country_id.name or ''}",
                'phone1': self.custom_phone1 or company.phone or '',
                'phone2': self.custom_phone2 or '',
                'mobile': self.custom_mobile or company.mobile or '',
                'fax': self.custom_fax or '',
                'email': self.custom_email or company.email or '',
                'website': self.custom_website or company.website or '',
                'rc': self.custom_rc or '',
                'nif': self.custom_nif or company.vat or '',
                'nis': self.custom_nis or '',
                'ai': self.custom_ai or '',
                'logo': self.custom_logo if self.custom_logo else company.logo,
            }
        else:
            return {
                'title': company.name,
                'subtitle': '',
                'address_line1': company.street or '',
                'address_line2': f"{company.zip or ''} {company.city or ''}, {company.country_id.name or ''}",
                'phone1': company.phone or '',
                'phone2': '',
                'mobile': company.mobile or '',
                'fax': '',
                'email': company.email or '',
                'website': company.website or '',
                'rc': '',
                'nif': company.vat or '',
                'nis': '',
                'ai': '',
                'logo': company.logo,
            }

    def action_preview(self):
        """Ouvre l'aperçu du modèle avec la dernière vente de la société"""
        self.ensure_one()
        # Chercher la dernière vente de la société pour l'aperçu
        last_vente = self.env['gecafle.vente'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '!=', 'annule')
        ], order='date_vente desc', limit=1)

        if not last_vente:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucune vente disponible',
                    'message': 'Créez d\'abord une vente pour pouvoir prévisualiser ce modèle.',
                    'type': 'warning',
                }
            }

        # Générer l'aperçu avec ce template
        data = {
            'vente_id': last_vente.id,
            'template_id': self.id,
            'is_duplicata': False,
        }
        return self.env.ref(
            'adi_gecafle_bon_vente_designer.action_report_bon_vente_designer'
        ).report_action(last_vente, data=data)

    def action_set_as_company_default(self):
        """Définit ce modèle comme modèle par défaut de la société"""
        self.ensure_one()
        self.set_as_default()
        self.company_id.default_bon_vente_template_id = self.id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Modèle par défaut',
                'message': f'"{self.name}" est maintenant le modèle par défaut de la société.',
                'type': 'success',
            }
        }
