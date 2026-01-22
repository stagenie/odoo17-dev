# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SavReturnLine(models.Model):
    _name = 'sav.return.line'
    _description = 'Ligne de Retour SAV'
    _order = 'return_id, sequence, id'

    # Relation avec le header
    return_id = fields.Many2one(
        'sav.return',
        string='Retour SAV',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help='Ordre d\'affichage des lignes',
    )

    # Champs liés au retour pour faciliter les recherches
    state = fields.Selection(
        related='return_id.state',
        string='État du Retour',
        store=True,
        readonly=True,
    )
    sales_point_id = fields.Many2one(
        related='return_id.sales_point_id',
        string='Point de Vente',
        store=True,
        readonly=True,
    )
    return_center_id = fields.Many2one(
        related='return_id.return_center_id',
        string='Centre de Retour',
        store=True,
        readonly=True,
    )

    # Informations sur l'article
    product_id = fields.Many2one(
        'product.product',
        string='Article',
        required=True,
        index=True,
    )
    category_id = fields.Many2one(
        'sav.category',
        string='Catégorie',
        required=True,
    )
    serial_number = fields.Char(
        string='N° de Série',
        required=True,
        index=True,
        help='Numéro de série unique de l\'article retourné',
    )

    # Diagnostic
    fault_type_id = fields.Many2one(
        'sav.fault.type',
        string='Motif de Retour',
        required=True,
    )
    product_condition = fields.Selection([
        ('good', 'Bon État'),
        ('damaged', 'Endommagé'),
        ('broken', 'Cassé'),
        ('incomplete', 'Incomplet'),
    ], string='État du Produit',
        required=True,
        default='good',
    )
    diagnostic = fields.Text(
        string='Diagnostic',
        help='Diagnostic technique détaillé du problème',
    )

    # Résultat de la réparation
    repair_status = fields.Selection([
        ('pending', 'En Attente'),
        ('repaired', 'Réparé'),
        ('replaced', 'Changé'),
        ('not_repairable', 'Non Réparable'),
        ('rejected', 'Refusé'),
    ], string='Statut Réparation',
        default='pending',
        required=True,
        tracking=True,
    )
    repair_notes = fields.Text(
        string='Notes de Réparation',
        help='Notes techniques sur la réparation effectuée',
    )

    # Lien avec l'origine (optionnel)
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Ligne Commande Origine',
        help='Ligne de commande d\'origine de cet article',
    )

    # Dates de suivi
    date_repaired = fields.Datetime(
        string='Date de Réparation',
        readonly=True,
    )

    # ========== Motif d'Échec (si non réparable) ==========
    failure_reason_id = fields.Many2one(
        'sav.failure.reason',
        string='Motif d\'Échec',
        help='Motif pour lequel le réparateur n\'a pas pu réparer l\'article',
    )
    failure_notes = fields.Text(
        string='Notes d\'Échec',
        help='Commentaires additionnels sur l\'échec de réparation',
    )

    # ========== Décision Usine ==========
    factory_decision = fields.Selection([
        ('factory_repaired', 'Réparé par Usine'),
        ('factory_replaced', 'Remplacé par Usine'),
        ('factory_credited', 'Avoir'),
    ], string='Décision Usine',
        help='Décision de l\'usine pour cet article',
        tracking=True,
    )
    factory_notes = fields.Text(
        string='Notes Usine',
        help='Notes de l\'usine concernant le traitement de cet article',
    )
    date_factory_decision = fields.Datetime(
        string='Date Décision Usine',
        readonly=True,
    )

    # Suivi remplacement (si factory_replaced)
    replacement_serial_number = fields.Char(
        string='N° Série Remplacement',
        help='Numéro de série de l\'article de remplacement fourni par l\'usine',
    )
    replacement_product_id = fields.Many2one(
        'product.product',
        string='Article de Remplacement',
        help='Article fourni en remplacement par l\'usine (si différent)',
    )

    # Champs calculés
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('product_id', 'serial_number')
    def _compute_display_name(self):
        """Calcule le nom d'affichage de la ligne."""
        for line in self:
            if line.product_id and line.serial_number:
                line.display_name = f"{line.product_id.name} (S/N: {line.serial_number})"
            elif line.product_id:
                line.display_name = line.product_id.name
            else:
                line.display_name = _('Nouvelle ligne')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-remplir la catégorie selon le produit."""
        if self.product_id and self.product_id.categ_id:
            # Essayer de trouver une catégorie SAV correspondante
            sav_category = self.env['sav.category'].search([
                ('name', 'ilike', self.product_id.categ_id.name)
            ], limit=1)
            if sav_category:
                self.category_id = sav_category

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Filtrer les types de panne selon la catégorie."""
        if self.category_id and self.fault_type_id:
            if self.fault_type_id.category_ids and self.category_id not in self.fault_type_id.category_ids:
                self.fault_type_id = False

    @api.onchange('repair_status')
    def _onchange_repair_status(self):
        """Remplir automatiquement la date de réparation et gérer les champs d'échec."""
        if self.repair_status in ['repaired', 'replaced', 'not_repairable', 'rejected']:
            if not self.date_repaired:
                self.date_repaired = fields.Datetime.now()
        else:
            self.date_repaired = False
        # Effacer le motif d'échec si le statut n'est plus 'non réparable'
        if self.repair_status != 'not_repairable':
            self.failure_reason_id = False
            self.failure_notes = False

    @api.onchange('factory_decision')
    def _onchange_factory_decision(self):
        """Enregistrer la date de décision usine et gérer les champs de remplacement."""
        if self.factory_decision:
            if not self.date_factory_decision:
                self.date_factory_decision = fields.Datetime.now()
        else:
            self.date_factory_decision = False
        # Effacer les champs de remplacement si la décision n'est pas 'remplacé'
        if self.factory_decision != 'factory_replaced':
            self.replacement_serial_number = False
            self.replacement_product_id = False

    @api.constrains('serial_number', 'product_id')
    def _check_unique_serial_number(self):
        """Vérifier l'unicité du numéro de série par produit dans les retours actifs."""
        for line in self:
            if line.serial_number and line.product_id:
                # Chercher d'autres lignes avec le même produit et N° série dans les retours non clôturés
                duplicate = self.env['sav.return.line'].search([
                    ('id', '!=', line.id),
                    ('product_id', '=', line.product_id.id),
                    ('serial_number', '=', line.serial_number),
                    ('state', 'not in', ['closed', 'cancelled']),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        "Le numéro de série '%s' pour le produit '%s' existe déjà dans un retour actif (Réf: %s)."
                    ) % (line.serial_number, line.product_id.name, duplicate.return_id.name))

    @api.constrains('repair_status')
    def _check_repair_status_valid(self):
        """Valider que le statut de réparation est cohérent avec l'état du retour."""
        for line in self:
            if line.repair_status != 'pending' and line.state in ['draft', 'submitted', 'received_center', 'sent_to_repairer']:
                raise ValidationError(_(
                    "Vous ne pouvez pas définir un statut de réparation avant que les articles soient en réparation."
                ))
