# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class PayrollPeriod(models.Model):
    """Périodes de paie (mensuelle, hebdomadaire, etc.)"""
    _name = 'payroll.period'
    _description = 'Période de paie'
    _order = 'date_start desc'

    name = fields.Char(
        string='Nom de la période',
        compute='_compute_name',
        store=True,
        readonly=False  # Permet la modification manuelle si nécessaire
    )

    period_type = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('weekly', 'Hebdomadaire'),
        ('biweekly', 'Bimensuelle')
    ], string='Type de période', default='monthly', required=True)

    date_start = fields.Date(
        string='Date de début',
        required=True,
        default=fields.Date.today
    )

    date_end = fields.Date(
        string='Date de fin',
        required=True,
        compute='_compute_date_end',
        store=True,
        readonly=False
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('open', 'Ouverte'),
        ('closed', 'Fermée')
    ], string='État', default='draft')

    batch_ids = fields.One2many(
        'payroll.batch',
        'period_id',
        string='Lots de paie'
    )
    check_chev = fields.Boolean("Vérifier les chevauchements?",
                                default=True)

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
        required=True
    )

    @api.depends('period_type', 'date_start')
    def _compute_date_end(self):
        """Calcule automatiquement la date de fin selon le type de période"""
        for record in self:
            if record.date_start and record.period_type:
                if record.period_type == 'monthly':
                    # Dernier jour du mois
                    record.date_end = record.date_start + relativedelta(day=31)
                elif record.period_type == 'weekly':
                    record.date_end = record.date_start + relativedelta(days=6)
                elif record.period_type == 'biweekly':
                    record.date_end = record.date_start + relativedelta(days=13)

    @api.depends('period_type', 'date_start', 'date_end')
    def _compute_name(self):
        """Calcule le nom de la période"""
        for record in self:
            if record.date_start and record.date_end:
                if record.period_type == 'monthly':
                    # Format français pour le mois
                    months_fr = {
                        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
                        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
                        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
                    }
                    month_name = months_fr.get(record.date_start.month, '')
                    record.name = f"Paie {month_name} {record.date_start.year}"
                elif record.period_type == 'weekly':
                    record.name = f"Semaine du {record.date_start.strftime('%d/%m')} au {record.date_end.strftime('%d/%m/%Y')}"
                else:
                    record.name = f"Paie du {record.date_start.strftime('%d/%m')} au {record.date_end.strftime('%d/%m/%Y')}"
            else:
                record.name = f"Nouvelle période {record.period_type or ''}"

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Vérifie la cohérence des dates"""
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start > record.date_end:
                    raise ValidationError("La date de fin doit être après la date de début!")

                # Vérifier les chevauchements
                if record.check_chev:
                    overlapping = self.search([
                        ('id', '!=', record.id),
                        ('company_id', '=', record.company_id.id),
                        '|', '|',
                        '&', ('date_start', '<=', record.date_start), ('date_end', '>=', record.date_start),
                        '&', ('date_start', '<=', record.date_end), ('date_end', '>=', record.date_end),
                        '&', ('date_start', '>=', record.date_start), ('date_end', '<=', record.date_end),
                    ])
                    if overlapping:
                        raise ValidationError("Cette période chevauche avec une période existante!")

    def action_open(self):
        """Ouvre la période"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError("Seule une période en brouillon peut être ouverte!")

        # Vérifier qu'aucune autre période n'est ouverte
        open_periods = self.search([
            ('state', '=', 'open'),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id)
        ])
        if open_periods:
            raise ValidationError("Une autre période est déjà ouverte! Veuillez la fermer d'abord.")

        self.state = 'open'

    def action_close(self):
        """Ferme la période"""
        self.ensure_one()
        if self.state != 'open':
            raise ValidationError("Seule une période ouverte peut être fermée!")

        # Vérifier que tous les lots sont validés
        if any(batch.state != 'done' for batch in self.batch_ids):
            raise ValidationError("Tous les lots doivent être validés avant de fermer la période!")

        self.state = 'closed'

    @api.model
    def create_next_period(self):
        """Crée automatiquement la période suivante"""
        last_period = self.search([], order='date_end desc', limit=1)
        if last_period:
            next_start = last_period.date_end + relativedelta(days=1)
            return self.create({
                'period_type': last_period.period_type,
                'date_start': next_start,
                'company_id': last_period.company_id.id,
            })
