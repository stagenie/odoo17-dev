# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class TreasurySafeOperation(models.Model):
    _name = 'treasury.safe.operation'
    _description = 'Opération de coffre'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    safe_id = fields.Many2one(
        'treasury.safe',
        string='Coffre',
        required=True,
        domain="[('state', '=', 'active')]",
        tracking=True
    )

    operation_type = fields.Selection([
        ('initial', 'Solde initial'),  # Nouveau type
        ('bank_in', 'Entrée depuis Banque'),
        ('bank_out', 'Sortie vers Banque'),
        ('adjustment', 'Ajustement'),
        ('other_in', 'Autre entrée'),
        ('other_out', 'Autre sortie'),
    ], string='Type d\'opération', required=True, tracking=True)

    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='safe_id.currency_id',
        store=True
    )

    date = fields.Datetime(
        string='Date de l\'opération',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    bank_reference = fields.Char(
        string='Référence bancaire',
        help="Numéro de chèque, virement, etc."
    )

    description = fields.Text(
        string='Description',
        required=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Effectué'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True)

    # Soldes avant/après
    balance_before = fields.Monetary(
        string='Solde avant',
        compute='_compute_balances',
        currency_field='currency_id'
    )
    balance_after = fields.Monetary(
        string='Solde après',
        compute='_compute_balances',
        currency_field='currency_id'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Créé par',
        default=lambda self: self.env.user,
        readonly=True
    )

    validated_by = fields.Many2one(
        'res.users',
        string='Validé par',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        related='safe_id.company_id',
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Générer la référence et gérer l'initialisation"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                # Générer une référence spéciale pour l'initialisation
                if vals.get('operation_type') == 'initial':
                    vals['name'] = f"INIT/{vals.get('safe_id', '')}/{fields.Date.today()}"
                else:
                    sequence = self.env['ir.sequence'].search([
                        ('code', '=', 'treasury.safe.operation'),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    if not sequence:
                        sequence = self.env['ir.sequence'].create({
                            'name': 'Opération coffre',
                            'code': 'treasury.safe.operation',
                            'prefix': 'OP/%(year)s/',
                            'padding': 5,
                            'company_id': self.env.company.id,
                        })
                    vals['name'] = sequence.next_by_id()

        operations = super().create(vals_list)

        # Marquer le coffre comme initialisé si c'est une opération initiale
        for operation in operations:
            if operation.operation_type == 'initial' and operation.state == 'draft':
                operation.safe_id.is_initialized = True

        return operations

    @api.depends('safe_id', 'amount', 'operation_type', 'state')
    def _compute_balances(self):
        """Calculer les soldes avant/après"""
        for operation in self:
            if operation.safe_id:
                operation.balance_before = operation.safe_id.current_balance
                if operation.state == 'done':
                    if operation.operation_type in ['bank_in', 'other_in', 'adjustment']:
                        operation.balance_after = operation.balance_before + operation.amount
                    else:  # bank_out, other_out
                        operation.balance_after = operation.balance_before - operation.amount
                else:
                    operation.balance_after = operation.balance_before
            else:
                operation.balance_before = 0
                operation.balance_after = 0

    # Ajouter une contrainte pour l'initialisation unique
    @api.constrains('operation_type', 'safe_id')
    def _check_single_initialization(self):
        """Vérifier qu'un coffre n'a qu'une seule initialisation"""
        for operation in self:
            if operation.operation_type == 'initial':
                existing = self.search([
                    ('safe_id', '=', operation.safe_id.id),
                    ('operation_type', '=', 'initial'),
                    ('state', '!=', 'cancel'),
                    ('id', '!=', operation.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Le coffre '%s' a déjà été initialisé !") % operation.safe_id.name
                    )  # Ajouter une contrainte pour l'initialisation unique


    @api.constrains('operation_type', 'safe_id')
    def _check_single_initialization(self):
        """Vérifier qu'un coffre n'a qu'une seule initialisation"""
        for operation in self:
            if operation.operation_type == 'initial':
                existing = self.search([
                    ('safe_id', '=', operation.safe_id.id),
                    ('operation_type', '=', 'initial'),
                    ('state', '!=', 'cancel'),
                    ('id', '!=', operation.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Le coffre '%s' a déjà été initialisé !") % operation.safe_id.name
                    )

    """
    @api.constrains('amount')
    def _check_amount(self):
        Vérifier que le montant est positif
        for operation in self:
            if operation.amount <= 0:
                raise ValidationError(_("Le montant doit être positif !"))
    """


    def action_confirm(self):
        """Confirmer l'opération"""
        for operation in self:
            if operation.state != 'draft':
                raise UserError(_("Seules les opérations en brouillon peuvent être confirmées."))

            # Vérifier le solde pour les sorties
            if operation.operation_type in ['bank_out', 'other_out']:
                if operation.safe_id.current_balance < operation.amount:
                    raise UserError(
                        _("Solde insuffisant dans le coffre '%s'.\n"
                          "Solde disponible : %s %s") % (
                            operation.safe_id.name,
                            operation.safe_id.current_balance,
                            operation.currency_id.symbol
                        )
                    )

            operation.state = 'confirmed'
            operation.message_post(body=_("Opération confirmée par %s") % self.env.user.name)

    def action_done(self):
        """Effectuer l'opération"""
        for operation in self:
            if operation.state != 'confirmed':
                raise UserError(_("Seules les opérations confirmées peuvent être effectuées."))

            operation.write({
                'state': 'done',
                'validated_by': self.env.user.id
            })

            # Message détaillé
            if operation.operation_type == 'bank_in':
                msg = _("Entrée depuis banque : %s %s (Réf: %s)") % (
                    operation.amount, operation.currency_id.symbol,
                    operation.bank_reference or 'N/A'
                )
            elif operation.operation_type == 'bank_out':
                msg = _("Sortie vers banque : %s %s (Réf: %s)") % (
                    operation.amount, operation.currency_id.symbol,
                    operation.bank_reference or 'N/A'
                )
            else:
                msg = _("Opération %s : %s %s") % (
                    dict(operation._fields['operation_type'].selection).get(operation.operation_type),
                    operation.amount, operation.currency_id.symbol
                )

            operation.safe_id.message_post(body=msg)
            operation.message_post(body=_("Opération effectuée. Solde du coffre : %s → %s") % (
                operation.balance_before, operation.balance_after
            ))

    def action_cancel(self):
        """Annuler l'opération"""
        for operation in self:
            if operation.state == 'done':
                raise UserError(_("Une opération effectuée ne peut pas être annulée."))
            operation.state = 'cancel'
