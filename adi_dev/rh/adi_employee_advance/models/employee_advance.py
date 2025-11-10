# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class EmployeeAdvance(models.Model):
    """Gestion des avances sur salaire des employés"""
    _name = 'employee.advance'
    _description = 'Avance Employé'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    def _get_advance_product(self):
        """Retourne ou crée le produit pour les avances"""
        # Chercher le produit "Avance sur salaire"
        product = self.env['product.product'].search([
            ('default_code', '=', 'ADVANCE_SALARY')
        ], limit=1)

        if not product:
            # Créer le produit s'il n'existe pas
            product_vals = {
                'name': 'Avance sur salaire',
                'default_code': 'ADVANCE_SALARY',
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
                'list_price': 0.0,
                'standard_price': 0.0,
                'taxes_id': [(5, 0, 0)],  # Pas de taxes client
                'supplier_taxes_id': [(5, 0, 0)],  # Pas de taxes fournisseur
            }

            # Chercher ou créer la catégorie
            category = self.env['product.category'].search([
                ('name', '=', 'Ressources Humaines')
            ], limit=1)

            if not category:
                category = self.env['product.category'].create({
                    'name': 'Ressources Humaines',
                })

            product_vals['categ_id'] = category.id

            # Chercher le compte comptable approprié
            account = self._get_advance_account()
            if account:
                product_vals['property_account_expense_id'] = account.id

            product = self.env['product.product'].create(product_vals)

        return product

    def _get_advance_category(self):
        """Retourne ou crée la catégorie de produit pour les avances"""
        # Chercher la catégorie "Ressources Humaines"
        category = self.env['product.category'].search([
            ('name', '=', 'Ressources Humaines')
        ], limit=1)

        if not category:
            # Créer la catégorie si elle n'existe pas
            category = self.env['product.category'].create({
                'name': 'Ressources Humaines',
                'property_cost_method': 'standard',
                'property_valuation': 'manual_periodic'
            })

        return category

    def action_validate(self):
        """Valide l'avance et crée la facture fournisseur"""
        self.ensure_one()  # Important pour retourner une action

        if self.state != 'draft':
            raise ValidationError("Seules les avances en brouillon peuvent être validées!")

        # Créer ou récupérer l'employé comme fournisseur
        employee_partner = self.employee_id.user_id.partner_id if self.employee_id.user_id else False

        if not employee_partner:
            # Chercher si un partenaire existe déjà pour cet employé
            employee_partner = self.env['res.partner'].search([
                ('name', '=', self.employee_name),
                ('employee', '=', True)
            ], limit=1)

            if not employee_partner:
                # Créer le partenaire pour l'employé
                employee_partner = self.env['res.partner'].create({
                    'name': self.employee_name,
                    'supplier_rank': 1,
                    'employee': True,
                    'is_company': False,
                })
        else:
            # S'assurer que le partenaire est marqué comme fournisseur
            if employee_partner.supplier_rank < 1:
                employee_partner.supplier_rank = 1

        # Récupérer ou créer le produit avance
        advance_product = self._get_advance_product()

        # Créer la facture fournisseur avec l'employé comme fournisseur
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': employee_partner.id,
            'invoice_date': self.date,
            'date': self.date,
            'ref': f"Avance - {self.name}",
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': advance_product.id,
                'name': f"Avance sur salaire\n{self.observation or ''}",
                'quantity': 1.0,
                'price_unit': self.amount,
                'account_id': advance_product.property_account_expense_id.id or self._get_advance_account().id,
                'tax_ids': [(5, 0, 0)],  # Pas de taxes
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # Lier la facture à l'avance et changer l'état
        self.write({
            'state': 'validated',
            'invoice_id': invoice.id
        })

        # Message dans le chatter
        self.message_post(
            body=f"Avance validée. Facture fournisseur {invoice.name} créée pour {self.employee_name}."
        )

        # Retourner l'action pour afficher la facture
        return {
            'name': 'Facture Fournisseur',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'context': {
                'default_move_type': 'in_invoice',
            }
        }

    def _get_advance_account(self):
        """Retourne le compte comptable pour les avances"""
        # Chercher un compte spécifique pour les avances
        account = self.env['account.account'].search([
            '|',
            ('code', '=like', '425%'),  # Compte personnel - avances et acomptes
            ('code', '=like', '421%'),  # Personnel - rémunérations dues
            ('company_id', '=', self.company_id.id),
            ('deprecated', '=', False)
        ], limit=1)

        if not account:
            # Chercher un compte de charges de personnel
            account = self.env['account.account'].search([
                ('code', '=like', '6%'),  # Charges
                ('company_id', '=', self.company_id.id),
                ('deprecated', '=', False),
                ('user_type_id.type', '=', 'other')
            ], limit=1)

        if not account:
            raise UserError(
                "Aucun compte comptable trouvé pour les avances!\n"
                "Veuillez créer un compte 425xxx (Personnel - avances et acomptes) "
                "ou vérifier votre plan comptable."
            )

        return account

    # Informations de base

        # Nouveaux champs pour le suivi du paiement
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='État de paiement',
        store=True
    )

    is_invoice_paid = fields.Boolean(
        string='Facture payée',
        compute='_compute_is_invoice_paid',
        store=True
    )

    @api.depends('invoice_id', 'invoice_id.payment_state', 'invoice_state')
    def _compute_is_invoice_paid(self):
        """Calcule si la facture est payée et met à jour l'état de l'avance"""
        for record in self:
            # Vérifier si la facture est payée
            if record.invoice_id and record.invoice_id.payment_state in ('paid', 'in_payment'):
                record.is_invoice_paid = True
                # Mettre à jour automatiquement l'état de l'avance si elle est validée
                if record.state == 'validated':
                    record.state = 'paid'
            else:
                record.is_invoice_paid = False

    def action_view_payments(self):
        """Ouvre la vue des paiements de la facture"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("Aucune facture liée à cette avance!")

        # Si la facture n'est pas validée, l'ouvrir directement
        if self.invoice_id.state == 'draft':
            return self.action_view_invoice()

        # Chercher les paiements liés à la facture
        payments = self.env['account.payment'].search([
            ('reconciled_invoice_ids', 'in', self.invoice_id.id)
        ])

        if not payments:
            # S'il n'y a pas de paiements, proposer d'en créer un
            return self.invoice_id.action_register_payment()

        # S'il y a des paiements, les afficher
        action = {
            'name': 'Paiements',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }

        if len(payments) == 1:
            # Un seul paiement : ouvrir le formulaire
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            # Plusieurs paiements : ouvrir la liste
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })

        return action

    """ """
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
        states={'validated': [('readonly', True)], 'paid': [('readonly', True)]}
    )

    def action_print_receipt(self):
        """Imprime le reçu d'avance"""
        self.ensure_one()
        return self.env.ref('adi_employee_advance.action_report_advance_receipt').report_action(self)

    # Champs liés pour affichage
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

    # Informations de l'avance
    date = fields.Date(
        string='Date de l\'avance',
        required=True,
        default=fields.Date.today,
        tracking=True,
        states={'validated': [('readonly', True)], 'paid': [('readonly', True)]}
    )

    amount = fields.Monetary(
        string='Montant de l\'avance',
        required=True,
        tracking=True,
        states={'validated': [('readonly', True)], 'paid': [('readonly', True)]}
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    observation = fields.Text(
        string='Observations',
        states={'validated': [('readonly', True)], 'paid': [('readonly', True)]}
    )

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

    # État de l'avance
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validée'),
        ('paid', 'Payée'),
        ('processed', 'Traitée en paie'),
        ('cancelled', 'Annulée')
    ], string='État', default='draft', tracking=True)

    # Traitement paie
    is_processed = fields.Boolean(
        string='Traitée en paie',
        default=False,
        copy=False,
        help="Indique si cette avance a été déduite d'une paie"
    )

    # On garde une référence générique pour le futur module de paie
    payroll_ref = fields.Char(
        string='Référence paie',
        readonly=True,
        copy=False,
        help="Référence du bulletin de paie où cette avance a été déduite"
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
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.advance') or 'ADV/001'
        return super(EmployeeAdvance, self).create(vals)


    def action_cancel(self):
        """Annule l'avance"""
        for record in self:
            if record.state == 'processed':
                raise ValidationError("Impossible d'annuler une avance déjà traitée en paie!")

            if record.invoice_id and record.invoice_id.state == 'posted':
                raise ValidationError("Impossible d'annuler : la facture est déjà comptabilisée!")

            # Annuler la facture si elle existe
            if record.invoice_id:
                record.invoice_id.button_cancel()

            record.state = 'cancelled'

    def action_set_to_paid(self):
        """Marque l'avance comme payée"""
        for record in self:
            if record.state != 'validated':
                raise ValidationError("Seules les avances validées peuvent être marquées comme payées!")
            record.state = 'paid'

    def action_view_invoice(self):
        """Ouvre la facture fournisseur liée"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("Aucune facture liée à cette avance!")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture fournisseur',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


    @api.constrains('amount')
    def _check_amount(self):
        """Vérifie que le montant est positif"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Le montant de l'avance doit être positif!")

    def unlink(self):
        """Empêche la suppression des avances validées"""
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise ValidationError("Seules les avances en brouillon ou annulées peuvent être supprimées!")
        return super(EmployeeAdvance, self).unlink()

    # Méthode pour récupérer les avances non traitées d'un employé
    @api.model
    def get_unprocessed_advances(self, employee_id, date_from, date_to):
        """Retourne les avances non traitées pour un employé sur une période"""
        domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'paid'),
            ('is_processed', '=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]
        return self.search(domain)

    def mark_as_processed(self, payroll_ref):
        """Marque les avances comme traitées en paie"""
        for record in self:
            record.write({
                'is_processed': True,
                'state': 'processed',
                'payroll_ref': payroll_ref
            })
