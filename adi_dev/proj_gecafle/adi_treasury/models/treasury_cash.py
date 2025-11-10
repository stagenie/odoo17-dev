# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from num2words import num2words


class TreasuryCash(models.Model):
    _name = 'treasury.cash'
    _description = 'Caisse de Trésorerie'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    def action_view_pending_closings(self):
        """Afficher les clôtures en cours de cette caisse"""
        self.ensure_one()

        return {
            'name': _('Clôtures en cours - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.closing',
            'view_mode': 'kanban,tree,form',
            'domain': [
                ('cash_id', '=', self.id),
                ('state', 'in', ['draft', 'confirmed'])
            ],
            'context': {
                'default_cash_id': self.id,
                'search_default_group_state': 1,
                'create': True,
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucune clôture en cours
                </p>
                <p>
                    Les clôtures en cours sont celles qui ne sont pas encore validées.
                    <br/>Créez une nouvelle clôture pour commencer.
                </p>
            """
        }

    def action_create_operation(self):
        """Créer une nouvelle opération sur cette caisse avec gestion automatique de clôture"""
        self.ensure_one()

        # Vérifier ou créer une clôture pour aujourd'hui
        today = fields.Date.today()
        pending_closing = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', self.id),
            ('state', 'in', ['draft', 'confirmed']),
            ('closing_date', '=', today)
        ], limit=1)

        if not pending_closing:
            # Créer automatiquement une clôture
            closing_vals = {
                'cash_id': self.id,
                'closing_date': today,
            }
            pending_closing = self.env['treasury.cash.closing'].create(closing_vals)
            self.message_post(
                body=_("✓ Clôture automatique créée : %s") % pending_closing.name
            )

        return {
            'name': _('Nouvelle opération'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'form',
            'context': {
                'default_cash_id': self.id,
                'default_closing_id': pending_closing.id,
                'default_date': fields.Datetime.now(),
                'default_is_manual': True,
            },
            'target': 'current',
        }

    # Champs de base
    name = fields.Char(
        string='Nom de la caisse',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        help="Code unique pour identifier la caisse"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    # Responsables et configuration
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable principal',
        default=lambda self: self.env.user,
        tracking=True
    )
    user_ids = fields.Many2many(
        'res.users',
        'treasury_cash_users_rel',
        'cash_id',
        'user_id',
        string='Utilisateurs autorisés',
        help="Utilisateurs pouvant effectuer des opérations sur cette caisse"
    )

    # Soldes
    current_balance = fields.Monetary(
        string='Solde actuel',
        currency_field='currency_id',
        compute='_compute_current_balance',
        store=True,
        help="Solde calculé automatiquement"
    )
    last_closing_balance = fields.Monetary(
        string='Solde dernière clôture',
        currency_field='currency_id',
        readonly=True,
        help="Solde lors de la dernière clôture"
    )

    # États et dates
    state = fields.Selection([
        ('open', 'Ouverte'),
        ('closed', 'Fermée temporairement'),
        ('locked', 'Verrouillée')
    ], string='État', default='open', tracking=True)

    last_closing_date = fields.Datetime(
        string='Dernière clôture',
        readonly=True
    )
    opening_date = fields.Date(
        string='Date d\'ouverture',
        default=fields.Date.today,
        required=True
    )

    # Configuration
    auto_close_days = fields.Integer(
        string='Clôture automatique (jours)',
        default=1,
        help="Nombre de jours avant clôture automatique (0 = pas de clôture auto)"
    )
    require_closing = fields.Boolean(
        string='Clôture obligatoire',
        default=True,
        help="Obliger la clôture périodique de cette caisse"
    )
    max_amount = fields.Monetary(
        string='Montant maximum autorisé',
        currency_field='currency_id',
        help="Montant maximum pouvant être conservé dans la caisse"
    )

    # Journal comptable
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal de caisse',
        required=True,
        domain="[('type', '=', 'cash')]",
        help="Journal comptable de type caisse associé pour la synchronisation des paiements"
    )

    # Autres
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    location = fields.Char(
        string='Emplacement',
        help="Emplacement physique de la caisse"
    )

    notes = fields.Text(
        string='Notes internes'
    )

    color = fields.Integer(
        string='Couleur',
        help="Couleur pour la vue Kanban"
    )

    # Champs calculés pour les statistiques
    operation_count = fields.Integer(
        string='Nombre d\'opérations',
        compute='_compute_operation_count'
    )
    transfer_count = fields.Integer(
        string='Nombre de transferts',
        compute='_compute_transfer_count'
    )
    days_since_closing = fields.Integer(
        string='Jours depuis clôture',
        store=True,
        compute='_compute_days_since_closing'
    )

    # Champs relationnels pour les transferts
    transfer_out_ids = fields.One2many(
        'treasury.transfer',
        'cash_from_id',
        string='Transferts sortants'
    )
    transfer_in_ids = fields.One2many(
        'treasury.transfer',
        'cash_to_id',
        string='Transferts entrants'
    )

    # Relations avec les opérations et clôtures
    operation_ids = fields.One2many(
        'treasury.cash.operation',
        'cash_id',
        string='Opérations'
    )

    closing_ids = fields.One2many(
        'treasury.cash.closing',
        'cash_id',
        string='Clôtures'
    )

    last_closing_id = fields.Many2one(
        'treasury.cash.closing',
        string='Dernière clôture',
        compute='_compute_last_closing',
        store=True
    )

    closing_count = fields.Integer(
        string='Nombre de clôtures',
        compute='_compute_closing_count'
    )

    def _compute_operation_count(self):
        """Compteur d'opérations"""
        for cash in self:
            cash.operation_count = len(cash.operation_ids)

    def _compute_transfer_count(self):
        """Compteur de transferts"""
        for cash in self:
            cash.transfer_count = len(cash.transfer_out_ids | cash.transfer_in_ids)

    @api.depends('last_closing_date', 'opening_date')
    def _compute_days_since_closing(self):
        """Calcul du nombre de jours depuis la dernière clôture"""
        today = fields.Date.today()
        for cash in self:
            if cash.last_closing_date:
                delta = datetime.now() - cash.last_closing_date
                cash.days_since_closing = delta.days
            else:
                # Si jamais clôturée, compter depuis la date d'ouverture
                if cash.opening_date:
                    delta = today - cash.opening_date
                    cash.days_since_closing = delta.days
                else:
                    cash.days_since_closing = 0

    # 🔧 **CORRECTION MAJEURE : Calcul du solde actuel avec tri correct**
    @api.depends('operation_ids.state', 'operation_ids.operation_type', 'operation_ids.amount',
                 'closing_ids.state', 'closing_ids.balance_end_real', 'closing_ids.closing_date')
    def _compute_current_balance(self):
        """🔧 CALCUL DU SOLDE ACTUEL - VERSION CORRIGÉE"""
        for cash in self:
            balance = 0.0

            # 1. Partir du solde de la dernière clôture validée
            # 🔧 CORRECTION : Utiliser sorted() avec lambda au lieu de chaîne
            last_closing = cash.closing_ids.filtered(
                lambda c: c.state == 'validated'
            ).sorted(lambda c: (c.closing_date, c.closing_number), reverse=True)[:1]

            if last_closing:
                # ✅ Partir du solde réel de la dernière clôture validée
                balance = last_closing.balance_end_real

                # ✅ CORRECTION : Utiliser la date de clôture + 1 seconde comme référence
                # au lieu de period_end qui peut être imprécis
                reference_datetime = datetime.combine(
                    last_closing.closing_date,
                    datetime.max.time()
                ) + timedelta(seconds=1)

                # 2. Ajouter UNIQUEMENT les opérations APRÈS la dernière clôture validée
                operations_after = cash.operation_ids.filtered(
                    lambda o: (
                            o.state == 'posted' and
                            o.date > reference_datetime and
                            (not o.closing_id or o.closing_id.state != 'validated')
                    )
                )

                # 3. Calculer le solde avec ces opérations
                for op in operations_after:
                    if op.operation_type == 'in':
                        balance += op.amount
                    else:
                        balance -= op.amount

            else:
                # Aucune clôture validée : calculer depuis toutes les opérations postées
                all_posted_operations = cash.operation_ids.filtered(
                    lambda o: o.state == 'posted'
                )

                for op in all_posted_operations:
                    if op.operation_type == 'in':
                        balance += op.amount
                    else:
                        balance -= op.amount

            cash.current_balance = balance

    # 🔧 **CORRECTION : Tri correct dans _compute_last_closing**
    @api.depends('closing_ids.state', 'closing_ids.closing_date')
    def _compute_last_closing(self):
        """Déterminer la dernière clôture"""
        for cash in self:
            # 🔧 CORRECTION : Utiliser sorted() avec lambda
            last_closing = cash.closing_ids.filtered(
                lambda c: c.state == 'validated'
            ).sorted(lambda c: (c.closing_date, c.closing_number), reverse=True)[:1]

            cash.last_closing_id = last_closing

    def _compute_closing_count(self):
        """Compteur de clôtures"""
        for cash in self:
            cash.closing_count = self.env['treasury.cash.closing'].search_count([
                ('cash_id', '=', cash.id)
            ])

    @api.constrains('journal_id')
    def _check_journal_unique(self):
        """Vérifier qu'un journal n'est pas déjà utilisé par une autre caisse"""
        for cash in self:
            if cash.journal_id:
                other_cash = self.search([
                    ('journal_id', '=', cash.journal_id.id),
                    ('id', '!=', cash.id),
                    ('company_id', '=', cash.company_id.id)
                ])
                if other_cash:
                    raise ValidationError(
                        _("Le journal '%s' est déjà utilisé par la caisse '%s' !") %
                        (cash.journal_id.name, other_cash.name)
                    )

    @api.model
    def create(self, vals):
        """Override create pour créer automatiquement un journal si non fourni"""
        if not vals.get('journal_id') and vals.get('name') and vals.get('code'):
            # Créer automatiquement un journal de caisse
            journal_vals = {
                'name': _('Caisse %s') % vals.get('name'),
                'code': 'CSH%s' % vals.get('code', '')[:3],
                'type': 'cash',
                'company_id': vals.get('company_id', self.env.company.id),
            }
            journal = self.env['account.journal'].create(journal_vals)
            vals['journal_id'] = journal.id

        cash = super().create(vals)

        # Message de création
        cash.message_post(body=_("Caisse créée avec le journal comptable '%s'") % cash.journal_id.name)

        return cash

    @api.constrains('code')
    def _check_code_unique(self):
        """Vérifier l'unicité du code de caisse par société"""
        for cash in self:
            domain = [
                ('code', '=', cash.code),
                ('company_id', '=', cash.company_id.id),
                ('id', '!=', cash.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    _("Le code '%s' est déjà utilisé pour une autre caisse dans cette société !") % cash.code
                )

    @api.constrains('max_amount')
    def _check_max_amount(self):
        """Vérifier que le montant maximum est positif"""
        for cash in self:
            if cash.max_amount < 0:
                raise ValidationError(
                    _("Le montant maximum autorisé ne peut pas être négatif !")
                )

    def action_open(self):
        """Ouvrir la caisse"""
        self.ensure_one()
        if self.state != 'open':
            self.state = 'open'
            self.message_post(body=_("Caisse ouverte"))

    def action_close_temporary(self):
        """Fermer temporairement la caisse"""
        self.ensure_one()
        if self.state == 'open':
            self.state = 'closed'
            self.message_post(body=_("Caisse fermée temporairement"))

    def action_lock(self):
        """Verrouiller la caisse"""
        self.ensure_one()
        self.state = 'locked'
        self.message_post(body=_("Caisse verrouillée"))

    @api.onchange('require_closing', 'auto_close_days')
    def _onchange_closing_config(self):
        """Avertissement si pas de clôture automatique"""
        if self.require_closing and self.auto_close_days == 0:
            return {
                'warning': {
                    'title': _("Configuration de clôture"),
                    'message': _("La clôture est obligatoire mais aucune période automatique n'est définie. "
                                 "Pensez à clôturer manuellement la caisse régulièrement.")
                }
            }

    def name_get(self):
        """Affichage du nom avec le code"""
        result = []
        for cash in self:
            name = f"[{cash.code}] {cash.name}"
            result.append((cash.id, name))
        return result

    def action_view_transfers(self):
        """Afficher tous les transferts liés à cette caisse"""
        self.ensure_one()

        all_transfers = self.transfer_out_ids | self.transfer_in_ids

        return {
            'name': _('Transferts de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.transfer',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_transfers.ids)],
            'context': {
                'default_cash_from_id': self.id,
            }
        }

    def action_view_journal(self):
        """Ouvrir le journal associé"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal de caisse'),
            'res_model': 'account.journal',
            'res_id': self.journal_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _check_closing_required(self):
        """Vérifier si la caisse peut accepter des opérations"""
        self.ensure_one()

        # Vérifier s'il y a une clôture en cours
        pending_closing = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', self.id),
            ('state', 'in', ['draft', 'confirmed'])
        ], limit=1)

        if not pending_closing:
            raise UserError(_(
                "Aucune clôture en cours pour la caisse '%s'.\n"
                "Veuillez créer une clôture avant d'enregistrer des opérations."
            ) % self.name)

        return pending_closing

    def action_create_closing(self):
        """Créer une nouvelle clôture"""
        self.ensure_one()

        # Vérifier s'il y a une clôture en cours
        pending_closings = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', self.id),
            ('state', '!=', 'validated')
        ])

        if pending_closings:
            # Proposer d'ouvrir la clôture existante
            return {
                'type': 'ir.actions.act_window',
                'name': _('Clôture en cours'),
                'res_model': 'treasury.cash.closing',
                'res_id': pending_closings[0].id,
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'form_view_initial_mode': 'edit',
                }
            }

        return {
            'name': _('Nouvelle clôture'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.closing',
            'view_mode': 'form',
            'context': {
                'default_cash_id': self.id,
                'default_closing_date': fields.Date.today(),
            },
            'target': 'current',
        }

    def action_view_closings(self):
        """Afficher toutes les clôtures de cette caisse"""
        self.ensure_one()

        return {
            'name': _('Clôtures de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.closing',
            'view_mode': 'tree,form',
            'domain': [('cash_id', '=', self.id)],
            'context': {
                'default_cash_id': self.id,
                'search_default_group_state': 1,
            }
        }

    def action_initialize_balance(self):
        """Initialiser le solde de la caisse"""
        self.ensure_one()

        # Créer une clôture pour aujourd'hui si elle n'existe pas
        today = fields.Date.today()
        pending_closing = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', self.id),
            ('state', 'in', ['draft', 'confirmed']),
            ('closing_date', '=', today)
        ], limit=1)

        if not pending_closing:
            closing_vals = {
                'cash_id': self.id,
                'closing_date': today,
            }
            pending_closing = self.env['treasury.cash.closing'].create(closing_vals)

        # Créer l'action pour ouvrir un wizard d'initialisation
        return {
            'name': _('Initialiser le solde de la caisse'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'form',
            'context': {
                'default_cash_id': self.id,
                'default_closing_id': pending_closing.id,
                'default_operation_type': 'in',
                'default_category_id': self.env.ref('adi_treasury.category_ajustement').id,
                'default_description': _('Solde initial de la caisse %s') % self.name,
                'default_is_manual': True,
                'default_date': fields.Datetime.now(),
            },
            'target': 'new',
        }
