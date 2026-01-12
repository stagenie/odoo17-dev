# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SavReturn(models.Model):
    _name = 'sav.return'
    _description = 'Retour SAV'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True,
        domain="[('customer_rank', '>', 0)]",
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    # Article retourné
    filter_from_picking = fields.Boolean(
        string='Filtrer depuis BL',
        default=False,
        help='Si coché, seuls les articles du bon de livraison sélectionné seront disponibles',
    )
    available_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_available_product_ids',
        string='Produits Disponibles',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Article Retourné',
        required=True,
        tracking=True,
    )
    category_id = fields.Many2one(
        'sav.category',
        string='Catégorie',
        required=True,
        tracking=True,
    )
    serial_number = fields.Char(
        string='Numéro de Série',
        required=True,
        tracking=True,
        help='Numéro de série du produit retourné',
    )

    # Origine de la vente (optionnel)
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Bon de Vente Origine',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['sale', 'done'])]",
        tracking=True,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Bon de Livraison Origine',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
        tracking=True,
    )
    sale_date = fields.Datetime(
        string='Date de Vente',
        related='sale_order_id.date_order',
        store=True,
    )

    # Motif et état
    fault_type_id = fields.Many2one(
        'sav.fault.type',
        string='Motif de Retour',
        required=True,
        tracking=True,
    )
    product_condition = fields.Selection([
        ('good', 'Bon État'),
        ('damaged', 'Endommagé'),
        ('broken', 'Cassé'),
        ('incomplete', 'Incomplet'),
    ], string='État du Produit',
        required=True,
        default='good',
        tracking=True,
    )
    action_taken = fields.Selection([
        ('repaired', 'Réparé'),
        ('replaced', 'Changé'),
        ('refunded', 'Remboursé'),
        ('rejected', 'Refusé'),
    ], string='Action',
        tracking=True,
    )

    # Statut / Workflow
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('received', 'Reçu'),
        ('in_progress', 'En Réparation'),
        ('repaired', 'Réparé'),
        ('not_repaired', 'Non Réparé'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ], string='Statut',
        required=True,
        default='draft',
        tracking=True,
        group_expand='_expand_states',
    )

    # État du document
    doc_state = fields.Selection([
        ('none', 'Aucun'),
        ('repair_order', 'Bon de Réparation'),
        ('delivery_order', 'Bon de Livraison'),
    ], string='Type de Document',
        default='none',
        tracking=True,
    )

    # Observations
    observations = fields.Text(
        string='Observations',
    )
    diagnostic = fields.Text(
        string='Diagnostic',
    )
    repair_notes = fields.Text(
        string='Notes de Réparation',
    )

    # Dates de suivi
    reception_date = fields.Datetime(
        string='Date de Réception',
        readonly=True,
    )
    repair_start_date = fields.Datetime(
        string='Début Réparation',
        readonly=True,
    )
    repair_end_date = fields.Datetime(
        string='Fin Réparation',
        readonly=True,
    )
    delivery_date = fields.Datetime(
        string='Date de Livraison',
        readonly=True,
    )

    # Champs calculés pour les statistiques
    repair_duration = fields.Float(
        string='Durée Réparation (jours)',
        compute='_compute_repair_duration',
        store=True,
    )
    total_duration = fields.Float(
        string='Durée Totale (jours)',
        compute='_compute_total_duration',
        store=True,
    )

    # Couleur pour Kanban
    color = fields.Integer(
        string='Couleur',
        compute='_compute_color',
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Bas'),
        ('2', 'Moyen'),
        ('3', 'Urgent'),
    ], string='Priorité',
        default='0',
    )

    @api.model
    def _expand_states(self, states, domain, order):
        """Expand all states for kanban view."""
        return [key for key, val in self._fields['state'].selection]

    @api.depends('picking_id', 'filter_from_picking')
    def _compute_available_product_ids(self):
        """Calculer les produits disponibles selon le BL sélectionné."""
        for rec in self:
            if rec.filter_from_picking and rec.picking_id:
                rec.available_product_ids = rec.picking_id.move_ids.mapped('product_id')
            else:
                # Retourner False pour ne pas filtrer (tous les produits disponibles)
                rec.available_product_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sav.return') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('repair_start_date', 'repair_end_date')
    def _compute_repair_duration(self):
        for rec in self:
            if rec.repair_start_date and rec.repair_end_date:
                delta = rec.repair_end_date - rec.repair_start_date
                rec.repair_duration = delta.total_seconds() / 86400  # Convertir en jours
            else:
                rec.repair_duration = 0

    @api.depends('reception_date', 'delivery_date')
    def _compute_total_duration(self):
        for rec in self:
            if rec.reception_date and rec.delivery_date:
                delta = rec.delivery_date - rec.reception_date
                rec.total_duration = delta.total_seconds() / 86400
            else:
                rec.total_duration = 0

    @api.depends('state')
    def _compute_color(self):
        color_map = {
            'draft': 0,
            'received': 4,      # Bleu clair
            'in_progress': 3,   # Jaune
            'repaired': 10,     # Vert
            'not_repaired': 1,  # Rouge
            'delivered': 10,    # Vert
            'cancelled': 1,     # Rouge
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Récupérer les informations depuis le bon de vente."""
        if self.sale_order_id:
            self.partner_id = self.sale_order_id.partner_id
            # Chercher le bon de livraison associé
            picking = self.env['stock.picking'].search([
                ('sale_id', '=', self.sale_order_id.id),
                ('state', '=', 'done'),
                ('picking_type_code', '=', 'outgoing'),
            ], limit=1)
            if picking:
                self.picking_id = picking

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Reset les champs liés quand le client change."""
        if self.partner_id:
            self.sale_order_id = False
            self.picking_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Filtrer les types de panne selon la catégorie."""
        if self.category_id and self.fault_type_id:
            if self.fault_type_id.category_ids and self.category_id not in self.fault_type_id.category_ids:
                self.fault_type_id = False

    @api.onchange('filter_from_picking', 'picking_id')
    def _onchange_filter_from_picking(self):
        """Réinitialiser le produit si le filtre change."""
        if self.filter_from_picking and self.picking_id:
            # Récupérer les produits du BL
            product_ids = self.picking_id.move_ids.mapped('product_id').ids
            # Si le produit actuel n'est pas dans la liste, le réinitialiser
            if self.product_id and self.product_id.id not in product_ids:
                self.product_id = False

    def action_confirm(self):
        """Confirmer la réception."""
        for rec in self:
            rec.write({
                'state': 'received',
                'reception_date': fields.Datetime.now(),
            })

    def action_start_repair(self):
        """Démarrer la réparation."""
        for rec in self:
            rec.write({
                'state': 'in_progress',
                'repair_start_date': fields.Datetime.now(),
                'doc_state': 'repair_order',
            })

    def action_mark_repaired(self):
        """Marquer comme réparé."""
        for rec in self:
            rec.write({
                'state': 'repaired',
                'repair_end_date': fields.Datetime.now(),
                'action_taken': 'repaired',
            })

    def action_mark_not_repaired(self):
        """Marquer comme non réparable."""
        for rec in self:
            rec.write({
                'state': 'not_repaired',
                'repair_end_date': fields.Datetime.now(),
            })

    def action_mark_replaced(self):
        """Marquer comme changé."""
        for rec in self:
            rec.write({
                'state': 'repaired',
                'repair_end_date': fields.Datetime.now(),
                'action_taken': 'replaced',
            })

    def action_deliver(self):
        """Marquer comme livré."""
        for rec in self:
            rec.write({
                'state': 'delivered',
                'delivery_date': fields.Datetime.now(),
                'doc_state': 'delivery_order',
            })

    def action_cancel(self):
        """Annuler le retour."""
        for rec in self:
            rec.write({
                'state': 'cancelled',
            })

    def action_reset_draft(self):
        """Remettre en brouillon."""
        for rec in self:
            rec.write({
                'state': 'draft',
                'reception_date': False,
                'repair_start_date': False,
                'repair_end_date': False,
                'delivery_date': False,
            })

    def action_print_repair_order(self):
        """Imprimer le bon de réparation."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_sav_repair_order').report_action(self)

    def action_print_delivery_order(self):
        """Imprimer le bon de livraison."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_sav_delivery_order').report_action(self)
