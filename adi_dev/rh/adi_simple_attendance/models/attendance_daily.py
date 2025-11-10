# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import ValidationError


class AttendanceDaily(models.Model):
    """Modèle principal pour la gestion quotidienne des pointages"""
    _name = 'attendance.daily'
    _description = 'Pointage Quotidien'
    _order = 'date desc'
    _rec_name = 'date'
    _inherit = ['mail.thread','mail.activity.mixin']


    def action_set_to_draft(self):
        """Remet le pointage en brouillon si non traité en paie"""
        self.ensure_one()

        # Vérifier que le pointage n'est pas traité en paie
        if self.state == 'processed':
            # Vérifier si des lignes ont été traitées
            processed_lines = self.attendance_line_ids.filtered(lambda l: l.is_processed)
            if processed_lines:
                raise ValidationError(
                    "Impossible de remettre en brouillon : des lignes ont été traitées en paie!\n"
                    f"Nombre de lignes traitées : {len(processed_lines)}"
                )

        # Remettre en brouillon
        self.state = 'draft'



    def action_cancel_attendance(self):
        """Annule toutes les présences du pointage si non traité"""
        self.ensure_one()

        # Vérifier que le pointage n'est pas traité
        if self.state == 'processed':
            raise ValidationError("Impossible d'annuler : le pointage a été traité en paie!")

        # Vérifier si des lignes ont été traitées
        processed_lines = self.attendance_line_ids.filtered(lambda l: l.is_processed)
        if processed_lines:
            raise ValidationError(
                "Impossible d'annuler : certaines lignes ont été traitées en paie!\n"
                f"Employés concernés : {', '.join(processed_lines.mapped('employee_name'))}"
            )

        # Annuler toutes les présences
        for line in self.attendance_line_ids:
            line.write({
                'presence': False,
                'standard_hours': 0.0,
                'actual_hours': 0.0,
                'overtime_hours': 0.0
            })

        # Mettre en brouillon si confirmé
        self.write({'state': 'canceled'})



    def action_print_sheet(self):
        """Imprime la feuille de présence"""
        self.ensure_one()
        return self.env.ref('adi_simple_attendance.action_report_attendance_sheet').report_action(self)
    # Champs principaux
    date = fields.Date(
        string='Date du pointage',
        required=True,
        default=fields.Date.today
    )

    # Sélection des employés
    selection_type = fields.Selection([
        ('all', 'Tous les employés'),
        ('department', 'Par département')
    ], string='Type de sélection', default='all', required=True)

    department_ids = fields.Many2many(
        'hr.department',
        string='Départements'
    )

    attendance_line_ids = fields.One2many(
        'attendance.daily.line',
        'attendance_id',
        string='Lignes de pointage'
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('processed', 'Traité'),
        ('canceled', 'Annulé')
    ], string='État', default='draft')

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )

    @api.onchange('selection_type')
    def _onchange_selection_type(self):
        """Vide les lignes et départements quand on change le type de sélection"""
        # Vider les lignes existantes
        self.attendance_line_ids = [(5, 0, 0)]

        if self.selection_type == 'all':
            # Si on passe à "tous", on vide les départements et génère toutes les lignes
            self.department_ids = [(5, 0, 0)]
            # Générer automatiquement toutes les lignes
            employees = self.env['hr.employee'].search([
                ('contract_ids.state', '=', 'open')
            ])
            lines = []
            for employee in employees:
                lines.append((0, 0, {
                    'employee_id': employee.id,
                    'presence': True,  # Par défaut présent
                    'standard_hours': 8.0,
                    'actual_hours': 8.0,  # NOUVEAU : actual_hours par défaut
                }))
            self.attendance_line_ids = lines
        else:
            # Si on passe à "par département", on vide tout
            self.department_ids = [(5, 0, 0)]

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        """Régénère les lignes quand on change les départements"""
        if self.selection_type == 'department':
            # Vider toutes les lignes existantes
            self.attendance_line_ids = [(5, 0, 0)]

            # Si des départements sont sélectionnés, générer les lignes
            if self.department_ids:
                employees = self.env['hr.employee'].search([
                    ('contract_ids.state', '=', 'open'),
                    ('department_id', 'in', self.department_ids.ids)
                ])

                lines = []
                for employee in employees:
                    lines.append((0, 0, {
                        'employee_id': employee.id,
                        'presence': True,  # Par défaut présent
                        'standard_hours': 8.0,
                        'actual_hours': 8.0,  # NOUVEAU : actual_hours par défaut
                    }))
                self.attendance_line_ids = lines

    def action_generate_lines(self):
        """Bouton pour régénérer toutes les lignes"""
        self.ensure_one()

        # Supprimer toutes les lignes existantes
        self.attendance_line_ids.unlink()

        # Récupérer les employés selon la sélection
        domain = [('contract_ids.state', '=', 'open')]
        if self.selection_type == 'department' and self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))

        employees = self.env['hr.employee'].search(domain)

        # Créer une ligne pour chaque employé
        for employee in employees:
            self.env['attendance.daily.line'].create({
                'attendance_id': self.id,
                'employee_id': employee.id,
                'presence': True,  # Par défaut présent
                'standard_hours': 8.0,
                'actual_hours': 8.0,  # NOUVEAU : actual_hours par défaut
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{len(employees)} lignes créées',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_confirm(self):
        """Confirme le pointage du jour"""
        self.ensure_one()
        if not self.attendance_line_ids:
            raise ValidationError("Aucune ligne de pointage à confirmer!")
        self.state = 'confirmed'

    def action_process(self):
        """Marque le pointage comme traité (utilisé dans la paie)"""
        self.ensure_one()
        self.state = 'processed'
        # Marquer toutes les lignes comme traitées
        self.attendance_line_ids.write({'is_processed': True})

    def unlink(self):
        """Empêche la suppression des pointages confirmés"""
        for record in self:
            if record.state != 'canceled':
                raise ValidationError("Impossible de supprimer un pointage non annulé!")
        return super(AttendanceDaily, self).unlink()


class AttendanceDailyLine(models.Model):
    """Lignes de détail pour chaque employé"""
    _name = 'attendance.daily.line'
    _description = 'Ligne de pointage'
    _rec_name = 'employee_id'

    attendance_id = fields.Many2one(
        'attendance.daily',
        string='Pointage',
        required=True,
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True
    )

    # Informations employé (champs liés pour affichage)
    employee_name = fields.Char(
        related='employee_id.name',
        string='Nom et Prénom',
        readonly=True,
        store=True
    )

    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Poste',
        readonly=True,
        store=True
    )

    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Département',
        readonly=True,
        store=True
    )

    # NOUVEAU : Un seul champ pour gérer la présence
    presence = fields.Boolean(
        string='Présence',
        default=True,
        help="Coché = Présent, Décoché = Absent"
    )

    # Champs calculés pour compatibilité
    is_present = fields.Boolean(
        string='Présent',
        compute='_compute_presence_status',
        store=True
    )

    is_absent = fields.Boolean(
        string='Absent',
        compute='_compute_presence_status',
        store=True
    )

    # Heures

    standard_hours = fields.Float(
        string='Heures standard',
        default=8.0,
        readonly=True,  # NOUVEAU : en lecture seule
        help="Heures de présence normale (par défaut 8h)"
    )

    actual_hours = fields.Float(
        string='Heures de présence',
        default=8.0,  # NOUVEAU : valeur par défaut 8
        help="Heures réelles de présence"
    )
    overtime_hours = fields.Float(
        string='Heures supplémentaires',
        default=0.0
    )

    # État
    is_processed = fields.Boolean(
        string='Traité',
        default=False,
        help="Indique si cette ligne a été utilisée dans une paie"
    )

    company_id = fields.Many2one(
        related='attendance_id.company_id',
        store=True
    )

    @api.depends('presence')
    def _compute_presence_status(self):
        """Calcule is_present et is_absent basé sur le champ presence"""
        for record in self:
            record.is_present = record.presence
            record.is_absent = not record.presence

    @api.onchange('presence')
    def _onchange_presence(self):
        """Ajuste les heures selon la présence"""
        if self.presence:  # Si présent
            # Toujours mettre 8h par défaut quand on coche présent
            self.standard_hours = 8.0
            self.actual_hours = 8.0  # NOUVEAU : remettre à 8h
            # Réinitialiser les heures supplémentaires si elles étaient à 0
            if not self.overtime_hours:
                self.overtime_hours = 0.0
        else:  # Si absent
            self.standard_hours = 0.0
            self.actual_hours = 0.0
            self.overtime_hours = 0.0

    @api.constrains('employee_id', 'attendance_id')
    def _check_unique_employee(self):
        """Vérifie qu'un employé n'apparaît qu'une fois par pointage"""
        for record in self:
            if not record.employee_id:
                continue
            duplicate = self.search([
                ('attendance_id', '=', record.attendance_id.id),
                ('employee_id', '=', record.employee_id.id),
                ('id', '!=', record.id)
            ])
            if duplicate:
                raise ValidationError(
                    f"L'employé {record.employee_name} est déjà dans la liste!"
                )

    def get_total_hours(self):
        """Calcule le total des heures pour la ligne"""
        self.ensure_one()
        if not self.presence:  # Si absent
            return 0.0
        elif self.actual_hours > 0:
            return self.actual_hours + self.overtime_hours
        else:
            return self.standard_hours + self.overtime_hours
