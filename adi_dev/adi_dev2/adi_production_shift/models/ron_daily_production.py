# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RonDailyProductionShift(models.Model):
    _inherit = 'ron.daily.production'

    # -------------------------------------------------------------------------
    # Champs de shift
    # -------------------------------------------------------------------------
    shift_two = fields.Selection([
        ('day', 'Jour'),
        ('night', 'Nuit'),
    ], string="Shift", tracking=True,
       help="Sélectionnez le shift pour cette production (système 2 shifts)")

    shift_three = fields.Selection([
        ('morning', 'Matin'),
        ('afternoon', 'Après-midi'),
        ('night', 'Nuit'),
    ], string="Shift", tracking=True,
       help="Sélectionnez le shift pour cette production (système 3 shifts)")

    # Champ calculé pour affichage unifié dans les listes
    shift_display = fields.Char(
        string="Shift",
        compute='_compute_shift_display',
        store=True,
        help="Affichage du shift pour les listes et rapports"
    )

    # Champ calculé pour récupérer le système de shift depuis la config
    shift_system = fields.Selection([
        ('no_shift', '8 heures (pas de shift)'),
        ('two_shifts', '2 Shifts (Jour/Nuit)'),
        ('three_shifts', '3 Shifts (Matin/Après-midi/Nuit)'),
    ], string="Système de Shift",
       compute='_compute_shift_system',
       store=False,
       readonly=True,
       default=lambda self: self._get_default_shift_system())

    # -------------------------------------------------------------------------
    # Méthodes de calcul
    # -------------------------------------------------------------------------
    @api.model
    def _get_default_shift_system(self):
        """Récupère le système de shift par défaut depuis la configuration."""
        company = self.env.company
        config = self.env['ron.production.config'].sudo().search([
            ('company_id', '=', company.id)
        ], limit=1)
        return config.shift_system if config else 'no_shift'

    @api.depends('company_id')
    def _compute_shift_system(self):
        """Récupère le système de shift depuis la configuration de la société."""
        for rec in self:
            config = self.env['ron.production.config'].sudo().search([
                ('company_id', '=', rec.company_id.id)
            ], limit=1)
            rec.shift_system = config.shift_system if config else 'no_shift'

    @api.onchange('company_id')
    def _onchange_company_shift_system(self):
        """Met à jour le système de shift quand la société change."""
        if self.company_id:
            config = self.env['ron.production.config'].sudo().search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            self.shift_system = config.shift_system if config else 'no_shift'
        else:
            self.shift_system = 'no_shift'

    @api.depends('shift_two', 'shift_three', 'company_id')
    def _compute_shift_display(self):
        """Calcule l'affichage unifié du shift."""
        shift_two_labels = dict(self._fields['shift_two'].selection)
        shift_three_labels = dict(self._fields['shift_three'].selection)

        for rec in self:
            config = self.env['ron.production.config'].sudo().search([
                ('company_id', '=', rec.company_id.id)
            ], limit=1)
            shift_system = config.shift_system if config else 'no_shift'

            if shift_system == 'two_shifts' and rec.shift_two:
                rec.shift_display = shift_two_labels.get(rec.shift_two, '')
            elif shift_system == 'three_shifts' and rec.shift_three:
                rec.shift_display = shift_three_labels.get(rec.shift_three, '')
            else:
                rec.shift_display = ''

    # -------------------------------------------------------------------------
    # Contraintes
    # -------------------------------------------------------------------------
    @api.constrains('production_date', 'shift_two', 'shift_three')
    def _check_unique_date_shift(self):
        """
        Une seule production par jour ET par shift selon le système configuré.
        Cette contrainte remplace la contrainte originale _check_unique_date.
        """
        for rec in self:
            # Récupérer la configuration du système de shift
            config = self.env['ron.production.config'].sudo().search([
                ('company_id', '=', rec.company_id.id)
            ], limit=1)
            shift_system = config.shift_system if config else 'no_shift'

            # Construire le domaine de recherche de base
            domain = [
                ('production_date', '=', rec.production_date),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id)
            ]

            # Adapter le domaine selon le système de shift
            if shift_system == 'two_shifts':
                # Vérifier que le shift est sélectionné
                if not rec.shift_two:
                    raise ValidationError(_(
                        "Veuillez sélectionner le shift (Jour/Nuit) pour cette production."
                    ))
                domain.append(('shift_two', '=', rec.shift_two))
                shift_label = dict(self._fields['shift_two'].selection).get(rec.shift_two, '')

            elif shift_system == 'three_shifts':
                # Vérifier que le shift est sélectionné
                if not rec.shift_three:
                    raise ValidationError(_(
                        "Veuillez sélectionner le shift (Matin/Après-midi/Nuit) pour cette production."
                    ))
                domain.append(('shift_three', '=', rec.shift_three))
                shift_label = dict(self._fields['shift_three'].selection).get(rec.shift_three, '')

            else:
                # Système no_shift : comportement par défaut (1 production par jour)
                shift_label = None

            # Rechercher les productions existantes
            existing = self.search(domain)
            if existing:
                if shift_label:
                    raise ValidationError(_(
                        "Une production existe déjà pour la date %s et le shift '%s' (Réf: %s)."
                    ) % (rec.production_date, shift_label, existing[0].name))
                else:
                    raise ValidationError(_(
                        "Une production existe déjà pour la date %s (Réf: %s)."
                    ) % (rec.production_date, existing[0].name))

    def _check_unique_date(self):
        """
        Désactive la contrainte originale du module parent.
        La nouvelle contrainte _check_unique_date_shift gère tous les cas.
        """
        # Ne rien faire - la contrainte _check_unique_date_shift gère tout
        pass
