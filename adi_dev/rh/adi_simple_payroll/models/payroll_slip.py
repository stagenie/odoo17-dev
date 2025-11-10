# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PayrollSlip(models.Model):
    """Bulletin de paie individuel"""
    _name = 'payroll.slip'
    _description = 'Bulletin de paie'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'number'

    # Ajouter ce champ
    notes = fields.Text(
        string='Notes',
        help="Notes ou commentaires sur ce bulletin"
    )

    number = fields.Char(
        string='Numéro',
        required=True,
        readonly=True,
        default='Nouveau'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        readonly=True,
    )

    # Informations employé
    employee_name = fields.Char(
        related='employee_id.name',
        string='Nom et Prénom',
        store=True
    )

    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Poste',
        store=True
    )

    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Département',
        store=True
    )

    marital = fields.Selection(
        related='employee_id.marital',
        string='Situation familiale',
        store=True
    )

    # Contrat
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contrat',
        compute='_compute_contract',
        store=True
    )

    wage = fields.Monetary(
        related='contract_id.wage',
        string='Salaire de base',
        store=True
    )

    # Période et lot
    batch_id = fields.Many2one(
        'payroll.batch',
        string='Lot de paie',
        required=True,
        ondelete='cascade'
    )

    period_id = fields.Many2one(
        'payroll.period',
        string='Période',
        required=True
    )

    date_from = fields.Date(
        related='period_id.date_start',
        string='Date début',
        store=True
    )

    date_to = fields.Date(
        related='period_id.date_end',
        string='Date fin',
        store=True
    )

    @api.constrains('employee_id')
    def _check_employee_contract(self):
        """Vérifie que l'employé a un contrat actif"""
        for record in self:
            if record.employee_id and not record.contract_id:
                raise ValidationError(
                    f"L'employé {record.employee_name} n'a pas de contrat actif!"
                )

    # Lignes de paie
    line_ids = fields.One2many(
        'payroll.line',
        'slip_id',
        string='Détails du bulletin'
    )

    # Calculs
    worked_days = fields.Integer(
        string='Jours travaillés',
        compute='_compute_worked_days',
        store=True
    )

    daily_wage = fields.Monetary(
        string='Taux journalier',
        compute='_compute_daily_wage',
        store=True
    )

    # Totaux
    total_earnings = fields.Monetary(
        string='Total gains',
        compute='_compute_totals',
        store=True
    )

    total_deductions = fields.Monetary(
        string='Total retenues',
        compute='_compute_totals',
        store=True
    )

    total_gross = fields.Monetary(
        string='Salaire brut',
        compute='_compute_totals',
        store=True
    )

    total_net = fields.Monetary(
        string='Salaire net',
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
        ('compute', 'Calculé'),
        ('confirm', 'Confirmé'),
        ('done', 'Validé'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model
    def create(self, vals):
        """Génère le numéro du bulletin"""
        if vals.get('number', 'Nouveau') == 'Nouveau':
            vals['number'] = self.env['ir.sequence'].next_by_code('payroll.slip') or 'PAIE/001'
        return super(PayrollSlip, self).create(vals)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_contract(self):
        """Trouve le contrat actif de l'employé"""
        for record in self:
            if record.employee_id and record.date_from and record.date_to:
                # Chercher un contrat valide pour la période
                contract = record.employee_id.contract_ids.filtered(
                    lambda c: c.state == 'open' and
                              c.date_start <= record.date_to and
                              (not c.date_end or c.date_end >= record.date_from)
                )
                if contract:
                    record.contract_id = contract[0]
                else:
                    record.contract_id = False
            else:
                record.contract_id = False

    @api.depends('contract_id', 'contract_id.wage', 'contract_id.resource_calendar_id')
    def _compute_daily_wage(self):
        """Calcule le taux journalier basé sur le calendrier de travail"""
        for record in self:
            if record.contract_id and record.contract_id.wage:
                # Obtenir le nombre de jours ouvrables par mois du calendrier
                if record.contract_id.resource_calendar_id:
                    # Par défaut 22 jours ouvrables, modifiable via le calendrier
                    working_days_per_month = self._get_working_days_per_month(record.contract_id)
                else:
                    # Fallback à 22 jours si pas de calendrier
                    working_days_per_month = 22

                record.daily_wage = record.contract_id.wage / working_days_per_month
            else:
                record.daily_wage = 0

    def _get_working_days_per_month(self, contract):
        """Version simplifiée basée sur les jours de présence du calendrier"""
        if not contract.resource_calendar_id:
            return 22

        calendar = contract.resource_calendar_id

        # Compter les jours uniques dans le calendrier
        working_days_per_week = len(set(calendar.attendance_ids.mapped('dayofweek')))

        # Convertir en jours par mois
        if working_days_per_week == 6:  # Lundi à Samedi
            return 26
        elif working_days_per_week == 5:  # Lundi à Vendredi
            return 22
        elif working_days_per_week == 7:  # Tous les jours
            return 30
        else:
            # Cas spécial : calculer proportionnellement
            weeks_per_month = 4.33
            return int(working_days_per_week * weeks_per_month)

    # Ajouter aussi un champ pour afficher le nombre de jours ouvrables
    working_days_per_month = fields.Integer(
        string='Jours ouvrables/mois',
        compute='_compute_working_days_per_month',
        store=True
    )

    @api.depends('contract_id', 'contract_id.resource_calendar_id')
    def _compute_working_days_per_month(self):
        """Affiche le nombre de jours ouvrables par mois"""
        for record in self:
            if record.contract_id:
                record.working_days_per_month = self._get_working_days_per_month(record.contract_id)
            else:
                record.working_days_per_month = 22    # Ajouter aussi un champ pour afficher le nombre de jours ouvrables







    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_worked_days(self):
        """Calcule le nombre de jours travaillés depuis les pointages"""
        for record in self:
            if record.employee_id and record.date_from and record.date_to:
                # Récupérer les pointages de la période
                attendances = self.env['attendance.daily.line'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('attendance_id.date', '>=', record.date_from),
                    ('attendance_id.date', '<=', record.date_to),
                    ('attendance_id.state', 'in', ('confirmed', 'processed')),
                    ('is_present', '=', True)
                ])
                record.worked_days = len(attendances)
            else:
                record.worked_days = 0

        # Modifier les calculs des totaux

    @api.depends('line_ids.amount_earning', 'line_ids.amount_deduction')
    def _compute_totals(self):
        """Calcule les totaux du bulletin - CORRIGÉ"""
        for record in self:
            # Calculer les totaux depuis les lignes
            total_earnings = 0.0
            total_deductions = 0.0

            for line in record.line_ids:
                if line.category == 'earning':
                    total_earnings += line.amount_earning
                elif line.category == 'deduction':
                    total_deductions += line.amount_deduction

            record.total_earnings = total_earnings
            record.total_deductions = total_deductions
            record.total_gross = total_earnings
            record.total_net = total_earnings - total_deductions

    def action_compute_sheet(self):
        """Calcule le bulletin de paie"""
        self.ensure_one()

        # Vérifier le contrat
        if not self.contract_id:
            raise ValidationError(
                f"L'employé {self.employee_name} n'a pas de contrat actif pour cette période!"
            )

        if self.state not in ('draft', 'compute'):
            raise ValidationError("Le bulletin doit être en brouillon pour être calculé!")

        # Supprimer les lignes existantes
        self.line_ids.unlink()

        # Créer les lignes de paie
        lines = []

        # 1. Salaire de base (jours travaillés)
        if self.worked_days > 0 and self.daily_wage > 0:
            lines.append((0, 0, {
                'name': 'Jours travaillés',
                'code': 'BASIC',
                'category': 'earning',
                'quantity': self.worked_days,
                'rate': self.daily_wage,
                'sequence': 1,
            }))
        else:
            # Si pas de pointage, prendre le salaire mensuel complet
            if self.wage > 0:
                lines.append((0, 0, {
                    'name': 'Salaire mensuel',
                    'code': 'BASIC',
                    'category': 'earning',
                    'quantity': 1,
                    'rate': self.wage,
                    'sequence': 1,
                }))

        # 2. Heures supplémentaires
        overtime_hours = self._get_overtime_hours()
        if overtime_hours > 0:
            overtime_rate = self.daily_wage / 8 * 1.5  # Taux horaire * 1.5
            lines.append((0, 0, {
                'name': 'Heures supplémentaires',
                'code': 'OVERTIME',
                'category': 'earning',
                'quantity': overtime_hours,
                'rate': overtime_rate,
                'sequence': 2,
            }))

        # 3. Avances à déduire
        advances = self._get_advances()
        advance_seq = 10
        for advance in advances:
            lines.append((0, 0, {
                'name': f'Avance {advance.name}',
                'code': 'ADVANCE',
                'category': 'deduction',
                'quantity': 1,
                'rate': advance.amount,
                'sequence': advance_seq,
                'reference_id': f'employee.advance,{advance.id}'
            }))
            advance_seq += 1

        # 4. Échéances de prêt
        installments = self._get_loan_installments()
        loan_seq = 20
        for installment in installments:
            lines.append((0, 0, {
                'name': f'Prêt {installment.loan_id.name} - Échéance {installment.sequence}',
                'code': 'LOAN',
                'category': 'deduction',
                'quantity': 1,
                'rate': installment.amount,
                'sequence': loan_seq,
                'reference_id': f'loan.installment,{installment.id}'
            }))
            loan_seq += 1

        self.line_ids = lines
        self.state = 'compute'

        # Afficher un résumé
        self.message_post(
            body=f"""
            <b>Bulletin calculé:</b><br/>
            - Jours travaillés: {self.worked_days}<br/>
            - Total gains: {self.total_earnings:,.2f}<br/>
            - Total retenues: {self.total_deductions:,.2f}<br/>
            - Salaire net: {self.total_net:,.2f}
            """
        )

    def _get_overtime_hours(self):
        """Récupère les heures supplémentaires de la période"""
        attendances = self.env['attendance.daily.line'].search([
            ('employee_id', '=', self.employee_id.id),
            ('attendance_id.date', '>=', self.date_from),
            ('attendance_id.date', '<=', self.date_to),
            ('attendance_id.state', 'in', ('confirmed', 'processed')),
            ('is_present', '=', True)
        ])
        return sum(attendances.mapped('overtime_hours'))

    def _get_advances(self):
        """Récupère les avances non traitées de la période"""
        return self.env['employee.advance'].get_unprocessed_advances(
            self.employee_id.id,
            self.date_from,
            self.date_to
        )

    def _get_loan_installments(self):
        """Récupère les échéances de prêt à prélever"""
        return self.env['loan.installment'].get_pending_installments(
            self.employee_id.id,
            self.date_to
        )
    """ Méthode si on veux customiser des nouveaux rubriques
      ou ajouter une ligne personalisée
        def action_add_custom_line(self):         
        self.ensure_one()
        return {
            'name': 'Ajouter une rubrique',
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_slip_id': self.id,
                'default_sequence': 20,
            }
        }

    
    
    """

    def action_confirm(self):
        """Confirme le bulletin"""
        for record in self:
            if record.state != 'compute':
                raise ValidationError("Le bulletin doit être calculé avant confirmation!")
            record.state = 'confirm'

    def action_done(self):
        """Valide le bulletin et marque les éléments comme traités"""
        for record in self:
            if record.state != 'confirm':
                raise ValidationError("Le bulletin doit être confirmé avant validation!")

            # Marquer les avances comme traitées
            for line in record.line_ids.filtered(lambda l: l.code == 'ADVANCE'):
                if line.reference_id:
                    advance = self.env['employee.advance'].browse(int(line.reference_id.split(',')[1]))
                    advance.mark_as_processed(record.number)

            # Marquer les échéances comme traitées
            for line in record.line_ids.filtered(lambda l: l.code == 'LOAN'):
                if line.reference_id:
                    installment = self.env['loan.installment'].browse(int(line.reference_id.split(',')[1]))
                    installment.mark_as_processed(record.number)

            # Marquer les pointages comme traités
            attendances = self.env['attendance.daily.line'].search([
                ('employee_id', '=', record.employee_id.id),
                ('attendance_id.date', '>=', record.date_from),
                ('attendance_id.date', '<=', record.date_to),
                ('attendance_id.state', '=', 'confirmed')
            ])
            attendances.write({'is_processed': True})
            attendances.mapped('attendance_id').write({'state': 'processed'})

            record.state = 'done'

    def action_print_slip(self):
        """Imprime le bulletin de paie"""
        self.ensure_one()
        return self.env.ref('adi_simple_payroll.action_report_payroll_slip').report_action(self)

    def action_cancel(self):
        """Annule le bulletin"""
        for record in self:
            if record.state == 'done':
                raise ValidationError("Impossible d'annuler un bulletin validé!")
            record.state = 'cancel'

    def action_add_custom_earning(self):
        """Ajoute rapidement une rubrique de gain"""
        self.ensure_one()
        # Déterminer la séquence
        max_seq = max(self.line_ids.mapped('sequence') or [0])

        self.env['payroll.line'].create({
            'slip_id': self.id,
            'name': 'Rubrique personnalisée',
            'code': 'CUSTOM',
            'category': 'earning',
            'line_type': 'earning',
            'sequence': max_seq + 1,
            'quantity': 1,
            'rate': 0,
        })

    def action_add_custom_deduction(self):
        """Ajoute rapidement une rubrique de retenue"""
        self.ensure_one()
        max_seq = max(self.line_ids.mapped('sequence') or [0])

        self.env['payroll.line'].create({
            'slip_id': self.id,
            'name': 'Retenue personnalisée',
            'code': 'DEDUCT',
            'category': 'deduction',
            'line_type': 'deduction',
            'sequence': max_seq + 1,
            'quantity': 1,
            'rate': 0,
        })

