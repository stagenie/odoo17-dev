# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleAvoirExpressWizard(models.TransientModel):
    _name = 'gecafle.avoir.client.wizard'
    _description = 'Wizard de création express d\'avoir'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True,
        readonly=True
    )

    montant_vente = fields.Monetary(
        string="Montant de la vente",
        related='vente_id.montant_total_a_payer',
        readonly=True,
        currency_field='currency_id'
    )

    type_avoir = fields.Selection([
        ('non_vendu', 'Marchandise non vendue'),
        ('qualite', 'Problème de qualité'),
        ('perte', 'Perte/Détérioration'),
        ('accord_commercial', 'Accord commercial'),
        ('consigne', 'Retour consigne'),
    ], string="Type d'avoir", required=True, default='non_vendu')

    montant_avoir = fields.Monetary(
        string="Montant de l'avoir",
        required=True,
        currency_field='currency_id'
    )

    description = fields.Text(
        string="Description",
        required=True,
        default="Avoir express"
    )

    generer_avoirs_producteurs = fields.Boolean(
        string="Générer avoirs producteurs",
        default=True,
        help="Si coché, génère automatiquement les avoirs pour chaque producteur"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='vente_id.currency_id',
        readonly=True
    )

    # Champ calculé pour afficher/cacher l'option
    show_generer_producteurs = fields.Boolean(
        string="Afficher option producteurs",
        compute='_compute_show_generer_producteurs'
    )

    @api.depends('type_avoir')
    def _compute_show_generer_producteurs(self):
        """Détermine si on affiche l'option de génération des avoirs producteurs"""
        for record in self:
            # Ne pas afficher pour les consignes
            if record.type_avoir == 'consigne':
                record.show_generer_producteurs = False
                record.generer_avoirs_producteurs = False
            else:
                record.show_generer_producteurs = True
                # Utiliser la configuration par défaut
                if not record.generer_avoirs_producteurs:
                    record.generer_avoirs_producteurs = self.env.company.avoir_generer_producteurs_defaut

    @api.onchange('type_avoir')
    def _onchange_type_avoir(self):
        """Ajuste automatiquement l'option de génération selon le type"""
        company = self.env.company

        # Pour les consignes, toujours désactiver
        if self.type_avoir == 'consigne':
            self.generer_avoirs_producteurs = False
        # Pour les accords commerciaux, vérifier la configuration
        elif self.type_avoir == 'accord_commercial' and company.avoir_types_sans_producteur == 'consigne_accord':
            self.generer_avoirs_producteurs = False
        # Pour les autres, utiliser la valeur par défaut
        else:
            self.generer_avoirs_producteurs = company.avoir_generer_producteurs_defaut

    @api.constrains('montant_avoir', 'montant_vente')
    def _check_montant_avoir(self):
        for record in self:
            if record.montant_avoir <= 0:
                raise ValidationError(_("Le montant de l'avoir doit être supérieur à zéro."))
            if record.montant_avoir > record.montant_vente:
                raise ValidationError(_("Le montant de l'avoir ne peut pas dépasser le montant de la vente."))

    def action_create_avoir_express(self):
        """Crée l'avoir avec automatisation complète"""
        self.ensure_one()

        # Créer l'avoir avec le contexte d'automatisation
        avoir = self.env['gecafle.avoir.client'].with_context(
            force_automation=True,
            skip_confirmation=True
        ).create({
            'vente_id': self.vente_id.id,
            'date': fields.Date.today(),
            'type_avoir': self.type_avoir,
            'montant_avoir': self.montant_avoir,
            'description': self.description,
            'generer_avoirs_producteurs': self.generer_avoirs_producteurs,
        })

        # Retourner la vue de l'avoir créé
        return {
            'name': _('Avoir Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client',
            'res_id': avoir.id,
            'target': 'current',
        }
