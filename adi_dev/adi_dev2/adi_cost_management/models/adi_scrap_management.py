# -*- coding: utf-8 -*-
# Part of ADI Cost Management Module
# Copyright (C) 2024 ADICOPS (<https://adicops-dz.com>)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class AdiScrapManagement(models.Model):
    """
    Gestion personnalisée des rebuts de production.

    Ce modèle remplace le système de rebuts standard d'Odoo pour permettre :
    - L'enregistrement des rebuts en kilogrammes
    - La distinction entre rebuts de produits finis et emballages
    - Le calcul automatique de l'impact sur le prix de revient
    - La traçabilité complète des pertes de production
    """

    _name = 'adi.scrap.management'
    _description = 'Gestion des Rebuts (Produits Finis et Emballages)'
    _rec_name = 'name'
    _order = 'scrap_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ================== CHAMPS D'IDENTIFICATION ==================

    name = fields.Char(
        'Référence',
        required=True,
        default='Nouveau',
        copy=False,
        readonly=True,
        index=True,
        tracking=True
    )

    scrap_date = fields.Date(
        'Date du Rebut',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True,
        help="Date à laquelle le rebut a été constaté"
    )

    scrap_time = fields.Datetime(
        'Date/Heure Exacte',
        default=fields.Datetime.now,
        help="Horodatage précis de l'enregistrement du rebut"
    )

    # ================== RELATIONS ==================

    daily_production_id = fields.Many2one(
        'adi.daily.production',
        'Production Journalière',
        ondelete='cascade',
        index=True,
        help="Lien vers la production journalière associée"
    )

    production_id = fields.Many2one(
        'mrp.production',
        'Ordre de Fabrication',
        help="Ordre de fabrication d'origine (optionnel)"
    )

    # ================== TYPE ET PRODUIT ==================

    scrap_type = fields.Selection([
        ('finished', 'Produit Fini'),
        ('packaging', 'Emballage'),
        ('raw', 'Matière Première')
    ],
        'Type de Rebut',
        required=True,
        default='finished',
        tracking=True,
        help="""Type de rebut :
    - Produit Fini : Impact direct sur le calcul du prix de revient
    - Emballage : Perte comptabilisée mais sans impact sur les unités
    - Matière Première : Perte avant transformation"""
    )

    product_id = fields.Many2one(
        'product.product',
        'Produit',
        required=True,
        domain="[('type', '=', 'product')]",
        tracking=True,
        help="Produit concerné par le rebut"
    )

    product_category_id = fields.Many2one(
        'product.category',
        'Catégorie',
        related='product_id.categ_id',
        store=True,
        readonly=True
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        'Unité de Mesure',
        related='product_id.uom_id',
        readonly=True,
        help="Unité de mesure principale du produit"
    )

    # ================== QUANTITÉS ET POIDS ==================

    product_weight = fields.Float(
        'Poids Unitaire (kg)',
        help="Poids d'une unité de produit fini en kilogrammes",
        default=1.0,
        digits='Product Unit of Measure'
    )

    # NOUVEAU CHAMP : Coût unitaire du produit
    product_unit_cost = fields.Monetary(
        'Coût Unitaire',
        currency_field='currency_id',
        help="Coût d'une unité de produit (récupéré automatiquement depuis le produit)",
        tracking=True
    )

    qty_kg = fields.Float(
        'Quantité Rebut (kg)',
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Quantité totale de rebut en kilogrammes"
    )

    qty_units = fields.Float(
        'Équivalent en Unités',
        compute='_compute_qty_units',
        store=True,
        readonly=True,
        digits='Product Unit of Measure',
        help="Nombre d'unités équivalentes pour les produits finis"
    )

    qty_percentage = fields.Float(
        'Pourcentage du Total',
        compute='_compute_percentages',
        store=True,
        help="Pourcentage par rapport à la production totale du jour"
    )

    # ================== COÛTS ==================

    cost_per_kg = fields.Monetary(
        'Coût par kg',
        currency_field='currency_id',
        compute='_compute_cost_per_kg',
        store=True,
        readonly=False,  # Permet la saisie manuelle si nécessaire
        tracking=True,
        help="Coût de revient par kilogramme (calculé automatiquement : Coût unitaire ÷ Poids unitaire)"
    )

    total_cost = fields.Monetary(
        'Coût Total du Rebut',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
        tracking=True,
        help="Valeur totale de la perte (Quantité kg × Coût par kg)"
    )

    currency_id = fields.Many2one(
        'res.currency',
        'Devise',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ================== RAISONS ET CLASSIFICATION ==================

    reason = fields.Text(
        'Raison du Rebut',
        help="Description détaillée de la cause du rebut"
    )

    reason_category = fields.Selection([
        ('quality', 'Défaut Qualité'),
        ('machine', 'Problème Machine'),
        ('human', 'Erreur Humaine'),
        ('material', 'Défaut Matière'),
        ('process', 'Problème Process'),
        ('other', 'Autre')
    ],
        'Catégorie de Cause',
        default='quality',
        help="Classification de la cause principale du rebut"
    )

    # ================== VALIDATION ET WORKFLOW ==================

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé')
    ],
        'État',
        default='draft',
        tracking=True,
        help="""État du rebut :
    - Brouillon : En cours de saisie
    - Confirmé : Validé par l'opérateur
    - Validé : Approuvé et comptabilisé"""
    )

    validated_by = fields.Many2one(
        'res.users',
        'Validé par',
        readonly=True,
        help="Utilisateur ayant validé le rebut"
    )

    validated_date = fields.Datetime(
        'Date de Validation',
        readonly=True
    )

    # ================== TRAÇABILITÉ ==================

    lot_id = fields.Many2one(
        'stock.lot',
        'Lot/Numéro de Série',
        domain="[('product_id', '=', product_id)]",
        help="Lot concerné par le rebut (si applicable)"
    )

    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        'Poste de Travail',
        help="Poste de travail où le rebut a été constaté"
    )

    operator_id = fields.Many2one(
        'hr.employee',
        'Opérateur',
        help="Opérateur ayant constaté le rebut"
    )

    shift = fields.Selection([
        ('morning', 'Matin'),
        ('afternoon', 'Après-midi'),
        ('night', 'Nuit')
    ],
        'Équipe',
        help="Équipe de travail lors du rebut"
    )

    # ================== INFORMATIONS COMPLÉMENTAIRES ==================

    company_id = fields.Many2one(
        'res.company',
        'Société',
        default=lambda self: self.env.company,
        required=True
    )

    notes = fields.Text(
        'Notes Internes',
        help="Notes supplémentaires pour usage interne"
    )

    corrective_action = fields.Text(
        'Actions Correctives',
        help="Actions mises en place pour éviter la récurrence"
    )

    # Champ optionnel pour la couleur dans la vue kanban
    color = fields.Integer('Couleur', default=0)

    # ================== MÉTHODES DE CALCUL ==================

    @api.model
    def create(self, vals):
        """Génération automatique de la référence à la création"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('adi.scrap.management') or 'Nouveau'

        # Log de création
        result = super().create(vals)
        _logger.info(f"Rebut créé : {result.name} - {result.qty_kg}kg de {result.product_id.name}")

        return result

    @api.depends('product_unit_cost', 'product_weight')
    def _compute_cost_per_kg(self):
        """
        Calcule automatiquement le coût par kg
        Formule : Coût/kg = Coût unitaire ÷ Poids unitaire
        Exemple : Si 1 unité coûte 1500 DA et pèse 3 kg, alors coût/kg = 500 DA
        """
        for rec in self:
            if rec.product_weight > 0 and rec.product_unit_cost > 0:
                # Calcul automatique : Prix unitaire / Poids unitaire
                rec.cost_per_kg = rec.product_unit_cost / rec.product_weight
            elif not rec.cost_per_kg:
                # Si pas de calcul possible et pas de valeur manuelle, mettre 0
                rec.cost_per_kg = 0

    @api.depends('qty_kg', 'cost_per_kg')
    def _compute_total_cost(self):
        """Calcul du coût total du rebut"""
        for rec in self:
            rec.total_cost = rec.qty_kg * rec.cost_per_kg

    @api.depends('qty_kg', 'product_weight', 'scrap_type')
    def _compute_qty_units(self):
        """Conversion kg vers unités pour les produits finis"""
        for rec in self:
            if rec.scrap_type == 'finished' and rec.product_weight > 0:
                rec.qty_units = rec.qty_kg / rec.product_weight
            else:
                rec.qty_units = 0

    @api.depends('qty_kg', 'daily_production_id.qty_produced', 'product_weight')
    def _compute_percentages(self):
        """Calcul du pourcentage par rapport à la production totale"""
        for rec in self:
            if rec.daily_production_id and rec.daily_production_id.qty_produced > 0:
                if rec.scrap_type == 'finished' and rec.product_weight > 0:
                    qty_units_scrapped = rec.qty_kg / rec.product_weight
                    rec.qty_percentage = (qty_units_scrapped / rec.daily_production_id.qty_produced) * 100
                else:
                    rec.qty_percentage = 0
            else:
                rec.qty_percentage = 0

    # ================== MÉTHODES ONCHANGE ==================

    @api.onchange('product_id')
    def _onchange_product(self):
        """Mise à jour automatique des informations produit"""
        if self.product_id:
            # Récupération du coût standard (prix de revient)
            self.product_unit_cost = self.product_id.standard_price

            # Récupération du poids depuis le champ weight du produit
            if self.product_id.weight and self.product_id.weight > 0:
                self.product_weight = self.product_id.weight
            else:
                # Valeur par défaut si le poids n'est pas défini
                self.product_weight = 1.0

            # Le coût/kg sera calculé automatiquement via @api.depends
            # Si lié à une production, récupérer le produit fini principal
            if self.daily_production_id and self.scrap_type == 'finished':
                if self.daily_production_id.product_id == self.product_id:
                    # Le poids est déjà récupéré du produit
                    pass

    @api.onchange('product_unit_cost', 'product_weight')
    def _onchange_calculate_cost_per_kg(self):
        """
        Recalcule le coût/kg quand on change le prix ou le poids unitaire
        """
        if self.product_weight > 0 and self.product_unit_cost > 0:
            self.cost_per_kg = self.product_unit_cost / self.product_weight

    @api.onchange('daily_production_id')
    def _onchange_daily_production(self):
        """Mise à jour des informations depuis la production journalière"""
        if self.daily_production_id:
            self.scrap_date = self.daily_production_id.production_date

            # Suggérer le produit principal si type = finished
            if self.scrap_type == 'finished':
                self.product_id = self.daily_production_id.product_id

    @api.onchange('scrap_type')
    def _onchange_scrap_type(self):
        """Ajustement des champs selon le type de rebut"""
        if self.scrap_type == 'packaging':
            # Pour les emballages, le poids unitaire peut être différent
            pass
        elif self.scrap_type == 'finished' and self.daily_production_id:
            # Pour les produits finis, suggérer le produit de la production
            self.product_id = self.daily_production_id.product_id

    # ================== MÉTHODES D'ACTION ==================

    def action_confirm(self):
        """Confirmer le rebut"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Seuls les rebuts en brouillon peuvent être confirmés.'))

        # Vérifications
        if self.qty_kg <= 0:
            raise ValidationError(_('La quantité doit être supérieure à 0.'))

        if self.cost_per_kg < 0:
            raise ValidationError(_('Le coût par kg ne peut pas être négatif.'))

        self.write({'state': 'confirmed'})

        # Notification
        self.message_post(
            body=f"""
            <b>Rebut confirmé</b><br/>
            • Produit : {self.product_id.name}<br/>
            • Quantité : {self.qty_kg} kg<br/>
            • Coût total : {self.total_cost:.2f} {self.currency_id.symbol}
            """
        )

    def action_validate(self):
        """Valider et comptabiliser le rebut"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Seuls les rebuts confirmés peuvent être validés.'))

        self.write({
            'state': 'validated',
            'validated_by': self.env.user.id,
            'validated_date': fields.Datetime.now()
        })

        # Mise à jour de la production journalière si liée
        if self.daily_production_id:
            self.daily_production_id._compute_scrap_costs()
            self.daily_production_id._compute_final_cost()

        # Log et notification
        _logger.info(f"Rebut validé : {self.name} - Impact: {self.total_cost} {self.currency_id.symbol}")

        self.message_post(
            body=f"""
            <b>Rebut Validé</b><br/>
            Coût Total: {self.total_cost:.2f} {self.currency_id.symbol}<br/>
            Validé par: {self.env.user.name}
            """
        )

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        if self.state == 'validated':
            raise UserError(_('Un rebut validé ne peut pas être remis en brouillon.'))

        self.write({'state': 'draft'})

        self.message_post(
            body="Rebut remis en brouillon"
        )

    # ================== MÉTHODES DE CONTRAINTE ==================

    @api.constrains('qty_kg')
    def _check_qty_kg(self):
        """Vérifier que la quantité est positive"""
        for rec in self:
            if rec.qty_kg <= 0:
                raise ValidationError(_('La quantité de rebut doit être positive.'))

    @api.constrains('cost_per_kg')
    def _check_cost_per_kg(self):
        """Vérifier que le coût est positif ou nul"""
        for rec in self:
            if rec.cost_per_kg < 0:
                raise ValidationError(_('Le coût par kg ne peut pas être négatif.'))

    @api.constrains('product_weight')
    def _check_product_weight(self):
        """Vérifier le poids pour les produits finis"""
        for rec in self:
            if rec.scrap_type == 'finished' and rec.product_weight <= 0:
                raise ValidationError(_('Le poids unitaire doit être positif pour les produits finis.'))

    # ================== MÉTHODES UTILITAIRES ==================

    @api.model
    def get_scrap_summary(self, date_from=None, date_to=None, product_id=None):
        """
        Récupérer un résumé des rebuts pour une période donnée

        :param date_from: Date de début
        :param date_to: Date de fin
        :param product_id: ID du produit (optionnel)
        :return: Dictionnaire avec les statistiques
        """
        domain = [('state', '=', 'validated')]

        if date_from:
            domain.append(('scrap_date', '>=', date_from))
        if date_to:
            domain.append(('scrap_date', '<=', date_to))
        if product_id:
            domain.append(('product_id', '=', product_id))

        scraps = self.search(domain)

        # Calculs statistiques
        total_kg = sum(scraps.mapped('qty_kg'))
        total_cost = sum(scraps.mapped('total_cost'))
        total_units = sum(scraps.mapped('qty_units'))

        # Répartition par type
        by_type = {}
        for scrap_type in ['finished', 'packaging', 'raw']:
            type_scraps = scraps.filtered(lambda s: s.scrap_type == scrap_type)
            by_type[scrap_type] = {
                'count': len(type_scraps),
                'kg': sum(type_scraps.mapped('qty_kg')),
                'cost': sum(type_scraps.mapped('total_cost'))
            }

        # Répartition par cause
        by_reason = {}
        for reason in ['quality', 'machine', 'human', 'material', 'process', 'other']:
            reason_scraps = scraps.filtered(lambda s: s.reason_category == reason)
            by_reason[reason] = {
                'count': len(reason_scraps),
                'cost': sum(reason_scraps.mapped('total_cost'))
            }

        return {
            'period': {
                'from': date_from,
                'to': date_to
            },
            'totals': {
                'count': len(scraps),
                'kg': total_kg,
                'units': total_units,
                'cost': total_cost
            },
            'by_type': by_type,
            'by_reason': by_reason,
            'currency': self.env.company.currency_id.symbol
        }

    @api.model
    def create_from_production(self, production_id, qty_kg, reason=''):
        """
        Créer un rebut depuis un ordre de fabrication

        :param production_id: ID de l'ordre de fabrication
        :param qty_kg: Quantité en kg
        :param reason: Raison du rebut
        :return: Enregistrement créé
        """
        production = self.env['mrp.production'].browse(production_id)
        if not production:
            raise ValidationError(_('Ordre de fabrication introuvable.'))

        # Recherche de la production journalière du jour
        daily_prod = self.env['adi.daily.production'].search([
            ('production_date', '=', fields.Date.today()),
            ('product_id', '=', production.product_id.id)
        ], limit=1)

        vals = {
            'production_id': production_id,
            'daily_production_id': daily_prod.id if daily_prod else False,
            'product_id': production.product_id.id,
            'qty_kg': qty_kg,
            'product_unit_cost': production.product_id.standard_price,
            'product_weight': production.product_id.weight or 1.0,
            'reason': reason,
            'scrap_type': 'finished'
        }

        return self.create(vals)

    def unlink(self):
        """Empêcher la suppression des rebuts validés"""
        for rec in self:
            if rec.state == 'validated':
                raise UserError(_('Impossible de supprimer un rebut validé.'))
        return super().unlink()
