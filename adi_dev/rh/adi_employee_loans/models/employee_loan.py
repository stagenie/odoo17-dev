# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import math


class EmployeeLoan(models.Model):
    """Gestion des prêts accordés aux employés"""
    _name = 'employee.loan'
    _description = 'Prêt Employé'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # Ajouter ces champs dans la classe EmployeeLoan
    # Lien avec la comptabilité
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture fournisseur',
        readonly=True,
        copy=False
    )

    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='État de la facture',
        store=True
    )

    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='État de paiement',
        store=True
    )

    # Informations de base
    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='Nouveau',
        copy=False
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        domain="[('contract_ids.state', '=', 'open')]",
        required=True,
        tracking=True,
    )

    # Champs liés
    employee_name = fields.Char(
        related='employee_id.name',
        string='Nom et Prénom',
        store=True
    )

    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Fonction',
        store=True
    )

    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Département',
        store=True
    )

    # Informations du prêt
    date = fields.Date(
        string='Date de demande',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    loan_amount = fields.Monetary(
        string='Montant du prêt',
        required=True,
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    purpose = fields.Text(
        string='Objet du prêt',
        required=True,

    )

    # Modalités de remboursement
    installment_count = fields.Integer(
        string='Nombre de mensualités',
        required=True,
        default=12,

    )

    installment_amount = fields.Monetary(
        string='Montant par mensualité',
        compute='_compute_installment_amount',
        store=True
    )

    start_date = fields.Date(
        string='Date de début',
        required=True,
        default=lambda self: fields.Date.today() + relativedelta(months=1, day=1),
        help="Date de la première échéance",
    )

    payment_frequency = fields.Selection([
        ('monthly', 'Mensuel'),
        ('weekly', 'Hebdomadaire'),
        ('biweekly', 'Bimensuel')
    ], string='Fréquence de paiement', default='monthly', required=True)

    # État et suivi
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('approved', 'Approuvé'),
        ('running', 'En cours'),
        ('paid', 'Remboursé'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft', tracking=True)

    # Échéancier
    installment_ids = fields.One2many(
        'loan.installment',
        'loan_id',
        string='Échéancier'
    )

    # Montants calculés
    total_paid = fields.Monetary(
        string='Total remboursé',
        compute='_compute_amounts',
        store=True
    )

    remaining_amount = fields.Monetary(
        string='Montant restant',
        compute='_compute_amounts',
        store=True
    )

    next_payment_date = fields.Date(
        string='Prochaine échéance',
        compute='_compute_next_payment',
        store=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model
    def create(self, vals):
        """Génère automatiquement la référence"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.loan') or 'LOAN/001'
        return super(EmployeeLoan, self).create(vals)

    @api.depends('loan_amount', 'installment_count')
    def _compute_installment_amount(self):
        """Calcule le montant de chaque mensualité"""
        for record in self:
            if record.installment_count > 0:
                record.installment_amount = record.loan_amount / record.installment_count
            else:
                record.installment_amount = 0

    @api.depends('installment_ids.amount_paid', 'installment_ids.state')
    def _compute_amounts(self):
        """Calcule les montants payés et restants"""
        for record in self:
            paid_installments = record.installment_ids.filtered(lambda i: i.state == 'paid')
            record.total_paid = sum(paid_installments.mapped('amount_paid'))
            record.remaining_amount = record.loan_amount - record.total_paid

    @api.depends('installment_ids.date', 'installment_ids.state')
    def _compute_next_payment(self):
        """Calcule la date de la prochaine échéance"""
        for record in self:
            pending_installments = record.installment_ids.filtered(
                lambda i: i.state == 'pending'
            ).sorted('date')
            if pending_installments:
                record.next_payment_date = pending_installments[0].date
            else:
                record.next_payment_date = False

    def action_submit(self):
        """Soumet la demande de prêt"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError("Seules les demandes en brouillon peuvent être soumises!")
        self.state = 'submitted'

    # Modifier la méthode action_approve pour créer la facture
    def action_approve(self):
        """Approuve le prêt, génère l'échéancier et crée la facture"""
        self.ensure_one()
        if self.state != 'submitted':
            raise ValidationError("Seules les demandes soumises peuvent être approuvées!")

        # Générer l'échéancier
        self._generate_installments()

        # Créer la facture fournisseur
        self._create_loan_invoice()

        self.state = 'approved'

        # Message dans le chatter
        self.message_post(
            body=f"Prêt approuvé. {self.installment_count} échéances créées. Facture {self.invoice_id.name} générée."
        )

    # Ajouter cette nouvelle méthode
    def _create_loan_invoice(self):
        """Crée une facture fournisseur pour le prêt"""
        self.ensure_one()

        # Créer ou récupérer l'employé comme fournisseur
        employee_partner = self.employee_id.user_id.partner_id if self.employee_id.user_id else False

        if not employee_partner:
            employee_partner = self.env['res.partner'].search([
                ('name', '=', self.employee_name),
                ('employee', '=', True)
            ], limit=1)

            if not employee_partner:
                employee_partner = self.env['res.partner'].create({
                    'name': self.employee_name,
                    'supplier_rank': 1,
                    'employee': True,
                    'is_company': False,
                })
        else:
            if employee_partner.supplier_rank < 1:
                employee_partner.supplier_rank = 1

        # Créer ou récupérer le produit prêt
        loan_product = self._get_loan_product()

        # Créer la facture
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': employee_partner.id,
            'invoice_date': self.date,
            'date': self.date,
            'ref': f"Prêt {self.name} - {self.purpose}",
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': loan_product.id,
                'name': f"Prêt employé - {self.name}\n{self.purpose}\nMontant: {self.loan_amount:,.2f}\nRemboursement en {self.installment_count} mensualités",
                'quantity': 1.0,
                'price_unit': self.loan_amount,
                'tax_ids': [(5, 0, 0)],
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

    def _get_loan_product(self):
        """Retourne ou crée le produit pour les prêts"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'EMPLOYEE_LOAN')
        ], limit=1)

        if not product:
            product = self.env['product.product'].create({
                'name': 'Prêt Employé',
                'default_code': 'EMPLOYEE_LOAN',
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
                'list_price': 0.0,
                'standard_price': 0.0,
                'taxes_id': [(5, 0, 0)],
                'supplier_taxes_id': [(5, 0, 0)],
            })

        return product

    def action_view_invoice(self):
        """Ouvre la facture fournisseur liée"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("Aucune facture liée à ce prêt!")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture fournisseur',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_loan_agreement(self):
        """Imprime le bon de prêt"""
        self.ensure_one()
        return self.env.ref('adi_employee_loans.action_report_loan_agreement').report_action(self)

    def action_start(self):
        """Démarre le remboursement du prêt"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError("Seul un prêt approuvé peut être démarré!")
        self.state = 'running'

    def action_cancel(self):
        """Annule le prêt"""
        self.ensure_one()
        if self.state in ('running', 'paid'):
            raise ValidationError("Impossible d'annuler un prêt en cours ou remboursé!")

        # Supprimer les échéances non payées
        self.installment_ids.filtered(lambda i: i.state != 'paid').unlink()

        self.state = 'cancelled'

    def _generate_installments(self):
        """Génère l'échéancier de remboursement"""
        self.ensure_one()

        # Supprimer les échéances existantes non payées
        self.installment_ids.filtered(lambda i: i.state != 'paid').unlink()

        # Calculer les dates et montants
        installment_date = self.start_date
        remaining_amount = self.loan_amount

        for i in range(self.installment_count):
            # Calculer le montant de l'échéance
            if i == self.installment_count - 1:
                # Dernière échéance : ajuster pour le solde exact
                amount = remaining_amount
            else:
                amount = self.installment_amount

            # Créer l'échéance
            self.env['loan.installment'].create({
                'loan_id': self.id,
                'sequence': i + 1,
                'date': installment_date,
                'amount': amount,
                'state': 'pending'
            })

            # Prochaine date selon la fréquence
            if self.payment_frequency == 'monthly':
                installment_date = installment_date + relativedelta(months=1)
            elif self.payment_frequency == 'weekly':
                installment_date = installment_date + relativedelta(weeks=1)
            elif self.payment_frequency == 'biweekly':
                installment_date = installment_date + relativedelta(weeks=2)

            remaining_amount -= amount

    def check_loan_completion(self):
        """Vérifie si le prêt est entièrement remboursé"""
        self.ensure_one()
        if self.state == 'running' and all(i.state == 'paid' for i in self.installment_ids):
            self.state = 'paid'
            self.message_post(body="Prêt entièrement remboursé!")

    @api.constrains('loan_amount', 'installment_count')
    def _check_loan_values(self):
        """Vérifie la validité des valeurs du prêt"""
        for record in self:
            if record.loan_amount <= 0:
                raise ValidationError("Le montant du prêt doit être positif!")
            if record.installment_count <= 0:
                raise ValidationError("Le nombre de mensualités doit être positif!")
