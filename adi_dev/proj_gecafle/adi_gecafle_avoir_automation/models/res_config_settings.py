# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Paramètres d'automatisation des avoirs
    avoir_auto_validate = fields.Boolean(
        string="Validation automatique des avoirs",
        default=True,
        help="Valide automatiquement les avoirs après création"
    )

    avoir_auto_create_credit_note = fields.Boolean(
        string="Créer automatiquement la note de crédit",
        default=True,
        help="Crée automatiquement la note de crédit après validation"
    )

    avoir_auto_post_credit_note = fields.Boolean(
        string="Comptabiliser automatiquement la note de crédit",
        default=True,
        help="Valide automatiquement la note de crédit créée"
    )

    avoir_auto_validate_producteur = fields.Boolean(
        string="Valider automatiquement les avoirs producteurs",
        default=True,
        help="Valide automatiquement les avoirs producteurs générés"
    )

    avoir_default_type = fields.Selection([
        ('non_vendu', 'Marchandise non vendue'),
        ('qualite', 'Problème de qualité'),
        ('perte', 'Perte/Détérioration'),
        ('accord_commercial', 'Accord commercial'),
        ('consigne', 'Retour consigne'),
    ], string="Type d'avoir par défaut", default='non_vendu')

    # Paramètres pour la génération des avoirs producteurs
    avoir_generer_producteurs_defaut = fields.Boolean(
        string="Générer avoirs producteurs par défaut",
        default=True,
        help="Si activé, génère automatiquement les avoirs producteurs pour les avoirs normaux (hors consigne)"
    )

    avoir_types_sans_producteur = fields.Selection([
        ('consigne', 'Uniquement les consignes'),
        ('consigne_accord', 'Consignes et accords commerciaux'),
        ('custom', 'Personnalisé'),
    ], string="Types d'avoir sans génération producteur",
        default='consigne',
        help="Types d'avoir pour lesquels on ne génère pas d'avoirs producteurs"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Champs liés aux paramètres de la société
    avoir_auto_validate = fields.Boolean(
        related='company_id.avoir_auto_validate',
        readonly=False
    )

    avoir_auto_create_credit_note = fields.Boolean(
        related='company_id.avoir_auto_create_credit_note',
        readonly=False
    )

    avoir_auto_post_credit_note = fields.Boolean(
        related='company_id.avoir_auto_post_credit_note',
        readonly=False
    )

    avoir_auto_validate_producteur = fields.Boolean(
        related='company_id.avoir_auto_validate_producteur',
        readonly=False
    )

    avoir_default_type = fields.Selection(
        related='company_id.avoir_default_type',
        readonly=False
    )

    avoir_generer_producteurs_defaut = fields.Boolean(
        related='company_id.avoir_generer_producteurs_defaut',
        readonly=False
    )

    avoir_types_sans_producteur = fields.Selection(
        related='company_id.avoir_types_sans_producteur',
        readonly=False
    )
