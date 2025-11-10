# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class TreasuryCashOperation(models.Model):
    _name = 'treasury.cash.operation'
    _description = 'Opération de caisse'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    cash_id = fields.Many2one(
        'treasury.cash',
        string='Caisse',
        required=True,
        domain="[('state', '=', 'open')]",
        tracking=True
    )

    operation_type = fields.Selection([
        ('in', 'Entrée'),
        ('out', 'Sortie')
    ], string='Type', required=True, tracking=True)

    category_id = fields.Many2one(
        'treasury.operation.category',
        string='Catégorie',
        required=True,
        domain="[('operation_type', 'in', [operation_type, 'both'])]",
        tracking=True
    )

    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='cash_id.currency_id',
        store=True
    )

    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    description = fields.Text(
        string='Description'
    )

    reference = fields.Char(
        string='Référence externe',
        help="Numéro de facture, bon, etc."
    )

    # Lien avec les paiements Odoo
    payment_id = fields.Many2one(
        'account.payment',
        string='Paiement lié',
        readonly=True,
        help="Paiement Odoo qui a généré cette opération"
    )
    is_manual = fields.Boolean(
        string='Opération manuelle',
        default=False,
        help="Indique si l'opération a été créée manuellement"
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('posted', 'Comptabilisé'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True)

    # Clôture
    closing_id = fields.Many2one(
        'treasury.cash.closing',
        string='Clôture',
        readonly=True
    )

    # Pièces jointes
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Pièces jointes'
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count'
    )

    # Utilisateur
    user_id = fields.Many2one(
        'res.users',
        string='Créé par',
        default=lambda self: self.env.user,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        related='cash_id.company_id',
        store=True
    )
    # Lien avec le transfert
    # Dans treasury_cash_operation.py, ajouter ce champ
    transfer_id = fields.Many2one(
        'treasury.transfer',
        string='Transfert lié',
        readonly=True,
        ondelete='cascade',
        help="Transfert qui a généré cette opération"
    )

    # Ajout des champs et modèles nécessaire pour gérer
    # l'opération marsk as collected

    is_collected = fields.Boolean(
        string='Prélevé en caisse',
        default=False,
        tracking=True,
        help="Indique si cette opération a déjà été collectée dans une clôture"
    )

    collected_date = fields.Datetime(
        string='Date de prélèvement',
        readonly=True
    )

    collected_by = fields.Many2one(
        'res.users',
        string='Prélevé par',
        readonly=True
    )


    _sql_constraints = [
        ('unique_closing_operation',
         'UNIQUE(closing_id, id)',
         'Une opération ne peut appartenir qu\'à une seule clôture !'),
    ]

    def write(self, vals):
        """Override write pour vérifier les contraintes"""
        if 'closing_id' in vals and vals.get('closing_id'):
            for operation in self:
                if operation.closing_id and operation.closing_id.id != vals['closing_id']:
                    raise ValidationError(_(
                        "Cette opération est déjà associée à la clôture '%s' et ne peut pas être transférée à une autre clôture !"
                    ) % operation.closing_id.name)

        return super().write(vals)

    # Ajouter une méthode pour marquer comme prélevé
    def action_mark_collected(self):
        """Marquer l'opération comme prélevée"""
        for operation in self:
            if operation.state != 'posted':
                raise UserError(_("Seules les opérations comptabilisées peuvent être marquées comme prélevées."))

            if operation.is_collected:
                raise UserError(_("Cette opération est déjà marquée comme prélevée."))

            # Chercher ou créer une clôture pour cette opération
            today = fields.Date.today()
            closing = self.env['treasury.cash.closing'].search([
                ('cash_id', '=', operation.cash_id.id),
                ('state', 'in', ['draft', 'confirmed']),
                ('closing_date', '=', today)
            ], limit=1)

            if not closing:
                # Créer une nouvelle clôture
                closing = self.env['treasury.cash.closing'].create({
                    'cash_id': operation.cash_id.id,
                    'closing_date': today,
                })

            operation.write({
                'is_collected': True,
                'collected_date': fields.Datetime.now(),
                'collected_by': self.env.user.id,
                'closing_id': closing.id
            })

            # Message dans le chatter
            operation.message_post(
                body=_("✓ Opération marquée comme prélevée et ajoutée à la clôture %s") % closing.name
            )

            # Rafraîchir la clôture
            closing._compute_totals()
            closing._compute_closing_lines()

        return True

    def action_unmark_collected(self):
        """Retirer le marquage de prélèvement"""
        for operation in self:
            if not operation.is_collected:
                continue

            if operation.closing_id and operation.closing_id.state == 'validated':
                raise UserError(_(
                    "Impossible de retirer le marquage : cette opération fait partie de la clôture validée '%s'."
                ) % operation.closing_id.name)

            # Retirer de la clôture
            closing = operation.closing_id
            operation.write({
                'is_collected': False,
                'collected_date': False,
                'collected_by': False,
                'closing_id': False
            })

            # Message
            operation.message_post(
                body=_("⚠️ Marquage de prélèvement retiré")
            )

            # Rafraîchir la clôture si elle existe
            if closing:
                closing._compute_totals()
                closing._compute_closing_lines()

        return True
    # Fin des traitement marquer comem prélevé

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for operation in self:
            operation.attachment_count = len(operation.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Vérifier qu'une clôture est en cours avant de créer"""
        for vals in vals_list:
            # Si pas de clôture spécifiée, en chercher ou créer une
            if 'closing_id' not in vals or not vals.get('closing_id'):
                if 'cash_id' in vals:
                    cash = self.env['treasury.cash'].browse(vals['cash_id'])

                    # Rechercher une clôture en cours pour aujourd'hui
                    today = fields.Date.today()
                    pending_closing = self.env['treasury.cash.closing'].search([
                        ('cash_id', '=', vals['cash_id']),
                        ('state', 'in', ['draft', 'confirmed']),
                        ('closing_date', '=', today)
                    ], limit=1)

                    if not pending_closing:
                        # Créer automatiquement une clôture
                        closing_vals = {
                            'cash_id': vals['cash_id'],
                            'closing_date': today,
                        }
                        pending_closing = self.env['treasury.cash.closing'].create(closing_vals)
                        cash.message_post(
                            body=_(
                                "✓ Clôture automatique créée pour permettre l'enregistrement d'opérations : %s") % pending_closing.name
                        )

                    vals['closing_id'] = pending_closing.id

            # Marquer comme manuel si créé directement
            if not vals.get('payment_id'):
                vals['is_manual'] = True

            # Générer la référence
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                sequence = self.env['ir.sequence'].search([
                    ('code', '=', 'treasury.cash.operation'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if not sequence:
                    sequence = self.env['ir.sequence'].create({
                        'name': 'Opération de caisse',
                        'code': 'treasury.cash.operation',
                        'prefix': 'OPC/%(year)s/',
                        'padding': 5,
                        'company_id': self.env.company.id,
                    })
                vals['name'] = sequence.next_by_id()

        return super().create(vals_list)

    # Modifier la contrainte pour les opérations de transfert
    @api.constrains('closing_id', 'transfer_id')
    def _check_operation_closing(self):
        """Les opérations de transfert n'ont pas besoin de clôture immédiate"""
        for operation in self:
            if not operation.transfer_id and not operation.closing_id and operation.state == 'posted':
                # Chercher automatiquement une clôture
                today = fields.Date.today()
                pending_closing = self.env['treasury.cash.closing'].search([
                    ('cash_id', '=', operation.cash_id.id),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('closing_date', '=', today)
                ], limit=1)

                if not pending_closing:
                    # Créer une clôture
                    pending_closing = self.env['treasury.cash.closing'].create({
                        'cash_id': operation.cash_id.id,
                        'closing_date': today,
                    })

                operation.closing_id = pending_closing

    @api.constrains('amount')
    def _check_amount(self):
        """Vérifier que le montant est positif"""
        for operation in self:
            if operation.amount <= 0:
                raise ValidationError(_("Le montant doit être positif !"))

    @api.constrains('operation_type', 'amount', 'cash_id')
    def _check_cash_balance(self):
        """Vérifier le solde pour les sorties"""
        for operation in self:
            if operation.operation_type == 'out' and operation.state == 'posted':
                # Calculer le solde disponible
                balance = operation.cash_id.current_balance
                # Ajouter cette sortie car elle est déjà déduite
                balance += operation.amount

                if balance < operation.amount:
                    raise ValidationError(
                        _("Solde insuffisant dans la caisse '%s'.\n"
                          "Solde disponible : %s %s\n"
                          "Montant demandé : %s %s") % (
                            operation.cash_id.name,
                            balance,
                            operation.currency_id.symbol,
                            operation.amount,
                            operation.currency_id.symbol
                        )
                    )

    def action_post(self):
        """Comptabiliser l'opération"""
        for operation in self:
            if operation.state != 'draft':
                raise UserError(_("Seules les opérations en brouillon peuvent être comptabilisées."))

            # Si c'est une opération de transfert, elle est déjà posted
            if operation.transfer_id:
                raise UserError(_("Les opérations de transfert sont automatiquement comptabilisées."))

            # Vérifier la clôture
            operation.cash_id._check_closing_required()

            # Vérifier le solde pour les sorties
            if operation.operation_type == 'out':
                if operation.cash_id.current_balance < operation.amount:
                    raise UserError(
                        _("Solde insuffisant dans la caisse '%s'.\n"
                          "Solde disponible : %s %s") % (
                            operation.cash_id.name,
                            operation.cash_id.current_balance,
                            operation.currency_id.symbol
                        )
                    )

            operation.state = 'posted'
            operation.message_post(
                body=_("Opération comptabilisée : %s %s") % (
                    operation.amount,
                    operation.currency_id.symbol
                )
            )

    def action_cancel(self):
        """Annuler l'opération"""
        for operation in self:
            if operation.closing_id:
                raise UserError(
                    _("Cette opération fait partie de la clôture '%s' et ne peut pas être annulée.") %
                    operation.closing_id.name
                )
            operation.state = 'cancel'

    def action_draft(self):
        """Remettre en brouillon"""
        for operation in self:
            if operation.state != 'cancel':
                raise UserError(_("Seules les opérations annulées peuvent être remises en brouillon."))
            operation.state = 'draft'

    def action_view_attachments(self):
        """Voir les pièces jointes"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pièces jointes'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }

    @api.onchange('operation_type')
    def _onchange_operation_type(self):
        """Réinitialiser la catégorie si le type change"""
        self.category_id = False

    # Ajoutez ces champs dans la classe TreasuryCashOperation
    partner_id = fields.Many2one(
        'res.partner',
        string='Tiers',
        help="Client ou fournisseur concerné par l'opération"
    )

    observations = fields.Text(
        string='Observations',
        help="Notes ou observations sur l'opération"
    )
    # # filtrage
    is_today = fields.Boolean(
        string="Aujourd'hui",
        compute='_compute_date_filters',
        search='_search_is_today',
        store=False
    )

    is_this_week = fields.Boolean(
        string="Cette semaine",
        compute='_compute_date_filters',
        search='_search_is_this_week',
        store=False
    )

    is_this_month = fields.Boolean(
        string="Ce mois",
        compute='_compute_date_filters',
        search='_search_is_this_month',
        store=False
    )

    @api.depends('date')
    def _compute_date_filters(self):
        """Calculer les filtres de date"""
        today = fields.Date.today()
        for record in self:
            if record.date:
                record_date = record.date.date() if hasattr(record.date, 'date') else record.date
                record.is_today = record_date == today
                # Semaine
                week_start = today - timedelta(days=today.weekday())
                record.is_this_week = record_date >= week_start
                # Mois
                record.is_this_month = record_date.year == today.year and record_date.month == today.month
            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False

    @api.model
    def _search_is_today(self, operator, value):
        """Recherche pour aujourd'hui"""
        today = fields.Date.today()
        if operator == '=' and value:
            return [
                ('date', '>=', datetime.combine(today, datetime.min.time())),
                ('date', '<=', datetime.combine(today, datetime.max.time()))
            ]
        return []

    @api.model
    def _search_is_this_week(self, operator, value):
        """Recherche pour cette semaine"""
        today = fields.Date.today()
        if operator == '=' and value:
            week_start = today - timedelta(days=today.weekday())
            return [('date', '>=', datetime.combine(week_start, datetime.min.time()))]
        return []

    @api.model
    def _search_is_this_month(self, operator, value):
        """Recherche pour ce mois"""
        today = fields.Date.today()
        if operator == '=' and value:
            month_start = today.replace(day=1)
            return [('date', '>=', datetime.combine(month_start, datetime.min.time()))]
        return []
    ##

    # Modifier la méthode create pour récupérer le partenaire depuis le paiement
    def create_from_payment(self, payment):
        """Créer une opération depuis un paiement"""
        # Déterminer le type et la catégorie
        if payment.payment_type == 'inbound':
            operation_type = 'in'
            category = self.env['treasury.operation.category'].search([
                ('is_customer_payment', '=', True)
            ], limit=1)
        else:
            operation_type = 'out'
            category = self.env['treasury.operation.category'].search([
                ('is_vendor_payment', '=', True)
            ], limit=1)

        if category:
            return self.create({
                'cash_id': payment.journal_id.treasury_cash_id.id,  # Assumant qu'on ajoute ce lien
                'operation_type': operation_type,
                'category_id': category.id,
                'amount': payment.amount,
                'date': fields.Datetime.to_datetime(payment.date),
                'partner_id': payment.partner_id.id,  # Récupérer le partenaire
                'description': _("Paiement %s") % payment.name,
                'observations': payment.ref or '',  # Récupérer la référence comme observation
                'reference': payment.name,
                'payment_id': payment.id,
                'state': 'posted',
            })





    @api.model
    def create_manual_operation_with_closing(self, vals):
        """Créer une opération manuelle en créant automatiquement une clôture si nécessaire"""
        cash_id = vals.get('cash_id')
        if not cash_id:
            raise ValidationError(_("Veuillez sélectionner une caisse."))

        cash = self.env['treasury.cash'].browse(cash_id)

        # Chercher une clôture en cours
        pending_closing = self.env['treasury.cash.closing'].search([
            ('cash_id', '=', cash_id),
            ('state', 'in', ['draft', 'confirmed']),
            ('closing_date', '=', fields.Date.today())
        ], limit=1)

        # Si pas de clôture, en créer une automatiquement
        if not pending_closing:
            closing_vals = {
                'cash_id': cash_id,
                'closing_date': fields.Date.today(),
            }
            pending_closing = self.env['treasury.cash.closing'].create(closing_vals)
            cash.message_post(
                body=_(
                    "✓ Clôture automatique créée pour permettre l'enregistrement d'opérations : %s") % pending_closing.name
            )

        # Assigner la clôture à l'opération
        vals['closing_id'] = pending_closing.id

        # Créer l'opération
        operation = self.create(vals)

        # Si l'opération est créée en état 'posted', mettre à jour la clôture
        if operation.state == 'posted':
            pending_closing._compute_totals()
            pending_closing._compute_closing_lines()

        return operation


