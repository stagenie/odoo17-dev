# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PayrollBatch(models.Model):
    """Lot de bulletins de paie"""
    _name = 'payroll.batch'
    _description = 'Lot de paie'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'


    """"""
    # Ajouter ce champ dans la classe PayrollBatch
    notes = fields.Text(
        string='Notes',
        help="Notes internes sur ce lot de paie"
    )

    # Ajouter selection_type avec valeur par défaut
    selection_type = fields.Selection([
        ('all', 'Tous les employés'),
        ('department', 'Par département')
    ], string='Type de sélection', default='department')
    """" """

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='Nouveau'
    )

    period_id = fields.Many2one(
        'payroll.period',
        string='Période',
        required=True,
        domain=[('state', '=', 'open')]
    )

    date_start = fields.Date(
        related='period_id.date_start',
        string='Date début',
        store=True
    )

    date_end = fields.Date(
        related='period_id.date_end',
        string='Date fin',
        store=True
    )

    slip_ids = fields.One2many(
        'payroll.slip',
        'batch_id',
        string='Bulletins de paie'
    )

    slip_count = fields.Integer(
        string='Nombre de bulletins',
        compute='_compute_counts'
    )

    # Sélection des employés
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employés',
        domain="[('contract_ids.state', '=', 'open')]",
        help="Laisser vide pour tous les employés actifs"
    )

    department_ids = fields.Many2many(
        'hr.department',
        string='Départements',
        help="Filtrer par département"
    )

    # Montants totaux
    total_gross = fields.Monetary(
        string='Total brut',
        compute='_compute_totals',
        store=True
    )

    total_net = fields.Monetary(
        string='Total net',
        compute='_compute_totals',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('generate', 'Généré'),
        ('confirm', 'Confirmé'),
        ('done', 'Validé'),
        ('paid', 'Payé')
    ], string='État', default='draft', tracking=True)

    # Comptabilisation
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture groupée',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model
    def create(self, vals):
        """Génère la référence du lot"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('payroll.batch') or 'LOT/001'
        return super(PayrollBatch, self).create(vals)

    @api.depends('slip_ids')
    def _compute_counts(self):
        """Calcule le nombre de bulletins"""
        for record in self:
            record.slip_count = len(record.slip_ids)

    @api.depends('slip_ids.total_net', 'slip_ids.total_gross')
    def _compute_totals(self):
        """Calcule les totaux du lot"""
        for record in self:
            record.total_gross = sum(record.slip_ids.mapped('total_gross'))
            record.total_net = sum(record.slip_ids.mapped('total_net'))

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        """Ajoute automatiquement les employés des départements sélectionnés"""
        if self.department_ids:
            # Récupérer les employés des départements avec contrat actif
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids),
                ('contract_ids.state', '=', 'open')
            ])

            # Ajouter les nouveaux employés sans supprimer les existants
            if employees:
                self.employee_ids = [(4, emp.id) for emp in employees]

    def action_generate_slips(self):
        """Génère les bulletins de paie"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError("Les bulletins ne peuvent être générés qu'en brouillon!")

        # Déterminer les employés
        if self.employee_ids:
            # Vérifier que tous les employés sélectionnés ont un contrat actif
            employees_without_contract = self.employee_ids.filtered(
                lambda e: not e.contract_ids.filtered(lambda c: c.state == 'open')
            )
            if employees_without_contract:
                raise UserError(
                    "Les employés suivants n'ont pas de contrat actif:\n" +
                    "\n".join(employees_without_contract.mapped('name'))
                )
            employees = self.employee_ids
        elif self.department_ids:
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids),
                ('contract_ids.state', '=', 'open')
            ])
        else:
            employees = self.env['hr.employee'].search([
                ('contract_ids.state', '=', 'open')
            ])

        if not employees:
            raise UserError("Aucun employé trouvé avec un contrat actif!")

        # Supprimer les bulletins existants en brouillon
        self.slip_ids.filtered(lambda s: s.state == 'draft').unlink()

        # Créer un bulletin pour chaque employé
        created_slips = self.env['payroll.slip']
        for employee in employees:
            # Vérifier à nouveau le contrat au niveau individuel
            contract = employee.contract_ids.filtered(
                lambda c: c.state == 'open' and
                          c.date_start <= self.date_end and
                          (not c.date_end or c.date_end >= self.date_start)
            )

            if not contract:
                self.message_post(
                    body=f"⚠️ Employé {employee.name} ignoré : pas de contrat actif pour la période"
                )
                continue

            slip = self.env['payroll.slip'].create({
                'employee_id': employee.id,
                'batch_id': self.id,
                'period_id': self.period_id.id,
            })
            created_slips |= slip

        if not created_slips:
            raise UserError("Aucun bulletin n'a pu être créé!")

        self.state = 'generate'

        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': 'Bulletins générés',
        #         'message': f'{len(created_slips)} bulletins créés',
        #         'type': 'success',
        #         'sticky': False,
        #     }
        # }

    def action_compute_sheet(self):
        """Calcule tous les bulletins du lot"""
        self.ensure_one()
        if self.state not in ('generate', 'confirm'):
            raise ValidationError("Le lot doit être généré pour calculer les bulletins!")

        for slip in self.slip_ids:
            if slip.state == 'draft':
                slip.action_compute_sheet()

    def action_confirm(self):
        """Confirme tous les bulletins"""
        self.ensure_one()
        if self.state != 'generate':
            raise ValidationError("Le lot doit être généré avant confirmation!")

        # Vérifier l'état des bulletins
        draft_slips = self.slip_ids.filtered(lambda s: s.state == 'draft')
        if draft_slips:
            raise ValidationError(
                f"{len(draft_slips)} bulletin(s) ne sont pas calculés!\n"
                "Utilisez le bouton 'Calculer tout' ou calculez-les individuellement."
            )

        # Confirmer uniquement les bulletins calculés
        computed_slips = self.slip_ids.filtered(lambda s: s.state == 'compute')
        if computed_slips:
            computed_slips.action_confirm()

        # Si tous les bulletins sont déjà confirmés ou validés, passer directement
        if all(slip.state in ('confirm', 'done') for slip in self.slip_ids):
            self.state = 'confirm'
        else:
            raise ValidationError("Impossible de confirmer le lot!")

    # Ajouter ces champs après invoice_id
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='État de Facture',
        store=True
    )
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

    @api.depends('invoice_id', 'invoice_id.payment_state')
    def _compute_is_invoice_paid(self):
        """Détermine si la facture est payée"""
        for record in self:
            record.is_invoice_paid = bool(
                record.invoice_id and
                record.invoice_id.payment_state in ('paid', 'in_payment')
            )

    def action_done(self):
        """Valide le lot et comptabilise"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError("Le lot doit être confirmé avant validation!")

        # Valider uniquement les bulletins confirmés
        confirmed_slips = self.slip_ids.filtered(lambda s: s.state == 'confirm')
        if confirmed_slips:
            confirmed_slips.action_done()

        # Vérifier que tous les bulletins sont maintenant validés
        if not all(slip.state == 'done' for slip in self.slip_ids):
            invalid_slips = self.slip_ids.filtered(lambda s: s.state != 'done')
            raise ValidationError(
                f"{len(invalid_slips)} bulletin(s) ne sont pas validés!\n"
                f"États: {', '.join(invalid_slips.mapped('state'))}"
            )

        # Créer la facture groupée
        self._create_grouped_invoice()

        self.state = 'done'

        # Message de confirmation
        self.message_post(
            body=f"""
            <b>Lot validé avec succès!</b><br/>
            - Nombre de bulletins: {self.slip_count}<br/>
            - Total net: {self.total_net:,.2f}<br/>
            - Facture créée: {self.invoice_id.name if self.invoice_id else 'N/A'}
            """
        )

        # Ouvrir automatiquement la facture créée
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Facture de paie',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def _create_grouped_invoice(self):
        """Crée une facture fournisseur groupée pour tout le lot"""
        self.ensure_one()

        # Fournisseur "Paie Employés"
        payroll_vendor = self.env['res.partner'].search([
            ('name', '=', 'PAIE EMPLOYES')
        ], limit=1)

        if not payroll_vendor:
            payroll_vendor = self.env['res.partner'].create({
                'name': 'PAIE EMPLOYES',
                'supplier_rank': 1,
                'is_company': True,
            })

        # Produit "Salaire"
        salary_product = self.env['product.product'].search([
            ('default_code', '=', 'SALARY')
        ], limit=1)

        if not salary_product:
            salary_product = self.env['product.product'].create({
                'name': 'Salaire',
                'default_code': 'SALARY',
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
            })

        # Créer la facture
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': payroll_vendor.id,
            'invoice_date': fields.Date.today(),
            'ref': f"Paie {self.name} - {self.period_id.name}",
            'invoice_line_ids': [(0, 0, {
                'product_id': salary_product.id,
                'name': f"Salaires période {self.period_id.name}\nNombre d'employés: {self.slip_count}",
                'quantity': 1,
                'price_unit': self.total_net,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

    def action_view_slips(self):
        """Affiche les bulletins du lot"""
        self.ensure_one()
        return {
            'name': 'Bulletins de paie',
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.slip',
            'view_mode': 'tree,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'default_batch_id': self.id}
        }

    def action_print_batch_report(self):
        """Imprime le rapport du lot"""
        self.ensure_one()
        return self.env.ref('adi_simple_payroll.action_report_payroll_batch').report_action(self)

    # Ajouter cette méthode dans la classe PayrollBatch
    def action_view_invoice(self):
        """Affiche la facture groupée du lot"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("Aucune facture liée à ce lot!")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture de paie',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

