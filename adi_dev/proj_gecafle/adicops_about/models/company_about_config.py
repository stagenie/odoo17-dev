# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CompanyAboutConfig(models.Model):
    _name = 'company.about.config'
    _description = 'Configuration des informations société intégratrice'


    # Informations de base
    name = fields.Char("Nom", default= "A propos d'ADICOPS")
    company_name = fields.Char(
        'Nom de la société',
        required=True,
        help="Nom de la société intégratrice"
    )

    slogan = fields.Char(
        'Slogan',
        help="Slogan ou phrase d'accroche de la société"
    )
    tel_mob = fields.Char(
        'Tel / Mob',
        help="TEl / Mob société"
    )

    address = fields.Text(
        'Adresse complète',
        help="Adresse complète de la société"
    )

    experience_years = fields.Integer(
        'Années d\'expérience',
        default=1,
        help="Nombre d'années d'expérience dans le domaine"
    )

    domain = fields.Selection([
        ('agro_alimentaire', 'Agro-alimentaire'),
        ('industrie', 'Industrie'),
        ('service', 'Service'),
        ('retail', 'Commerce de détail'),
        ('healthcare', 'Santé'),
        ('education', 'Éducation'),
        ('finance', 'Finance'),
        ('technology', 'Technologie'),
        ('construction', 'Construction'),
        ('other', 'Autre'),
    ], string='Domaine d\'activité',
        help="Domaine principal d'intervention de la société")

    app_name = fields.Char(
        'Nom de l\'application',
        help="Nom personnalisé de l'application Odoo"
    )

    # Logo de la société
    logo = fields.Binary(
        'Logo de la société',
        help="Logo qui sera affiché sur la page About"
    )

    # Champs techniques
    active = fields.Boolean('Actif', default=True)
    is_default = fields.Boolean(
        'Configuration par défaut',
        default=True,
        help="Une seule configuration peut être par défaut"
    )

    @api.constrains('experience_years')
    def _check_experience_years(self):
        """Vérifier que le nombre d'années d'expérience est positif."""
        for record in self:
            if record.experience_years < 0:
                raise ValidationError(
                    "Le nombre d'années d'expérience doit être positif !"
                )

    @api.constrains('is_default')
    def _check_unique_default(self):
        """S'assurer qu'il n'y a qu'une seule configuration par défaut."""
        for record in self:
            if record.is_default:
                existing = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        "Une seule configuration peut être définie par défaut !"
                    )

    @api.model
    def get_default_config(self):
        """Récupérer la configuration par défaut."""
        config = self.search([('is_default', '=', True)], limit=1)
        if not config:
            config = self.search([], limit=1)
        return config

    def name_get(self):
        """Affichage personnalisé du nom dans les listes."""
        result = []
        for record in self:
            name = record.company_name or 'Configuration sans nom'
            if record.is_default:
                name += ' (Par défaut)'
            result.append((record.id, name))
        return result

    def action_view_about(self):
        """Action pour afficher la page About."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'À Propos de Notre Société',
            'res_model': 'company.about.config',
            'view_mode': 'about',
            'res_id': self.id,
            'target': 'current',
        }


class CompanyAboutDisplay(models.TransientModel):
    _name = 'company.about.display'
    _description = 'Affichage des informations About'

    def default_get(self, fields_list):
        """Récupérer la configuration par défaut."""
        res = super().default_get(fields_list)
        config_model = self.env['company.about.config']
        config = config_model.get_default_config()
        if config:
            res.update({
                'config_id': config.id,
                'company_name': config.company_name,
                'slogan': config.slogan,
                'address': config.address,
                'experience_years': config.experience_years,
                'domain': config.domain,
                'tel_mob': config.tel_mob,
                'app_name': config.app_name,
                'logo': config.logo,
            })
        return res

    # Champs miroir pour l'affichage
    config_id = fields.Many2one('company.about.config', 'Configuration')
    company_name = fields.Char('Nom de la société', readonly=True)
    name = fields.Char('Nom de la société', default=" A Propos d'ADICOPS", readonly=True)
    slogan = fields.Char('Slogan', readonly=True)
    tel_mob = fields.Char(
        'Tel / Mob',
        help="TEl / Mob société"
    )
    address = fields.Text('Adresse complète', readonly=True)
    experience_years = fields.Integer('Années d\'expérience', readonly=True)
    domain = fields.Selection([
        ('agro_alimentaire', 'Agro-alimentaire'),
        ('industrie', 'Industrie'),
        ('service', 'Service'),
        ('retail', 'Commerce de détail'),
        ('healthcare', 'Santé'),
        ('education', 'Éducation'),
        ('finance', 'Finance'),
        ('technology', 'Technologie'),
        ('construction', 'Construction'),
        ('other', 'Autre'),
    ], string='Domaine d\'activité', readonly=True)
    app_name = fields.Char('Nom de l\'application', readonly=True)
    logo = fields.Binary('Logo de la société', readonly=True)

    def action_edit_config(self):
        """Action pour éditer la configuration (admin seulement)."""
        if not self.env.user.has_group('base.group_system'):
            raise ValidationError("Seuls les administrateurs peuvent modifier la configuration !")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Modifier la Configuration About',
            'res_model': 'company.about.config',
            'view_mode': 'form',
            'res_id': self.config_id.id if self.config_id else False,
            'target': 'current',
        }
