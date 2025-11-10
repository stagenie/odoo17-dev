# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)


class TreasuryCashClosing(models.Model):
    _name = 'treasury.cash.closing'
    _description = 'Clôture de caisse'
    _order = 'closing_date desc, closing_number desc'
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
        readonly="state != 'draft'",
        tracking=True
    )

    # Une seule date pour la clôture
    closing_date = fields.Date(
        string='Date de clôture',
        required=True,
        default=fields.Date.today,
        readonly="state != 'draft'",
        tracking=True
    )

    closing_number = fields.Integer(
        string='N° de clôture du jour',
        default=1,
        readonly=True,
        help="Numéro de clôture dans la journée (1, 2, 3...)"
    )

    # Champs calculés pour la période
    period_start = fields.Datetime(
        string='Début de période',
        compute='_compute_period',
        store=True
    )

    period_end = fields.Datetime(
        string='Fin de période',
        compute='_compute_period',
        store=True
    )

    # Soldes
    balance_start = fields.Monetary(
        string='Solde de départ',
        currency_field='currency_id',
        compute='_compute_balance_start',
        store=True,
        readonly=True,
        help="Calculé automatiquement depuis la dernière clôture"
    )

    balance_end_theoretical = fields.Monetary(
        string='Solde théorique',
        currency_field='currency_id',
        compute='_compute_theoretical_balance',
        store=True
    )

    balance_end_real = fields.Monetary(
        string='Solde réel (compté)',
        currency_field='currency_id',
        readonly="state != 'draft'",
        tracking=True
    )

    difference = fields.Monetary(
        string='Écart',
        currency_field='currency_id',
        compute='_compute_difference',
        store=True
    )

    # Totaux des opérations
    total_in = fields.Monetary(
        string='Total entrées',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )

    total_out = fields.Monetary(
        string='Total sorties',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )

    # Relations
    operation_ids = fields.One2many(
        'treasury.cash.operation',
        'closing_id',
        string='Opérations'
    )

    line_ids = fields.One2many(
        'treasury.cash.closing.line',
        'closing_id',
        string='Détail des opérations'
    )

    adjustment_operation_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération d\'ajustement',
        readonly=True
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé'),
        ('cancel', 'Annulé')  # Nouvel état
    ], string='État', default='draft', tracking=True)
    #
    # Ajouter ces méthodes dans la classe TreasuryCashClosing

    def action_show_all_operations(self):
        """Afficher toutes les opérations"""
        self.ensure_one()
        return {
            'name': _('Toutes les opérations'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'tree,form',
            'domain': [('closing_id', '=', self.id)],
            'context': {'default_closing_id': self.id}
        }

    def action_show_auto_operations(self):
        """Afficher uniquement les opérations automatiques"""
        self.ensure_one()
        return {
            'name': _('Opérations automatiques'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'tree,form',
            'domain': [
                ('closing_id', '=', self.id),
                ('payment_id', '!=', False)
            ],
            'context': {'default_closing_id': self.id}
        }

    def action_show_manual_operations(self):
        """Afficher uniquement les opérations manuelles"""
        self.ensure_one()
        return {
            'name': _('Opérations manuelles'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'tree,form',
            'domain': [
                ('closing_id', '=', self.id),
                ('is_manual', '=', True)
            ],
            'context': {'default_closing_id': self.id}
        }

    # Ajouter après la méthode action_back_to_draft
    def action_cancel(self):
        """Annuler la clôture avec vérifications"""
        for closing in self:
            if closing.state == 'cancel':
                continue

            # Vérification 1 : Pas de clôture ultérieure
            later_closings = self.search([
                ('cash_id', '=', closing.cash_id.id),
                ('state', '!=', 'cancel'),
                '|',
                ('closing_date', '>', closing.closing_date),
                '&',
                ('closing_date', '=', closing.closing_date),
                ('closing_number', '>', closing.closing_number)
            ])

            if later_closings:
                raise UserError(_(
                    "Impossible d'annuler cette clôture car il existe des clôtures ultérieures.\n"
                    "Clôtures concernées : %s"
                ) % ', '.join(later_closings.mapped('name')))

            # Vérification 2 : Si validée avec ajustement
            if closing.state == 'validated' and closing.adjustment_operation_id:
                if closing.adjustment_operation_id.state == 'posted':
                    # Annuler l'opération d'ajustement
                    closing.adjustment_operation_id.state = 'cancel'
                    closing.adjustment_operation_id.message_post(
                        body=_("Opération annulée suite à l'annulation de la clôture %s") % closing.name
                    )

            # Vérification 3 : Libérer les opérations
            if closing.operation_ids:
                # Pour les opérations manuelles uniquement (pas celles liées aux paiements)
                manual_operations = closing.operation_ids.filtered(lambda o: not o.payment_id)
                if manual_operations:
                    # Demander confirmation
                    if not self._context.get('force_cancel'):
                        raise UserError(_(
                            "Cette clôture contient %d opérations manuelles.\n"
                            "Voulez-vous vraiment l'annuler ?\n"
                            "Les opérations manuelles seront dissociées de la clôture."
                        ) % len(manual_operations))

                # Dissocier toutes les opérations
                closing.operation_ids.write({'closing_id': False})

            # Annuler la clôture
            closing.write({
                'state': 'cancel',
                'validated_by': False,
            })

            # Message dans le chatter
            closing.message_post(
                body=_("Clôture annulée par %s<br/>"
                       "Raison : %s") % (
                         self.env.user.name,
                         self._context.get('cancel_reason', 'Non spécifiée')
                     )
            )

            # Mettre à jour la caisse si nécessaire
            if closing.cash_id.last_closing_id == closing:
                # Retrouver la clôture précédente valide
                previous_closing = self.search([
                    ('cash_id', '=', closing.cash_id.id),
                    ('state', '=', 'validated'),
                    ('id', '!=', closing.id)
                ], order='closing_date desc, closing_number desc', limit=1)

                if previous_closing:
                    closing.cash_id.write({
                        'last_closing_date': previous_closing.period_end,
                        'last_closing_balance': previous_closing.balance_end_real,
                        'last_closing_id': previous_closing.id
                    })
                else:
                    closing.cash_id.write({
                        'last_closing_date': False,
                        'last_closing_balance': 0.0,
                        'last_closing_id': False
                    })

        return True

    # Autres
    currency_id = fields.Many2one(
        'res.currency',
        related='cash_id.currency_id',
        store=True
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
        related='cash_id.company_id',
        store=True
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.depends('closing_date', 'closing_number', 'cash_id')
    def _compute_period(self):
        """Calculer automatiquement la période de la clôture"""
        for closing in self:
            if not closing.closing_date or not closing.cash_id:
                closing.period_start = False
                closing.period_end = False
                continue

            # La fin est maintenant (ou 23:59:59 du jour de clôture si on est plus tard)
            now = fields.Datetime.now()
            end_of_day = datetime.combine(closing.closing_date, datetime.max.time()).replace(microsecond=0)

            # Si on est le jour de la clôture, la fin est maintenant
            # Sinon c'est 23:59:59 du jour de clôture
            if now.date() == closing.closing_date and now < end_of_day:
                closing.period_end = now
            else:
                closing.period_end = end_of_day

            if closing.closing_number == 1:
                # Première clôture : depuis minuit
                closing.period_start = datetime.combine(closing.closing_date, datetime.min.time())
            else:
                # Clôtures suivantes : depuis la dernière clôture validée du jour
                last_closing = self.search([
                    ('cash_id', '=', closing.cash_id.id),
                    ('closing_date', '=', closing.closing_date),
                    ('closing_number', '<', closing.closing_number),
                    ('state', '=', 'validated')
                ], order='closing_number desc', limit=1)

                if last_closing and last_closing.period_end:
                    closing.period_start = last_closing.period_end + timedelta(seconds=1)
                else:
                    closing.period_start = datetime.combine(closing.closing_date, datetime.min.time())

    @api.depends('cash_id', 'closing_number', 'closing_date', 'period_start')
    def _compute_balance_start(self):
        """Calculer automatiquement le solde de départ"""
        for closing in self:
            if not closing.cash_id:
                closing.balance_start = 0
                continue

            # Chercher la dernière clôture validée
            last_closing = self.search([
                ('cash_id', '=', closing.cash_id.id),
                ('state', '=', 'validated'),
                '|',
                ('closing_date', '<', closing.closing_date),
                '&',
                ('closing_date', '=', closing.closing_date),
                ('closing_number', '<', closing.closing_number)
            ], order='closing_date desc, closing_number desc', limit=1)

            if last_closing:
                closing.balance_start = last_closing.balance_end_real
            else:
                # Pas de clôture précédente : calculer le solde depuis le début jusqu'à la période
                balance = 0.0

                if closing.period_start:
                    # Prendre toutes les opérations AVANT le début de cette clôture
                    previous_operations = self.env['treasury.cash.operation'].search([
                        ('cash_id', '=', closing.cash_id.id),
                        ('state', '=', 'posted'),
                        ('date', '<', closing.period_start)
                    ])

                    for op in previous_operations:
                        if op.operation_type == 'in':
                            balance += op.amount
                        else:
                            balance -= op.amount

                    # Ajouter les transferts entrants AVANT la période
                    in_transfers = self.env['treasury.transfer'].search([
                        ('cash_to_id', '=', closing.cash_id.id),
                        ('state', '=', 'done'),
                        ('date', '<', closing.period_start)
                    ])
                    balance += sum(in_transfers.mapped('amount'))

                    # Soustraire les transferts sortants AVANT la période
                    out_transfers = self.env['treasury.transfer'].search([
                        ('cash_from_id', '=', closing.cash_id.id),
                        ('state', '=', 'done'),
                        ('date', '<', closing.period_start)
                    ])
                    balance -= sum(out_transfers.mapped('amount'))

                    # Ajouter les opérations d'initialisation de coffre vers caisse
                    safe_to_cash_transfers = self.env['treasury.transfer'].search([
                        ('transfer_type', '=', 'safe_to_cash'),
                        ('cash_to_id', '=', closing.cash_id.id),
                        ('state', '=', 'done'),
                        ('date', '<', closing.period_start)
                    ])
                    balance += sum(safe_to_cash_transfers.mapped('amount'))

                closing.balance_start = balance

    @api.model_create_multi
    def create(self, vals_list):
        """Override pour gérer la numérotation journalière"""
        for vals in vals_list:
            if 'closing_date' in vals and 'cash_id' in vals:
                # Compter les clôtures du jour
                closing_date = vals.get('closing_date')
                existing_closings = self.search_count([
                    ('cash_id', '=', vals['cash_id']),
                    ('closing_date', '=', closing_date),
                ])
                vals['closing_number'] = existing_closings + 1

                # Générer la référence
                if vals.get('name', _('Nouveau')) == _('Nouveau'):
                    cash = self.env['treasury.cash'].browse(vals['cash_id'])
                    vals['name'] = f"CLO/{cash.code}/{closing_date}/{vals['closing_number']:02d}"

        # Créer l'objet
        closings = super().create(vals_list)

        # Charger automatiquement les opérations
        for closing in closings:
            closing.action_load_operations()
            closing._compute_closing_lines()

        return closings


    @api.depends('operation_ids', 'operation_ids.state', 'operation_ids.amount', 'operation_ids.operation_type')
    def _compute_totals(self):
        """Calculer les totaux des opérations"""
        for closing in self:
            operations = closing.operation_ids.filtered(lambda o: o.state == 'posted')
            total_in = 0.0
            total_out = 0.0

            for op in operations:
                if op.operation_type == 'in':
                    total_in += op.amount
                else:  # out
                    total_out += op.amount

            closing.total_in = total_in
            closing.total_out = total_out

    @api.depends('balance_start', 'total_in', 'total_out')
    def _compute_theoretical_balance(self):
        """Calculer le solde théorique"""
        for closing in self:
            closing.balance_end_theoretical = closing.balance_start + closing.total_in - closing.total_out

    @api.depends('balance_end_theoretical', 'balance_end_real')
    def _compute_difference(self):
        """Calculer l'écart"""
        for closing in self:
            if closing.balance_end_real is not None:
                closing.difference = closing.balance_end_real - closing.balance_end_theoretical
            else:
                closing.difference = 0.0

    def _compute_closing_lines(self):
        """Calculer les lignes de détail avec solde cumulé"""
        for closing in self:
            if not closing.id:
                continue

            # Supprimer les anciennes lignes
            closing.line_ids.unlink()

            lines_data = []
            running_balance = closing.balance_start

            # Ligne de solde initial
            lines_data.append({
                'sequence': 0,
                'date': closing.period_start or fields.Datetime.now(),
                'operation_type': 'initial',
                'description': _('Solde initial (report du solde précédent)') if closing.balance_start != 0 else _(
                    'Solde initial'),
                'amount_in': 0,
                'amount_out': 0,
                'cumulative_balance': running_balance,
                'closing_id': closing.id,
            })

            # Lignes des opérations
            operations = closing.operation_ids.filtered(
                lambda o: o.state == 'posted'
            ).sorted('date')

            for seq, op in enumerate(operations, 1):
                if op.operation_type == 'in':
                    running_balance += op.amount
                    amount_in = op.amount
                    amount_out = 0
                else:
                    running_balance -= op.amount
                    amount_in = 0
                    amount_out = op.amount

                lines_data.append({
                    'sequence': seq,
                    'date': op.date,
                    'operation_id': op.id,
                    'partner_id': op.partner_id.id if op.partner_id else False,
                    'category_id': op.category_id.id,
                    'operation_type': op.operation_type,
                    'description': op.description,
                    'reference': op.reference,
                    'amount_in': amount_in,
                    'amount_out': amount_out,
                    'cumulative_balance': running_balance,
                    'closing_id': closing.id,
                })

            # Créer les nouvelles lignes
            self.env['treasury.cash.closing.line'].create(lines_data)

    def action_load_operations(self):
        """Charger automatiquement toutes les opérations de la période"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Les opérations ne peuvent être chargées qu'en brouillon."))

        if not self.period_start or not self.period_end:
            return

        # Rechercher les opérations non clôturées de la période
        operations = self.env['treasury.cash.operation'].search([
            ('cash_id', '=', self.cash_id.id),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'posted'),
            ('closing_id', '=', False),
            ('is_collected', '=', False)
        ])

        # Les assigner à cette clôture
        operations.write({'closing_id': self.id})

        # Créer les opérations depuis les paiements non traités
        self._create_operations_from_payments()

        # Recalculer les lignes
        self._compute_closing_lines()

        if len(self.operation_ids) > 0:
            self.message_post(body=_("%d opérations chargées pour la clôture.") % len(self.operation_ids))

        return True

    def _create_operations_from_payments(self):
        """Créer les opérations depuis tous les paiements"""
        if not self.cash_id or not self.cash_id.journal_id or not self.period_start or not self.period_end:
            return

        # Rechercher TOUS les paiements
        domain = [
            '|',
            ('journal_id', '=', self.cash_id.journal_id.id),
            ('is_cash_collected', '=', True),
            ('date', '>=', self.period_start.date()),
            ('date', '<=', self.period_end.date()),
            ('state', '=', 'posted'),
            ('treasury_operation_id', '=', False)
        ]

        if self.cash_id:
            domain.append('|')
            domain.append(('cash_id', '=', False))
            domain.append(('cash_id', '=', self.cash_id.id))

        payments = self.env['account.payment'].search(domain)

        for payment in payments:
            # Déterminer le type et la catégorie
            if payment.payment_type == 'inbound':
                if payment.partner_type == 'customer':
                    operation_type = 'in'
                    category = self.env['treasury.operation.category'].search([
                        ('is_customer_payment', '=', True)
                    ], limit=1)
                else:  # supplier
                    operation_type = 'in'
                    category = self.env['treasury.operation.category'].search([
                        ('code', '=', 'REFUND_SUPPLIER')
                    ], limit=1)
            else:  # outbound
                if payment.partner_type == 'supplier':
                    operation_type = 'out'
                    category = self.env['treasury.operation.category'].search([
                        ('is_vendor_payment', '=', True)
                    ], limit=1)
                else:  # customer
                    operation_type = 'out'
                    category = self.env['treasury.operation.category'].search([
                        ('code', '=', 'REFUND_CUSTOMER')
                    ], limit=1)

            if category:
                operation = self.env['treasury.cash.operation'].create({
                    'cash_id': self.cash_id.id,
                    'operation_type': operation_type,
                    'category_id': category.id,
                    'amount': payment.amount,
                    'date': fields.Datetime.to_datetime(payment.date),
                    'partner_id': payment.partner_id.id,
                    'description': _("Paiement %s - %s") % (
                        payment.name,
                        payment.partner_id.name if payment.partner_id else 'N/A'
                    ),
                    'reference': payment.name,
                    'payment_id': payment.id,
                    'closing_id': self.id,
                    'state': 'posted',
                })

                payment.treasury_operation_id = operation

    def action_create_manual_operation(self):
        """Créer une opération manuelle directement depuis la clôture"""
        self.ensure_one()

        if self.state == 'validated':
            raise UserError(_("Impossible d'ajouter des opérations à une clôture validée."))

        return {
            'name': _('Nouvelle opération manuelle'),
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'form',
            'context': {
                'default_cash_id': self.cash_id.id,
                'default_closing_id': self.id,
                'default_date': fields.Datetime.now(),
                'default_is_manual': True,
            },
            'target': 'new',
        }

    def action_confirm(self):
        """Confirmer la clôture"""
        for closing in self:
            if closing.state != 'draft':
                raise UserError(_("Seules les clôtures en brouillon peuvent être confirmées."))

            # Charger automatiquement les opérations si pas déjà fait
            #if not closing.operation_ids:

            closing.action_load_operations() # Toujours charger les opérationsé

            # NOUVEAU : Vérifier qu'il n'y a pas d'opérations manuelles en brouillon
            draft_manual_operations = closing.operation_ids.filtered(
                lambda o: o.state == 'draft' and o.is_manual
            )

            if draft_manual_operations:
                operations_list = '\n'.join(
                    [f"- {op.name} ({op.category_id.name})" for op in draft_manual_operations[:5]])
                if len(draft_manual_operations) > 5:
                    operations_list += f"\n... et {len(draft_manual_operations) - 5} autres"

                raise UserError(_(
                    "Impossible de confirmer la clôture car il y a %d opération(s) manuelle(s) en brouillon.\n\n"
                    "Opérations à valider :\n%s\n\n"
                    "Veuillez d'abord comptabiliser ces opérations."
                ) % (len(draft_manual_operations), operations_list))

            # Vérifier que le solde réel a été saisi
            if closing.balance_end_real is None:
                raise UserError(_("Veuillez saisir le solde réel (compté) avant de confirmer."))

            closing.write({
                'state': 'confirmed'
            })

            # Message dans le chatter
            closing.message_post(
                body=_("Clôture confirmée par %s<br/>"
                       "Solde théorique : %s %s<br/>"
                       "Solde réel : %s %s<br/>"
                       "Écart : %s %s") % (
                         self.env.user.name,
                         closing.balance_end_theoretical,
                         closing.currency_id.symbol,
                         closing.balance_end_real,
                         closing.currency_id.symbol,
                         closing.difference,
                         closing.currency_id.symbol
                     )
            )

        return True

    def action_validate(self):
        """Valider la clôture et créer l'ajustement si nécessaire"""
        for closing in self:
            if closing.state != 'confirmed':
                raise UserError(_("Seules les clôtures confirmées peuvent être validées."))

            # Créer une opération d'ajustement si écart
            if closing.difference != 0:
                # Trouver la catégorie d'ajustement
                category = self.env['treasury.operation.category'].search([
                    ('code', '=', 'AJUST')
                ], limit=1)

                if not category:
                    category = self.env['treasury.operation.category'].create({
                        'name': 'Ajustement',
                        'code': 'AJUST',
                        'operation_type': 'both',
                        'sequence': 99
                    })

                # Créer l'opération d'ajustement
                adjustment_vals = {
                    'cash_id': closing.cash_id.id,
                    'operation_type': 'in' if closing.difference > 0 else 'out',
                    'category_id': category.id,
                    'amount': abs(closing.difference),
                    'date': closing.period_end,
                    'description': _("Ajustement automatique suite à écart de clôture"),
                    'reference': closing.name,
                    'closing_id': closing.id,
                    'state': 'posted',
                }

                adjustment = self.env['treasury.cash.operation'].create(adjustment_vals)
                closing.adjustment_operation_id = adjustment

                adjustment_msg = _("Ajustement automatique créé : %s %s %s") % (
                    '+' if closing.difference > 0 else '-',
                    abs(closing.difference),
                    closing.currency_id.symbol
                )
                closing.message_post(body=adjustment_msg)

            # Marquer comme validé
            closing.write({
                'state': 'validated',
                'validated_by': self.env.user.id
            })

            # Mettre à jour les informations de la caisse
            closing.cash_id.write({
                'last_closing_date': closing.period_end,
                'last_closing_balance': closing.balance_end_real
            })

            # Message de validation
            closing.message_post(
                body=_("Clôture validée par %s<br/>"
                       "Solde final : %s %s<br/>"
                       "Écart : %s %s") % (
                         self.env.user.name,
                         closing.balance_end_real,
                         closing.currency_id.symbol,
                         closing.difference,
                         closing.currency_id.symbol
                     )
            )

            # Notification sur la caisse
            closing.cash_id.message_post(
                body=_("Clôture %s validée - Solde : %s %s") % (
                    closing.name,
                    closing.balance_end_real,
                    closing.currency_id.symbol
                )
            )

        return True

    def write(self, vals):
        """Override write pour recalculer les lignes si nécessaire"""
        res = super().write(vals)

        # Recharger les opérations si la date change
        if 'closing_date' in vals and self.state == 'draft':
            self.action_load_operations()

        # Recharger automatiquement à chaque modification si en brouillon
        if self.state == 'draft':
            self.with_context(skip_compute=True).action_load_operations()

        # Recalculer les lignes si nécessaire
        if any(field in vals for field in ['operation_ids', 'balance_start']):
            self._compute_closing_lines()

        return res

    # Ajouter un compute sur operation_ids pour le rechargement automatique
    @api.depends('cash_id', 'period_start', 'period_end')
    def _compute_auto_load_operations(self):
        """Charger automatiquement les opérations lors de la création"""
        for closing in self:
            if closing.state == 'draft' and not closing.operation_ids and closing.period_start and closing.period_end:
                closing.with_context(skip_compute=True).action_load_operations()

    def action_back_to_draft(self):
        """Remettre en brouillon avec vérifications"""
        for closing in self:
            if closing.state == 'draft':
                continue

            # Vérification 1 : Pas de clôture ultérieure qui dépend de celle-ci
            later_closings = self.search([
                ('cash_id', '=', closing.cash_id.id),
                ('state', '!=', 'draft'),
                '|',
                ('closing_date', '>', closing.closing_date),
                '&',
                ('closing_date', '=', closing.closing_date),
                ('closing_number', '>', closing.closing_number)
            ])

            if later_closings:
                raise UserError(_(
                    "Impossible de remettre en brouillon cette clôture car il existe des clôtures ultérieures validées.\n"
                    "Vous devez d'abord annuler les clôtures suivantes : %s"
                ) % ', '.join(later_closings.mapped('name')))

            # Vérification 2 : Si validée, vérifier l'opération d'ajustement
            if closing.state == 'validated' and closing.adjustment_operation_id:
                # Vérifier que l'ajustement peut être annulé
                if closing.adjustment_operation_id.state == 'posted':
                    # L'annuler
                    closing.adjustment_operation_id.state = 'cancel'

            # Vérification 3 : Les opérations ne doivent pas être dans d'autres clôtures
            operations_in_other_closings = closing.operation_ids.filtered(
                lambda o: o.closing_id != closing and o.closing_id
            )

            if operations_in_other_closings:
                raise UserError(_(
                    "Certaines opérations sont déjà dans d'autres clôtures.\n"
                    "Opérations concernées : %s"
                ) % ', '.join(operations_in_other_closings.mapped('name')))

            # Remettre en brouillon
            closing.write({
                'state': 'draft',
                'validated_by': False,
                'balance_end_real': False  # Réinitialiser le solde réel pour forcer une nouvelle saisie
            })

            # Si la caisse avait été mise à jour avec cette clôture
            if closing.cash_id.last_closing_id == closing:
                # Retrouver la clôture précédente
                previous_closing = self.search([
                    ('cash_id', '=', closing.cash_id.id),
                    ('state', '=', 'validated'),
                    ('id', '!=', closing.id),
                    '|',
                    ('closing_date', '<', closing.closing_date),
                    '&',
                    ('closing_date', '=', closing.closing_date),
                    ('closing_number', '<', closing.closing_number)
                ], order='closing_date desc, closing_number desc', limit=1)

                if previous_closing:
                    closing.cash_id.write({
                        'last_closing_date': previous_closing.period_end,
                        'last_closing_balance': previous_closing.balance_end_real
                    })
                else:
                    # Pas de clôture précédente
                    closing.cash_id.write({
                        'last_closing_date': False,
                        'last_closing_balance': 0.0
                    })

            # Message dans le chatter
            closing.message_post(
                body=_("Clôture remise en brouillon par %s") % self.env.user.name
            )

        return True


    def action_print_report(self):
        """Imprimer le rapport de clôture"""
        self.ensure_one()

        # Vérifier que la clôture n'est pas en brouillon
        if self.state == 'draft':
            raise UserError(_(
                "Impossible d'imprimer une clôture en brouillon.\n"
                "Veuillez d'abord confirmer la clôture."
            ))

        # Retourner l'action d'impression
        return self.env.ref('adi_treasury.action_report_treasury_cash_closing').report_action(self)

    manual_operation_count = fields.Integer(
        string='Opérations manuelles',
        compute='_compute_operation_counts'
    )

    automatic_operation_count = fields.Integer(
        string='Opérations automatiques',
        compute='_compute_operation_counts'
    )

    draft_manual_operation_count = fields.Integer(
        string='Opérations manuelles en brouillon',
        compute='_compute_operation_counts'
    )

    @api.depends('operation_ids', 'operation_ids.is_manual', 'operation_ids.payment_id', 'operation_ids.state')
    def _compute_operation_counts(self):
        """Calculer le nombre d'opérations manuelles et automatiques"""
        for closing in self:
            operations = closing.operation_ids

            # Opérations manuelles
            manual_ops = operations.filtered(lambda o: o.is_manual)
            closing.manual_operation_count = len(manual_ops)

            # Opérations manuelles en brouillon
            closing.draft_manual_operation_count = len(manual_ops.filtered(lambda o: o.state == 'draft'))

            # Opérations automatiques (liées aux paiements)
            closing.automatic_operation_count = len(operations.filtered(lambda o: o.payment_id))

    def action_view_manual_operations(self):
        """Afficher les opérations manuelles de cette clôture"""
        self.ensure_one()

        return {
            'name': _('Opérations manuelles - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'treasury.cash.operation',
            'view_mode': 'tree,form',
            'domain': [
                ('closing_id', '=', self.id),
                ('is_manual', '=', True)
            ],
            'context': {
                'default_closing_id': self.id,
                'default_cash_id': self.cash_id.id,
                'default_is_manual': True,
                'search_default_draft': 1,  # Filtrer par défaut sur les brouillons
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucune opération manuelle trouvée
                </p>
                <p>
                    Les opérations manuelles sont les entrées/sorties de caisse créées directement,
                    sans lien avec un paiement comptable.
                </p>
            """
        }

    def action_view_automatic_operations(self):
        """Afficher les opérations automatiques (paiements) de cette clôture"""
        self.ensure_one()

        # Récupérer les IDs des paiements liés
        payment_ids = self.operation_ids.filtered(lambda o: o.payment_id).mapped('payment_id.id')

        return {
            'name': _('Paiements automatiques - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payment_ids)],
            'context': {
                'create': False,  # Pas de création depuis cette vue
                'edit': False,  # Lecture seule
                'delete': False,  # Pas de suppression
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucun paiement automatique trouvé
                </p>
                <p>
                    Les paiements automatiques sont créés depuis les factures clients/fournisseurs
                    et génèrent automatiquement des opérations de caisse.
                </p>
            """
        }




# Modèle pour les lignes de clôture (reste identique)
class TreasuryCashClosingLine(models.Model):
    _name = 'treasury.cash.closing.line'
    _description = 'Ligne de clôture de caisse'
    _order = 'sequence, date'

    closing_id = fields.Many2one(
        'treasury.cash.closing',
        string='Clôture',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10
    )

    date = fields.Datetime(
        string='Date/Heure'
    )

    operation_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Tiers'
    )

    category_id = fields.Many2one(
        'treasury.operation.category',
        string='Catégorie'
    )

    operation_type = fields.Selection([
        ('initial', 'Solde initial'),
        ('in', 'Entrée'),
        ('out', 'Sortie')
    ], string='Type')

    description = fields.Text(
        string='Description'
    )

    reference = fields.Char(
        string='Référence'
    )

    amount_in = fields.Monetary(
        string='Entrée',
        currency_field='currency_id'
    )

    amount_out = fields.Monetary(
        string='Sortie',
        currency_field='currency_id'
    )

    cumulative_balance = fields.Monetary(
        string='Solde cumulé',
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='closing_id.currency_id',
        store=True
    )


