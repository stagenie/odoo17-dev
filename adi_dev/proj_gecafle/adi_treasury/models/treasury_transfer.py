# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from num2words import num2words


class TreasuryTransfer(models.Model):
    _name = 'treasury.transfer'
    _description = 'Transfert entre caisses'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    def amount_to_text(self):
        """Convertir le montant en lettres"""
        self.ensure_one()

        # Convertir en lettres
        try:
            # Pour le français
            amount_text = num2words(self.amount, lang='fr', to='currency')
            # Ajouter la devise
            currency_name = self.currency_id.currency_unit_label or self.currency_id.name
            return f"{amount_text} {currency_name}".upper()
        except:
            # Fallback si num2words n'est pas installé
            whole = int(self.amount)
            decimal = int((self.amount - whole) * 100)
            text = f"{whole:,}".replace(',', ' ')
            if decimal:
                text += f",{decimal:02d}"
            return f"{text} {self.currency_id.symbol}"

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    # Type de transfert
    transfer_type = fields.Selection([
        ('cash_to_cash', 'Caisse vers Caisse'),
        ('cash_to_safe', 'Caisse vers Coffre'),
        ('safe_to_cash', 'Coffre vers Caisse'),
        ('safe_to_safe', 'Coffre vers Coffre'),
    ], string='Type de transfert', required=True, default='cash_to_cash', tracking=True)

    # Caisses source et destination
    cash_from_id = fields.Many2one(
        'treasury.cash',
        string='Caisse source',
        domain="[('state', '=', 'open')]",
        tracking=True
    )
    cash_to_id = fields.Many2one(
        'treasury.cash',
        string='Caisse destination',
        domain="[('state', '=', 'open')]",
        tracking=True
    )

    # Coffres source et destination
    safe_from_id = fields.Many2one(
        'treasury.safe',
        string='Coffre source',
        domain="[('state', '=', 'active')]",
        tracking=True
    )
    safe_to_id = fields.Many2one(
        'treasury.safe',
        string='Coffre destination',
        domain="[('state', '=', 'active')]",
        tracking=True
    )

    # Champs pour les opérations de caisse liées
    cash_operation_out_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération de sortie',
        readonly=True,
        ondelete='restrict'
    )

    cash_operation_in_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération d\'entrée',
        readonly=True,
        ondelete='restrict'
    )

    # Montants et devise
    amount = fields.Monetary(
        string='Montant à transférer',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        compute='_compute_currency_id',
        store=True,
        readonly=True
    )

    @api.depends('cash_from_id', 'cash_to_id', 'safe_from_id', 'safe_to_id', 'transfer_type')
    def _compute_currency_id(self):
        """Calculer la devise selon la source"""
        for transfer in self:
            if transfer.transfer_type in ['cash_to_cash', 'cash_to_safe'] and transfer.cash_from_id:
                transfer.currency_id = transfer.cash_from_id.currency_id
            elif transfer.transfer_type in ['safe_to_cash', 'safe_to_safe'] and transfer.safe_from_id:
                transfer.currency_id = transfer.safe_from_id.currency_id
            else:
                transfer.currency_id = self.env.company.currency_id

    # Dates et informations
    date = fields.Datetime(
        string='Date du transfert',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    description = fields.Text(
        string='Description'
    )

    # État du transfert
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('done', 'Effectué'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True, required=True)

    # Utilisateurs et société
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
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        readonly=True
    )

    # Champs calculés pour affichage
    balance_before_from = fields.Monetary(
        string='Solde avant (Source)',
        compute='_compute_balances',
        currency_field='currency_id'
    )
    balance_after_from = fields.Monetary(
        string='Solde après (Source)',
        compute='_compute_balances',
        currency_field='currency_id'
    )
    balance_before_to = fields.Monetary(
        string='Solde avant (Destination)',
        compute='_compute_balances',
        currency_field='currency_id'
    )
    balance_after_to = fields.Monetary(
        string='Solde après (Destination)',
        compute='_compute_balances',
        currency_field='currency_id'
    )

    # Soldes stockés
    balance_before_from_stored = fields.Monetary(
        string='Solde avant (Source) - Stocké',
        currency_field='currency_id',
        readonly=True,
        help="Solde capturé au moment de la validation"
    )
    balance_after_from_stored = fields.Monetary(
        string='Solde après (Source) - Stocké',
        currency_field='currency_id',
        readonly=True
    )
    balance_before_to_stored = fields.Monetary(
        string='Solde avant (Destination) - Stocké',
        currency_field='currency_id',
        readonly=True
    )
    balance_after_to_stored = fields.Monetary(
        string='Solde après (Destination) - Stocké',
        currency_field='currency_id',
        readonly=True
    )

    # Champ color pour le kanban
    color = fields.Integer(
        string='Couleur',
        default=0
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Générer la référence automatiquement"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                sequence = self.env['ir.sequence'].search([
                    ('code', '=', 'treasury.transfer'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if not sequence:
                    sequence = self.env['ir.sequence'].create({
                        'name': 'Transfert de trésorerie',
                        'code': 'treasury.transfer',
                        'prefix': 'TR/%(year)s/',
                        'padding': 5,
                        'company_id': self.env.company.id,
                    })
                vals['name'] = sequence.next_by_id()
        return super().create(vals_list)

    def _check_source_destination_states(self):
        """Vérifier que les caisses/coffres source et destination sont dans le bon état"""
        self.ensure_one()

        # Vérifier les états selon le type
        if self.transfer_type in ['cash_to_cash', 'cash_to_safe']:
            if self.cash_from_id.state != 'open':
                raise UserError(_("La caisse source '%s' n'est pas ouverte !") % self.cash_from_id.name)
        elif self.transfer_type in ['safe_to_cash', 'safe_to_safe']:
            if self.safe_from_id.state != 'active':
                raise UserError(_("Le coffre source '%s' n'est pas actif !") % self.safe_from_id.name)

        if self.transfer_type in ['cash_to_cash', 'safe_to_cash']:
            if self.cash_to_id.state != 'open':
                raise UserError(_("La caisse destination '%s' n'est pas ouverte !") % self.cash_to_id.name)
        elif self.transfer_type in ['cash_to_safe', 'safe_to_safe']:
            if self.safe_to_id.state != 'active':
                raise UserError(_("Le coffre destination '%s' n'est pas actif !") % self.safe_to_id.name)

    @api.depends('cash_from_id', 'cash_to_id', 'safe_from_id', 'safe_to_id', 'amount', 'state', 'transfer_type')
    def _compute_balances(self):
        """Calculer les soldes avant/après pour affichage"""
        for transfer in self:
            # Source
            if transfer.transfer_type in ['cash_to_cash', 'cash_to_safe'] and transfer.cash_from_id:
                transfer.balance_before_from = transfer.cash_from_id.current_balance
                if transfer.state == 'done':
                    transfer.balance_after_from = transfer.balance_before_from - transfer.amount
                else:
                    transfer.balance_after_from = transfer.balance_before_from
            elif transfer.transfer_type in ['safe_to_cash', 'safe_to_safe'] and transfer.safe_from_id:
                transfer.balance_before_from = transfer.safe_from_id.current_balance
                if transfer.state == 'done':
                    transfer.balance_after_from = transfer.balance_before_from - transfer.amount
                else:
                    transfer.balance_after_from = transfer.balance_before_from
            else:
                transfer.balance_before_from = 0
                transfer.balance_after_from = 0

            # Destination
            if transfer.transfer_type in ['cash_to_cash', 'safe_to_cash'] and transfer.cash_to_id:
                transfer.balance_before_to = transfer.cash_to_id.current_balance
                if transfer.state == 'done':
                    transfer.balance_after_to = transfer.balance_before_to + transfer.amount
                else:
                    transfer.balance_after_to = transfer.balance_before_to
            elif transfer.transfer_type in ['cash_to_safe', 'safe_to_safe'] and transfer.safe_to_id:
                transfer.balance_before_to = transfer.safe_to_id.current_balance
                if transfer.state == 'done':
                    transfer.balance_after_to = transfer.balance_before_to + transfer.amount
                else:
                    transfer.balance_after_to = transfer.balance_before_to
            else:
                transfer.balance_before_to = 0
                transfer.balance_after_to = 0

    @api.constrains('transfer_type', 'cash_from_id', 'cash_to_id', 'safe_from_id', 'safe_to_id')
    def _check_transfer_consistency(self):
        """Vérifier la cohérence complète du transfert selon son type"""
        for transfer in self:
            # Vérifications par type de transfert
            if transfer.transfer_type == 'cash_to_cash':
                if not transfer.cash_from_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers caisse, vous devez sélectionner une caisse source."))
                if not transfer.cash_to_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers caisse, vous devez sélectionner une caisse destination."))
                if transfer.safe_from_id or transfer.safe_to_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers caisse, vous ne devez pas sélectionner de coffre."))
                if transfer.cash_from_id == transfer.cash_to_id:
                    raise ValidationError(_("La caisse source et la caisse destination doivent être différentes !"))

            elif transfer.transfer_type == 'cash_to_safe':
                if not transfer.cash_from_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers coffre, vous devez sélectionner une caisse source."))
                if not transfer.safe_to_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers coffre, vous devez sélectionner un coffre destination."))
                if transfer.cash_to_id or transfer.safe_from_id:
                    raise ValidationError(
                        _("Pour un transfert caisse vers coffre, vous ne devez pas sélectionner de caisse destination ou coffre source."))

            elif transfer.transfer_type == 'safe_to_cash':
                if not transfer.safe_from_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers caisse, vous devez sélectionner un coffre source."))
                if not transfer.cash_to_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers caisse, vous devez sélectionner une caisse destination."))
                if transfer.cash_from_id or transfer.safe_to_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers caisse, vous ne devez pas sélectionner de caisse source ou coffre destination."))

            elif transfer.transfer_type == 'safe_to_safe':
                if not transfer.safe_from_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers coffre, vous devez sélectionner un coffre source."))
                if not transfer.safe_to_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers coffre, vous devez sélectionner un coffre destination."))
                if transfer.cash_from_id or transfer.cash_to_id:
                    raise ValidationError(
                        _("Pour un transfert coffre vers coffre, vous ne devez pas sélectionner de caisse."))
                if transfer.safe_from_id == transfer.safe_to_id:
                    raise ValidationError(_("Le coffre source et le coffre destination doivent être différents !"))

    @api.constrains('amount')
    def _check_amount_positive(self):
        """Vérifier que le montant est positif"""
        for transfer in self:
            if transfer.amount <= 0:
                raise ValidationError(_("Le montant du transfert doit être strictement positif !"))

    def _create_cash_operations(self):
        """Créer les opérations de caisse IMMÉDIATEMENT en posted"""
        self.ensure_one()

        operation_obj = self.env['treasury.cash.operation']

        # Catégories
        cat_transfer_in = self.env.ref('adi_treasury.category_transfer_in', raise_if_not_found=False)
        cat_transfer_out = self.env.ref('adi_treasury.category_transfer_out', raise_if_not_found=False)

        # Créer les catégories si nécessaire
        if not cat_transfer_in or not cat_transfer_out:
            category_obj = self.env['treasury.operation.category']
            if not cat_transfer_out:
                cat_transfer_out = category_obj.create({
                    'name': 'Transfert sortant',
                    'code': 'TRANSFER_OUT',
                    'operation_type': 'out',
                    'sequence': 31
                })
            if not cat_transfer_in:
                cat_transfer_in = category_obj.create({
                    'name': 'Transfert entrant',
                    'code': 'TRANSFER_IN',
                    'operation_type': 'in',
                    'sequence': 30
                })

        # Pour les transferts impliquant des caisses
        if self.transfer_type == 'cash_to_safe' and self.cash_from_id:
            # Opération de sortie de la caisse
            op_out = operation_obj.create({
                'cash_id': self.cash_from_id.id,
                'operation_type': 'out',
                'category_id': cat_transfer_out.id,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfert vers coffre %s") % self.safe_to_id.name,
                'reference': self.name,
                'state': 'posted',  # IMPORTANT : directement posted
                'is_manual': False,
                'transfer_id': self.id,
            })
            self.cash_operation_out_id = op_out

        elif self.transfer_type == 'safe_to_cash' and self.cash_to_id:
            # Opération d'entrée dans la caisse
            op_in = operation_obj.create({
                'cash_id': self.cash_to_id.id,
                'operation_type': 'in',
                'category_id': cat_transfer_in.id,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfert depuis coffre %s") % self.safe_from_id.name,
                'reference': self.name,
                'state': 'posted',  # IMPORTANT : directement posted
                'is_manual': False,
                'transfer_id': self.id,
            })
            self.cash_operation_in_id = op_in

        elif self.transfer_type == 'cash_to_cash':
            # Sortie de la caisse source
            if self.cash_from_id:
                op_out = operation_obj.create({
                    'cash_id': self.cash_from_id.id,
                    'operation_type': 'out',
                    'category_id': cat_transfer_out.id,
                    'amount': self.amount,
                    'date': self.date,
                    'description': _("Transfert vers caisse %s") % self.cash_to_id.name,
                    'reference': self.name,
                    'state': 'posted',
                    'is_manual': False,
                    'transfer_id': self.id,
                })
                self.cash_operation_out_id = op_out

            # Entrée dans la caisse destination
            if self.cash_to_id:
                op_in = operation_obj.create({
                    'cash_id': self.cash_to_id.id,
                    'operation_type': 'in',
                    'category_id': cat_transfer_in.id,
                    'amount': self.amount,
                    'date': self.date,
                    'description': _("Transfert depuis caisse %s") % self.cash_from_id.name,
                    'reference': self.name,
                    'state': 'posted',
                    'is_manual': False,
                    'transfer_id': self.id,
                })
                self.cash_operation_in_id = op_in

    def action_confirm(self):
        """Confirmer le transfert - VERSION SIMPLIFIÉE"""
        for transfer in self:
            if transfer.state != 'draft':
                raise UserError(_("Seuls les transferts en brouillon peuvent être confirmés."))

            # Vérifications des états (caisses/coffres ouverts)
            transfer._check_source_destination_states()

            # Créer IMMÉDIATEMENT les opérations de caisse en état posted
            transfer._create_cash_operations()

            # Maintenant vérifier le solde APRÈS création des opérations
            if transfer.transfer_type in ['cash_to_cash', 'cash_to_safe'] and transfer.cash_from_id:
                # Forcer le recalcul du solde
                transfer.cash_from_id._compute_current_balance()

                if transfer.cash_from_id.current_balance < 0:
                    # Annuler les opérations créées
                    if transfer.cash_operation_out_id:
                        transfer.cash_operation_out_id.unlink()
                    if transfer.cash_operation_in_id:
                        transfer.cash_operation_in_id.unlink()

                    raise UserError(
                        _("Solde insuffisant dans la caisse '%s'.\n"
                          "Solde disponible : %s %s") % (
                            transfer.cash_from_id.name,
                            transfer.cash_from_id.current_balance + transfer.amount,
                            transfer.currency_id.symbol
                        )
                    )

            transfer.state = 'confirm'
            transfer.message_post(body=_("Transfert confirmé par %s") % self.env.user.name)

    def action_done(self):
        """Valider le transfert - SIMPLIFIÉ"""
        for transfer in self:
            if transfer.state != 'confirm':
                raise UserError(_("Seuls les transferts confirmés peuvent être effectués."))

            transfer.write({
                'state': 'done',
                'validated_by': self.env.user.id,
            })

            # Messages dans le chatter
            transfer._post_transfer_messages()

    def _post_transfer_messages(self):
        """Poster les messages de transfert dans les chatteurs des entités concernées"""
        self.ensure_one()

        # Message principal sur le transfert
        if self.transfer_type == 'cash_to_cash':
            msg = _("Transfert effectué de %s vers %s") % (self.cash_from_id.name, self.cash_to_id.name)
        elif self.transfer_type == 'cash_to_safe':
            msg = _("Transfert effectué de %s vers coffre %s") % (self.cash_from_id.name, self.safe_to_id.name)
        elif self.transfer_type == 'safe_to_cash':
            msg = _("Transfert effectué du coffre %s vers %s") % (self.safe_from_id.name, self.cash_to_id.name)
        else:
            msg = _("Transfert effectué du coffre %s vers coffre %s") % (self.safe_from_id.name, self.safe_to_id.name)

        self.message_post(body=msg)

        # Messages sur les entités concernées
        if self.transfer_type == 'cash_to_cash':
            if self.cash_from_id:
                self.cash_from_id.message_post(
                    body=_("Transfert sortant de %s %s vers %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.cash_to_id.name, self.name
                    )
                )
            if self.cash_to_id:
                self.cash_to_id.message_post(
                    body=_("Transfert entrant de %s %s depuis %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.cash_from_id.name, self.name
                    )
                )

        elif self.transfer_type == 'cash_to_safe':
            if self.cash_from_id:
                self.cash_from_id.message_post(
                    body=_("Transfert sortant de %s %s vers coffre %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.safe_to_id.name, self.name
                    )
                )
            if self.safe_to_id:
                self.safe_to_id.message_post(
                    body=_("Transfert entrant de %s %s depuis caisse %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.cash_from_id.name, self.name
                    )
                )

        elif self.transfer_type == 'safe_to_cash':
            if self.safe_from_id:
                self.safe_from_id.message_post(
                    body=_("Transfert sortant de %s %s vers caisse %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.cash_to_id.name, self.name
                    )
                )
            if self.cash_to_id:
                self.cash_to_id.message_post(
                    body=_("Transfert entrant de %s %s depuis coffre %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.safe_from_id.name, self.name
                    )
                )

        elif self.transfer_type == 'safe_to_safe':
            if self.safe_from_id:
                self.safe_from_id.message_post(
                    body=_("Transfert sortant de %s %s vers coffre %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.safe_to_id.name, self.name
                    )
                )
            if self.safe_to_id:
                self.safe_to_id.message_post(
                    body=_("Transfert entrant de %s %s depuis coffre %s (Réf: %s)") % (
                        self.amount, self.currency_id.symbol,
                        self.safe_from_id.name, self.name
                    )
                )

    def action_cancel(self):
        """Annuler le transfert et ses opérations"""
        for transfer in self:
            if transfer.state == 'done':
                raise UserError(_("Un transfert effectué ne peut pas être annulé."))

            # Supprimer les opérations de caisse liées
            operations_to_delete = self.env['treasury.cash.operation']
            if transfer.cash_operation_out_id:
                operations_to_delete |= transfer.cash_operation_out_id
            if transfer.cash_operation_in_id:
                operations_to_delete |= transfer.cash_operation_in_id

            operations_to_delete.unlink()

            transfer.state = 'cancel'
            transfer.message_post(body=_("Transfert annulé par %s") % self.env.user.name)

    def action_draft(self):
        """Remettre en brouillon"""
        for transfer in self:
            if transfer.state != 'cancel':
                raise UserError(_("Seuls les transferts annulés peuvent être remis en brouillon."))
            transfer.state = 'draft'

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Réinitialiser les champs selon le type de transfert"""
        if self.transfer_type == 'cash_to_cash':
            self.safe_from_id = False
            self.safe_to_id = False
        elif self.transfer_type == 'cash_to_safe':
            self.safe_from_id = False
            self.cash_to_id = False
        elif self.transfer_type == 'safe_to_cash':
            self.cash_from_id = False
            self.safe_to_id = False
        elif self.transfer_type == 'safe_to_safe':
            self.cash_from_id = False
            self.cash_to_id = False

    @api.onchange('cash_from_id')
    def _onchange_cash_from_id(self):
        """Mettre à jour le domaine de la caisse destination"""
        if self.cash_from_id and self.transfer_type == 'cash_to_cash':
            return {
                'domain': {
                    'cash_to_id': [
                        ('id', '!=', self.cash_from_id.id),
                        ('state', '=', 'open'),
                        ('currency_id', '=', self.cash_from_id.currency_id.id),
                        ('company_id', '=', self.company_id.id)
                    ]
                }
            }

    def name_get(self):
        """Personnaliser l'affichage du nom"""
        result = []
        for transfer in self:
            name = transfer.name
            if transfer.state == 'draft':
                name = f"{name} (Brouillon)"
            elif transfer.state == 'cancel':
                name = f"{name} (Annulé)"
            result.append((transfer.id, name))
        return result
