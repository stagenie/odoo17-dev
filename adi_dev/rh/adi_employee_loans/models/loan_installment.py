# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LoanInstallment(models.Model):
    """Échéances de remboursement des prêts"""
    _name = 'loan.installment'
    _description = 'Échéance de prêt'
    _order = 'loan_id, sequence'
    _rec_name = 'display_name'

    # Lien avec le prêt
    loan_id = fields.Many2one(
        'employee.loan',
        string='Prêt',
        required=True,
        ondelete='cascade'
    )

    # Informations employé (liées)
    employee_id = fields.Many2one(
        related='loan_id.employee_id',
        string='Employé',
        store=True
    )

    employee_name = fields.Char(
        related='loan_id.employee_name',
        string='Nom employé',
        store=True
    )

    # Détails de l'échéance
    sequence = fields.Integer(
        string='N°',
        required=True
    )

    date = fields.Date(
        string='Date d\'échéance',
        required=True
    )

    amount = fields.Monetary(
        string='Montant',
        required=True
    )

    currency_id = fields.Many2one(
        related='loan_id.currency_id',
        string='Devise'
    )

    # Paiement
    amount_paid = fields.Monetary(
        string='Montant payé',
        default=0.0
    )

    payment_date = fields.Date(
        string='Date de paiement'
    )

    # État
    state = fields.Selection([
        ('pending', 'En attente'),
        ('paid', 'Payée'),
        ('partial', 'Partielle')
    ], string='État', default='pending')

    # Traitement paie
    is_processed = fields.Boolean(
        string='Traitée en paie',
        default=False,
        help="Indique si cette échéance a été prélevée sur une paie"
    )

    payroll_ref = fields.Char(
        string='Référence paie',
        help="Référence du bulletin où cette échéance a été prélevée"
    )

    # Nom affiché
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True
    )

    company_id = fields.Many2one(
        related='loan_id.company_id',
        store=True
    )

    @api.depends('loan_id.name', 'sequence')
    def _compute_display_name(self):
        """Calcule le nom affiché de l'échéance"""
        for record in self:
            record.display_name = f"{record.loan_id.name} - Échéance {record.sequence}"

    def action_pay(self):
        """Marque l'échéance comme payée"""
        for record in self:
            if record.state == 'paid':
                raise ValidationError("Cette échéance est déjà payée!")

            record.write({
                'state': 'paid',
                'amount_paid': record.amount,
                'payment_date': fields.Date.today()
            })

            # Vérifier si le prêt est complètement remboursé
            record.loan_id.check_loan_completion()

    def action_pay_partial(self, amount):
        """Enregistre un paiement partiel"""
        self.ensure_one()
        if amount <= 0:
            raise ValidationError("Le montant doit être positif!")
        if amount > self.amount:
            raise ValidationError("Le montant ne peut pas dépasser le montant de l'échéance!")

        self.write({
            'state': 'partial' if amount < self.amount else 'paid',
            'amount_paid': amount,
            'payment_date': fields.Date.today()
        })

        if self.state == 'paid':
            self.loan_id.check_loan_completion()

    def mark_as_processed(self, payroll_ref):
        """Marque l'échéance comme traitée en paie"""
        for record in self:
            record.write({
                'is_processed': True,
                'payroll_ref': payroll_ref,
                'state': 'paid',
                'amount_paid': record.amount,
                'payment_date': fields.Date.today()
            })
            record.loan_id.check_loan_completion()

    # Méthode pour récupérer les échéances à prélever
    @api.model
    def get_pending_installments(self, employee_id, date_to):
        """Retourne les échéances en attente pour un employé jusqu'à une date"""
        domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'pending'),
            ('date', '<=', date_to),
            ('loan_id.state', '=', 'running')
        ]
        return self.search(domain)
