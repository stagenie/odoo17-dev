# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SavReturn(models.Model):
    _name = 'sav.return'
    _description = 'Retour SAV Électroménager'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    # ========== Informations Générales ==========
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
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Créé par',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Bas'),
        ('2', 'Moyen'),
        ('3', 'Urgent'),
    ], string='Priorité',
        default='0',
    )

    # ========== Acteurs du Circuit ==========
    sales_point_id = fields.Many2one(
        'res.partner',
        string='Point de Vente',
        required=True,
        tracking=True,
        domain="[('is_sales_point', '=', True)]",
        default=lambda self: self.env.user.sav_sales_point_id,
        help='Point de vente qui déclare le retour',
    )
    return_center_id = fields.Many2one(
        'res.partner',
        string='Centre de Retour',
        tracking=True,
        domain="[('is_return_center', '=', True)]",
        default=lambda self: self._get_default_return_center(),
        help='Centre de retour qui centralise les retours',
    )
    repairer_id = fields.Many2one(
        'res.partner',
        string='Réparateur',
        tracking=True,
        domain="[('is_repairer', '=', True)]",
        default=lambda self: self._get_default_repairer(),
        help='Réparateur qui effectue les réparations',
    )

    # ========== Origine (Optionnel) ==========
    partner_id = fields.Many2one(
        'res.partner',
        string='Client Final',
        domain="[('customer_rank', '>', 0)]",
        help='Client final qui a acheté les produits (optionnel)',
    )
    sale_order_ids = fields.Many2many(
        'sale.order',
        'sav_return_sale_order_rel',
        'return_id',
        'order_id',
        string='Commandes Origine',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['sale', 'done'])]",
        help='Bons de vente d\'origine (optionnel)',
    )
    picking_ids = fields.Many2many(
        'stock.picking',
        'sav_return_stock_picking_rel',
        'return_id',
        'picking_id',
        string='BL Origine',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
        help='Bons de livraison d\'origine (optionnel)',
    )

    # ========== Lignes d'Articles Retournés ==========
    line_ids = fields.One2many(
        'sav.return.line',
        'return_id',
        string='Articles Retournés',
        copy=True,
    )

    # Lignes filtrées pour l'onglet Usine (articles non réparables)
    factory_line_ids = fields.One2many(
        'sav.return.line',
        'return_id',
        string='Articles à Envoyer à l\'Usine',
        compute='_compute_factory_line_ids',
        inverse='_inverse_factory_line_ids',
    )

    # Contrôle visibilité de l'onglet usine
    show_factory_tab = fields.Boolean(
        string='Afficher Onglet Usine',
        compute='_compute_show_factory_tab',
        store=True,
    )

    # ========== Workflow Multi-Niveaux ==========
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis au Centre'),
        ('received_center', 'Reçu au Centre'),
        ('sent_to_repairer', 'Envoyé au Réparateur'),
        ('in_repair', 'En Réparation'),
        ('repaired', 'Réparé'),
        ('returned_to_center', 'Retourné au Centre'),
        # États workflow usine
        ('returned_to_center_not_repaired', 'Retourné (Non Réparé)'),
        ('sent_to_factory', 'Envoyé à l\'Usine'),
        ('in_factory', 'En Traitement Usine'),
        ('factory_processed', 'Traité par Usine'),
        ('returned_from_factory', 'Retourné de l\'Usine'),
        # États finaux
        ('sent_to_sales_point', 'Renvoyé au Point Vente'),
        ('closed', 'Clôturé'),
        ('cancelled', 'Annulé'),
    ], string='Statut',
        required=True,
        default='draft',
        tracking=True,
        group_expand='_expand_states',
    )

    # ========== Dates de Tracking ==========
    date_submission = fields.Datetime(
        string='Date Soumission',
        readonly=True,
        help='Date de soumission du retour au centre',
    )
    date_received_center = fields.Datetime(
        string='Date Réception Centre',
        readonly=True,
        help='Date de réception des articles au centre de retour',
    )
    date_sent_to_repairer = fields.Datetime(
        string='Date Envoi Réparateur',
        readonly=True,
        help='Date d\'envoi des articles au réparateur',
    )
    date_repair_start = fields.Datetime(
        string='Date Début Réparation',
        readonly=True,
        help='Date de début de la réparation',
    )
    date_repair_end = fields.Datetime(
        string='Date Fin Réparation',
        readonly=True,
        help='Date de fin de la réparation',
    )
    date_returned_to_center = fields.Datetime(
        string='Date Retour au Centre',
        readonly=True,
        help='Date de retour des articles réparés au centre',
    )
    date_sent_to_sales_point = fields.Datetime(
        string='Date Envoi Point Vente',
        readonly=True,
        help='Date de renvoi des articles au point de vente',
    )
    date_closed = fields.Datetime(
        string='Date Clôture',
        readonly=True,
        help='Date de clôture du retour',
    )

    # ========== Acteur Usine ==========
    factory_id = fields.Many2one(
        'res.partner',
        string='Usine',
        tracking=True,
        domain="[('is_factory', '=', True)]",
        default=lambda self: self._get_default_factory(),
        help='Usine/Fabricant qui traite les articles non réparables',
    )

    # Flag indiquant si des articles sont envoyés à l'usine
    has_factory_items = fields.Boolean(
        string='Articles Envoyés à l\'Usine',
        compute='_compute_has_factory_items',
        store=True,
        help='Indique si certains articles ont été envoyés à l\'usine',
    )

    # ========== Dates de Tracking Usine ==========
    date_returned_not_repaired = fields.Datetime(
        string='Date Retour (Non Réparé)',
        readonly=True,
        help='Date de retour des articles non réparés au centre',
    )
    date_sent_to_factory = fields.Datetime(
        string='Date Envoi Usine',
        readonly=True,
        help='Date d\'envoi des articles à l\'usine',
    )
    date_factory_start = fields.Datetime(
        string='Date Début Traitement Usine',
        readonly=True,
        help='Date de début du traitement par l\'usine',
    )
    date_factory_end = fields.Datetime(
        string='Date Fin Traitement Usine',
        readonly=True,
        help='Date de fin du traitement par l\'usine',
    )
    date_returned_from_factory = fields.Datetime(
        string='Date Retour de l\'Usine',
        readonly=True,
        help='Date de retour des articles de l\'usine au centre',
    )

    # ========== Champs Calculés ==========
    total_articles = fields.Integer(
        string='Nombre Total d\'Articles',
        compute='_compute_totals',
        store=True,
    )
    total_repaired = fields.Integer(
        string='Articles Réparés',
        compute='_compute_totals',
        store=True,
    )
    total_not_repaired = fields.Integer(
        string='Articles Non Réparés',
        compute='_compute_totals',
        store=True,
    )
    total_pending = fields.Integer(
        string='Articles En Attente',
        compute='_compute_totals',
        store=True,
    )

    # ========== Statistiques Usine ==========
    total_sent_to_factory = fields.Integer(
        string='Total Envoyés à l\'Usine',
        compute='_compute_factory_totals',
        store=True,
    )
    total_factory_repaired = fields.Integer(
        string='Réparés par Usine',
        compute='_compute_factory_totals',
        store=True,
    )
    total_factory_replaced = fields.Integer(
        string='Remplacés par Usine',
        compute='_compute_factory_totals',
        store=True,
    )
    total_factory_credited = fields.Integer(
        string='Avoirs Usine',
        compute='_compute_factory_totals',
        store=True,
    )

    # ========== Observations ==========
    observations = fields.Text(
        string='Observations Générales',
        help='Observations et remarques générales sur le retour',
    )

    # ========== Champ pour Kanban ==========
    color = fields.Integer(
        string='Couleur',
        compute='_compute_color',
    )

    # ========== Méthodes Default ==========
    @api.model
    def _get_default_return_center(self):
        """Récupérer le centre de retour par défaut."""
        return self.env['res.partner'].search([
            ('is_return_center', '=', True),
            ('is_default_return_center', '=', True),
        ], limit=1)

    @api.model
    def _get_default_repairer(self):
        """Récupérer le réparateur par défaut."""
        return self.env['res.partner'].search([
            ('is_repairer', '=', True),
            ('is_default_repairer', '=', True),
        ], limit=1)

    @api.model
    def _get_default_factory(self):
        """Récupérer l'usine par défaut."""
        return self.env['res.partner'].search([
            ('is_factory', '=', True),
            ('is_default_factory', '=', True),
        ], limit=1)

    # ========== Méthodes Compute ==========
    @api.model
    def _expand_states(self, states, domain, order):
        """Afficher tous les états dans la vue Kanban."""
        return [key for key, val in self._fields['state'].selection]

    @api.depends('line_ids', 'line_ids.repair_status')
    def _compute_totals(self):
        """Calculer les totaux depuis les lignes."""
        for rec in self:
            rec.total_articles = len(rec.line_ids)
            rec.total_repaired = len(rec.line_ids.filtered(lambda l: l.repair_status in ['repaired', 'replaced']))
            rec.total_not_repaired = len(rec.line_ids.filtered(lambda l: l.repair_status in ['not_repairable', 'rejected']))
            rec.total_pending = len(rec.line_ids.filtered(lambda l: l.repair_status == 'pending'))

    @api.depends('state')
    def _compute_color(self):
        """Calculer la couleur pour le Kanban."""
        color_map = {
            'draft': 0,
            'submitted': 4,
            'received_center': 4,
            'sent_to_repairer': 3,
            'in_repair': 3,
            'repaired': 10,
            'returned_to_center': 10,
            # États usine
            'returned_to_center_not_repaired': 2,  # Orange
            'sent_to_factory': 5,  # Violet
            'in_factory': 5,  # Violet
            'factory_processed': 6,  # Rose
            'returned_from_factory': 10,  # Vert
            # États finaux
            'sent_to_sales_point': 10,
            'closed': 10,
            'cancelled': 1,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    @api.depends('line_ids', 'line_ids.repair_status', 'line_ids.failure_reason_id')
    def _compute_has_factory_items(self):
        """Vérifier si des lignes ont des motifs d'échec (nécessitent l'usine)."""
        for rec in self:
            rec.has_factory_items = bool(rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable' and l.failure_reason_id
            ))

    @api.depends('line_ids', 'line_ids.factory_decision')
    def _compute_factory_totals(self):
        """Calculer les statistiques liées à l'usine."""
        for rec in self:
            rec.total_sent_to_factory = len(rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable' and l.failure_reason_id
            ))
            factory_lines = rec.line_ids.filtered(lambda l: l.factory_decision)
            rec.total_factory_repaired = len(factory_lines.filtered(
                lambda l: l.factory_decision == 'factory_repaired'
            ))
            rec.total_factory_replaced = len(factory_lines.filtered(
                lambda l: l.factory_decision == 'factory_replaced'
            ))
            rec.total_factory_credited = len(factory_lines.filtered(
                lambda l: l.factory_decision == 'factory_credited'
            ))

    @api.depends('line_ids', 'line_ids.repair_status')
    def _compute_factory_line_ids(self):
        """Filtrer les lignes non réparables pour l'onglet usine."""
        for rec in self:
            rec.factory_line_ids = rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable'
            )

    def _inverse_factory_line_ids(self):
        """Permettre la modification des lignes depuis l'onglet usine."""
        # Les modifications sont répercutées directement sur line_ids
        pass

    @api.depends('state', 'line_ids.repair_status')
    def _compute_show_factory_tab(self):
        """Déterminer si l'onglet usine doit être affiché."""
        factory_states = [
            'returned_to_center_not_repaired',
            'sent_to_factory',
            'in_factory',
            'factory_processed',
            'returned_from_factory',
            'sent_to_sales_point',
            'closed',
        ]
        for rec in self:
            has_not_repairable = bool(rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable'
            ))
            # Afficher si on est dans un état usine OU si on a des articles non réparables en réparation
            rec.show_factory_tab = (
                rec.state in factory_states or
                (rec.state == 'in_repair' and has_not_repairable)
            )

    # ========== Méthodes Onchange ==========
    @api.onchange('sales_point_id')
    def _onchange_sales_point_id(self):
        """Auto-remplir le centre de retour depuis le point de vente."""
        if self.sales_point_id and self.sales_point_id.parent_return_center_id:
            self.return_center_id = self.sales_point_id.parent_return_center_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Réinitialiser les commandes et BL quand le client change."""
        if self.partner_id:
            self.sale_order_ids = False
            self.picking_ids = False

    # ========== Création ==========
    @api.model_create_multi
    def create(self, vals_list):
        """Générer automatiquement la référence à la création."""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sav.return') or _('Nouveau')
        return super().create(vals_list)

    # ========== Actions du Workflow ==========

    def action_submit_to_center(self):
        """Point de Vente: Soumettre le retour au centre (Draft → Submitted)."""
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Vous devez ajouter au moins un article avant de soumettre le retour!"))
            if not rec.return_center_id:
                raise ValidationError(_("Vous devez sélectionner un centre de retour!"))
            rec.write({
                'state': 'submitted',
                'date_submission': fields.Datetime.now(),
            })
            rec.message_post(body=_("Retour soumis au centre de retour %s.") % rec.return_center_id.name)

    def action_confirm_reception_center(self):
        """Gérant Centre: Confirmer la réception des articles (Submitted → Received Center)."""
        for rec in self:
            rec.write({
                'state': 'received_center',
                'date_received_center': fields.Datetime.now(),
            })
            rec.message_post(body=_("Articles reçus au centre de retour."))

    def action_send_to_repairer(self):
        """Gérant Centre: Envoyer les articles au réparateur (Received Center → Sent to Repairer)."""
        for rec in self:
            if not rec.repairer_id:
                raise ValidationError(_("Vous devez sélectionner un réparateur!"))
            rec.write({
                'state': 'sent_to_repairer',
                'date_sent_to_repairer': fields.Datetime.now(),
            })
            rec.message_post(body=_("Articles envoyés au réparateur %s.") % rec.repairer_id.name)
            # Optionnel: ouvrir automatiquement le rapport PDF
            # return rec.action_print_delivery_to_repairer()

    def action_mark_in_repair(self):
        """Gérant Centre: Marquer les articles en réparation (Sent to Repairer → In Repair)."""
        for rec in self:
            rec.write({
                'state': 'in_repair',
                'date_repair_start': fields.Datetime.now(),
            })
            rec.message_post(body=_("Réparation démarrée par %s.") % rec.repairer_id.name)

    def action_mark_repaired(self):
        """Gérant Centre: Marquer la réparation terminée (In Repair → Repaired).

        Utilisé uniquement si TOUS les articles sont réparés ou remplacés.
        S'il y a des articles non réparables, utiliser action_return_to_center_not_repaired.
        """
        for rec in self:
            pending_lines = rec.line_ids.filtered(lambda l: l.repair_status == 'pending')
            if pending_lines:
                raise ValidationError(_(
                    "Veuillez définir le statut de réparation pour tous les articles avant de continuer!\n"
                    "Articles en attente: %s"
                ) % ', '.join(pending_lines.mapped('display_name')))

            # Vérifier s'il y a des articles non réparables
            not_repairable = rec.line_ids.filtered(lambda l: l.repair_status == 'not_repairable')
            if not_repairable:
                raise ValidationError(_(
                    "Il y a %s article(s) non réparable(s). "
                    "Utilisez le bouton 'Retourner au Centre (Non Réparé)' pour les envoyer à l'usine."
                ) % len(not_repairable))

            rec.write({
                'state': 'repaired',
                'date_repair_end': fields.Datetime.now(),
            })
            rec.message_post(body=_("Réparation terminée. %s réparés, %s remplacés.") % (
                len(rec.line_ids.filtered(lambda l: l.repair_status == 'repaired')),
                len(rec.line_ids.filtered(lambda l: l.repair_status == 'replaced'))
            ))

    def action_return_to_center(self):
        """Gérant Centre: Confirmer le retour du réparateur (Repaired → Returned to Center)."""
        for rec in self:
            rec.write({
                'state': 'returned_to_center',
                'date_returned_to_center': fields.Datetime.now(),
            })
            rec.message_post(body=_("Articles retournés au centre de retour."))
            # Optionnel: ouvrir automatiquement le rapport PDF
            # return rec.action_print_return_from_repairer()

    # ========== Actions Workflow Usine ==========

    def action_return_to_center_not_repaired(self):
        """Retourner les articles non réparables au centre (In Repair → Returned to Center Not Repaired).

        Le réparateur n'a pas pu réparer certains articles. Ils seront envoyés à l'usine.
        """
        for rec in self:
            # Vérifier qu'il y a des articles non réparables
            not_repairable_lines = rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable'
            )
            if not not_repairable_lines:
                raise ValidationError(_(
                    "Vous devez marquer au moins un article comme 'Non Réparable' avant d'utiliser cette action!"
                ))

            # Vérifier que tous les articles non réparables ont un motif d'échec
            lines_without_reason = not_repairable_lines.filtered(
                lambda l: not l.failure_reason_id
            )
            if lines_without_reason:
                raise ValidationError(_(
                    "Veuillez sélectionner un motif d'échec pour tous les articles non réparables:\n%s"
                ) % ', '.join(lines_without_reason.mapped('display_name')))

            # Vérifier qu'il n'y a pas d'articles en attente
            pending_lines = rec.line_ids.filtered(lambda l: l.repair_status == 'pending')
            if pending_lines:
                raise ValidationError(_(
                    "Veuillez définir le statut de réparation pour tous les articles:\n%s"
                ) % ', '.join(pending_lines.mapped('display_name')))

            rec.write({
                'state': 'returned_to_center_not_repaired',
                'date_returned_not_repaired': fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Articles retournés au centre - %s article(s) non réparable(s) à envoyer à l'usine."
            ) % len(not_repairable_lines))

    def action_send_to_factory(self):
        """Envoyer les articles non réparables à l'usine (Returned Not Repaired → Sent to Factory)."""
        for rec in self:
            if not rec.factory_id:
                raise ValidationError(_("Vous devez sélectionner une usine!"))

            not_repairable_count = len(rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable' and l.failure_reason_id
            ))

            rec.write({
                'state': 'sent_to_factory',
                'date_sent_to_factory': fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Articles envoyés à l'usine %s. %s article(s) concerné(s)."
            ) % (rec.factory_id.name, not_repairable_count))

    def action_mark_in_factory(self):
        """Marquer les articles en traitement par l'usine (Sent to Factory → In Factory)."""
        for rec in self:
            rec.write({
                'state': 'in_factory',
                'date_factory_start': fields.Datetime.now(),
            })
            rec.message_post(body=_("Traitement démarré par l'usine %s.") % rec.factory_id.name)

    def action_mark_factory_processed(self):
        """Marquer le traitement usine terminé (In Factory → Factory Processed)."""
        for rec in self:
            # Vérifier que tous les articles envoyés à l'usine ont une décision
            factory_lines = rec.line_ids.filtered(
                lambda l: l.repair_status == 'not_repairable' and l.failure_reason_id
            )
            pending_lines = factory_lines.filtered(lambda l: not l.factory_decision)

            if pending_lines:
                raise ValidationError(_(
                    "Veuillez définir la décision usine pour tous les articles:\n%s"
                ) % ', '.join(pending_lines.mapped('display_name')))

            rec.write({
                'state': 'factory_processed',
                'date_factory_end': fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Traitement usine terminé. %s réparé(s), %s remplacé(s), %s avoir(s)."
            ) % (rec.total_factory_repaired, rec.total_factory_replaced, rec.total_factory_credited))

    def action_confirm_return_from_factory(self):
        """Confirmer le retour des articles de l'usine (Factory Processed → Returned from Factory)."""
        for rec in self:
            rec.write({
                'state': 'returned_from_factory',
                'date_returned_from_factory': fields.Datetime.now(),
            })
            rec.message_post(body=_("Articles retournés de l'usine au centre."))

    def action_send_to_sales_point(self):
        """Gérant Centre: Renvoyer les articles au point de vente.

        Peut être appelé depuis:
        - returned_to_center (flux normal)
        - returned_from_factory (flux usine)
        """
        for rec in self:
            rec.write({
                'state': 'sent_to_sales_point',
                'date_sent_to_sales_point': fields.Datetime.now(),
            })
            rec.message_post(body=_("Articles renvoyés au point de vente %s.") % rec.sales_point_id.name)

    def action_close(self):
        """Point de Vente: Clôturer le retour après réception (Sent to Sales Point → Closed)."""
        for rec in self:
            rec.write({
                'state': 'closed',
                'date_closed': fields.Datetime.now(),
            })
            rec.message_post(body=_("Retour clôturé."))

    def action_cancel(self):
        """Annuler le retour (Any → Cancelled)."""
        for rec in self:
            rec.write({'state': 'cancelled'})
            rec.message_post(body=_("Retour annulé."))

    def action_reset_draft(self):
        """Remettre en brouillon (Cancelled → Draft)."""
        for rec in self:
            rec.write({
                'state': 'draft',
                # Dates originales
                'date_submission': False,
                'date_received_center': False,
                'date_sent_to_repairer': False,
                'date_repair_start': False,
                'date_repair_end': False,
                'date_returned_to_center': False,
                'date_sent_to_sales_point': False,
                'date_closed': False,
                # Dates usine
                'date_returned_not_repaired': False,
                'date_sent_to_factory': False,
                'date_factory_start': False,
                'date_factory_end': False,
                'date_returned_from_factory': False,
            })
            # Réinitialiser les décisions usine sur les lignes
            rec.line_ids.write({
                'factory_decision': False,
                'factory_notes': False,
                'date_factory_decision': False,
                'replacement_serial_number': False,
                'replacement_product_id': False,
            })
            rec.message_post(body=_("Retour remis en brouillon."))

    # ========== Actions Rapports PDF ==========
    def action_print_delivery_to_repairer(self):
        """Imprimer le Bon de Livraison Centre → Réparateur."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_delivery_to_repairer').report_action(self)

    def action_print_return_from_repairer(self):
        """Imprimer le Bon de Retour Réparateur → Centre."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_return_from_repairer').report_action(self)

    def action_print_delivery_to_sales_point(self):
        """Imprimer le Bon de Livraison Centre → Point de Vente."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_delivery_to_sales_point').report_action(self)

    def action_print_delivery_to_factory(self):
        """Imprimer le Bon de Livraison Centre → Usine."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_delivery_to_factory').report_action(self)

    def action_print_return_from_factory(self):
        """Imprimer le Bon de Retour Usine → Centre."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_return_from_factory').report_action(self)

    def action_print_delivery_from_sales_point(self):
        """Imprimer le Bon de Livraison Point de Vente → Centre."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_delivery_from_sales_point').report_action(self)

    def action_print_reception_sales_point(self):
        """Imprimer le Bon de Réception Point de Vente."""
        self.ensure_one()
        return self.env.ref('adi_sav_electromenager.action_report_reception_sales_point').report_action(self)
