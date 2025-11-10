# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TreasurySafe(models.Model):
    _name = 'treasury.safe'
    _description = 'Coffre-fort'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # Champs de base
    name = fields.Char(
        string='Nom du coffre',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        help="Code unique pour identifier le coffre"
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
    responsible_ids = fields.Many2many(
        'res.users',
        'treasury_safe_users_rel',
        'safe_id',
        'user_id',
        string='Responsables',
        help="Utilisateurs autorisés à accéder au coffre",
        required=True
    )

    # Soldes
    current_balance = fields.Monetary(
        string='Solde actuel',
        currency_field='currency_id',
        compute='_compute_current_balance',
        store=True,
        help="Solde total dans le coffre"
    )

    # États
    state = fields.Selection([
        ('active', 'Actif'),
        ('locked', 'Verrouillé')
    ], string='État', default='active', tracking=True)

    # Configuration
    location = fields.Char(
        string='Emplacement',
        help="Emplacement physique du coffre"
    )
    max_capacity = fields.Monetary(
        string='Capacité maximum',
        currency_field='currency_id',
        help="Montant maximum pouvant être stocké"
    )

    # Initialisation
    is_initialized = fields.Boolean(
        string='Initialisé',
        default=False,
        readonly=True,
        help="Indique si le coffre a déjà été initialisé"
    )

    # Autres
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    notes = fields.Text(
        string='Notes internes'
    )

    # Relations avec les transferts
    transfer_in_ids = fields.One2many(
        'treasury.transfer',
        'safe_to_id',
        string='Transferts entrants'
    )
    transfer_out_ids = fields.One2many(
        'treasury.transfer',
        'safe_from_id',
        string='Transferts sortants'
    )

    # Relations avec les opérations
    operation_ids = fields.One2many(
        'treasury.safe.operation',
        'safe_id',
        string='Opérations'
    )

    # Champs calculés
    transfer_count = fields.Integer(
        string='Nombre de transferts',
        compute='_compute_transfer_count'
    )
    last_operation_date = fields.Datetime(
        string='Dernière opération',
        compute='_compute_last_operation',
        store=True
    )

    @api.depends('operation_ids', 'operation_ids.state', 'operation_ids.amount', 'operation_ids.operation_type',
                 'transfer_in_ids.state', 'transfer_out_ids.state',
                 'transfer_in_ids.amount', 'transfer_out_ids.amount')
    def _compute_current_balance(self):
        """Calcul du solde actuel du coffre"""
        for safe in self:
            balance = 0.0

            # Ajouter/soustraire les opérations de coffre effectuées
            done_operations = safe.operation_ids.filtered(lambda o: o.state == 'done')
            for op in done_operations:
                if op.operation_type in ['initial', 'bank_in', 'other_in', 'adjustment']:
                    balance += op.amount
                else:  # bank_out, other_out
                    balance -= op.amount

            # Ajouter les transferts entrants effectués
            in_transfers = safe.transfer_in_ids.filtered(lambda t: t.state == 'done')
            balance += sum(in_transfers.mapped('amount'))

            # Soustraire les transferts sortants effectués
            out_transfers = safe.transfer_out_ids.filtered(lambda t: t.state == 'done')
            balance -= sum(out_transfers.mapped('amount'))

            safe.current_balance = balance

    def _compute_transfer_count(self):
        """Compteur de transferts"""
        for safe in self:
            safe.transfer_count = len(safe.transfer_in_ids | safe.transfer_out_ids)

    @api.depends('transfer_in_ids.date', 'transfer_out_ids.date', 'operation_ids.date')
    def _compute_last_operation(self):
        """Date de la dernière opération"""
        for safe in self:
            all_dates = []

            # Dates des transferts
            all_transfers = safe.transfer_in_ids | safe.transfer_out_ids
            done_transfers = all_transfers.filtered(lambda t: t.state == 'done')
            if done_transfers:
                all_dates.extend(done_transfers.mapped('date'))

            # Dates des opérations
            done_operations = safe.operation_ids.filtered(lambda o: o.state == 'done')
            if done_operations:
                all_dates.extend(done_operations.mapped('date'))

            if all_dates:
                safe.last_operation_date = max(all_dates)
            else:
                safe.last_operation_date = False

    @api.constrains('code')
    def _check_code_unique(self):
        """Vérifier l'unicité du code de coffre par société"""
        for safe in self:
            domain = [
                ('code', '=', safe.code),
                ('company_id', '=', safe.company_id.id),
                ('id', '!=', safe.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    _("Le code '%s' est déjà utilisé pour un autre coffre dans cette société !") % safe.code
                )

    @api.constrains('max_capacity', 'current_balance')
    def _check_capacity(self):
        """Vérifier que la capacité n'est pas dépassée"""
        for safe in self:
            if safe.max_capacity > 0 and safe.current_balance > safe.max_capacity:
                raise ValidationError(
                    _("La capacité maximum du coffre '%s' est dépassée !\n"
                      "Capacité : %s\n"
                      "Solde actuel : %s") % (
                        safe.name, safe.max_capacity, safe.current_balance
                    )
                )

    def action_lock(self):
        """Verrouiller le coffre"""
        self.ensure_one()
        self.state = 'locked'
        self.message_post(body=_("Coffre verrouillé"))

    def action_unlock(self):
        """Déverrouiller le coffre"""
        self.ensure_one()
        self.state = 'active'
        self.message_post(body=_("Coffre déverrouillé"))

    def action_view_transfers(self):
        """Afficher tous les transferts liés à ce coffre"""
        self.ensure_one()

        all_transfers = self.transfer_in_ids | self.transfer_out_ids

        return {
            'name': _('Transferts du coffre %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.transfer',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_transfers.ids)],
            'context': {
                'default_safe_from_id': self.id,
            }
        }

    def action_create_operation(self):
        """Créer une nouvelle opération sur ce coffre"""
        self.ensure_one()

        # Si pas encore initialisé, proposer l'initialisation
        if not self.is_initialized:
            context = {
                'default_safe_id': self.id,
                'default_operation_type': 'initial',
                'default_description': 'Solde initial du coffre',
            }
        else:
            context = {
                'default_safe_id': self.id,
            }

        return {
            'name': _('Nouvelle opération'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.safe.operation',
            'view_mode': 'form',
            'context': context,
            'target': 'current',
        }

    def name_get(self):
        """Affichage du nom avec le code"""
        result = []
        for safe in self:
            name = f"[{safe.code}] {safe.name}"
            result.append((safe.id, name))
        return result
