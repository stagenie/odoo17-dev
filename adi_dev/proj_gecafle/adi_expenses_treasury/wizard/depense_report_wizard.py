# -*- coding: utf-8 -*-
"""
Wizard d'impression de l'état de sortie des frais.

Filtres :
  - Période (date_from / date_to)
  - Caisses : par défaut « toutes » (case cochée). Si décochée, l'utilisateur
    peut sélectionner un sous-ensemble via un Many2many.
  - Catégories de frais : même pattern « toutes / sélection ».
  - Motifs de trésorerie : même pattern « tous / sélection ».
  - État : par défaut « comptabilisés » (l'état le plus utile pour un état
    de sortie). L'utilisateur peut élargir à brouillon ou annulé au besoin.

Sortie : PDF A4 portrait listant les frais filtrés avec total en pied.
"""
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DepenseReportWizard(models.TransientModel):
    _name = 'depense.report.wizard'
    _description = 'État de Sortie des Frais'

    # ------------------------------------------------------------------
    # Période
    # ------------------------------------------------------------------
    date_from = fields.Date(
        string='Date Début',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='Date Fin',
        required=True,
        default=lambda self: (
            fields.Date.today().replace(day=1) + relativedelta(months=1, days=-1)
        ),
    )

    # ------------------------------------------------------------------
    # Caisses
    # ------------------------------------------------------------------
    all_caisses = fields.Boolean(
        string='Toutes les caisses',
        default=True,
    )
    caisse_ids = fields.Many2many(
        'treasury.cash',
        'depense_report_wizard_caisse_rel',
        'wizard_id', 'caisse_id',
        string='Caisses',
    )

    # ------------------------------------------------------------------
    # Catégories de frais
    # ------------------------------------------------------------------
    all_categories = fields.Boolean(
        string='Toutes les catégories',
        default=True,
    )
    categorie_ids = fields.Many2many(
        'depenses.categorie',
        'depense_report_wizard_categorie_rel',
        'wizard_id', 'categorie_id',
        string='Catégories',
    )

    # ------------------------------------------------------------------
    # Motifs (treasury.operation.category)
    # ------------------------------------------------------------------
    all_motifs = fields.Boolean(
        string='Tous les motifs',
        default=True,
    )
    motif_ids = fields.Many2many(
        'treasury.operation.category',
        'depense_report_wizard_motif_rel',
        'wizard_id', 'motif_id',
        string='Motifs',
        domain="[('operation_type', 'in', ['out', 'both'])]",
    )

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state_filter = fields.Selection(
        [
            ('all', 'Tous les états'),
            ('posted', 'Comptabilisés uniquement'),
            ('draft', 'Brouillons uniquement'),
            ('cancel', 'Annulés uniquement'),
            ('not_cancel', 'Hors annulés'),
        ],
        string='État',
        default='posted',
        required=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # Onchange : vider la sélection quand on coche « Tous »
    # ------------------------------------------------------------------
    @api.onchange('all_caisses')
    def _onchange_all_caisses(self):
        if self.all_caisses:
            self.caisse_ids = [(5, 0, 0)]

    @api.onchange('all_categories')
    def _onchange_all_categories(self):
        if self.all_categories:
            self.categorie_ids = [(5, 0, 0)]

    @api.onchange('all_motifs')
    def _onchange_all_motifs(self):
        if self.all_motifs:
            self.motif_ids = [(5, 0, 0)]

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_(
                    "La date de début doit être antérieure à la date de fin."))

    @api.constrains('all_caisses', 'caisse_ids')
    def _check_caisses(self):
        for rec in self:
            if not rec.all_caisses and not rec.caisse_ids:
                raise UserError(_(
                    "Sélectionnez au moins une caisse, ou cochez « Toutes les caisses »."))

    @api.constrains('all_categories', 'categorie_ids')
    def _check_categories(self):
        for rec in self:
            if not rec.all_categories and not rec.categorie_ids:
                raise UserError(_(
                    "Sélectionnez au moins une catégorie, ou cochez « Toutes les catégories »."))

    @api.constrains('all_motifs', 'motif_ids')
    def _check_motifs(self):
        for rec in self:
            if not rec.all_motifs and not rec.motif_ids:
                raise UserError(_(
                    "Sélectionnez au moins un motif, ou cochez « Tous les motifs »."))

    # ------------------------------------------------------------------
    # Préparation du domaine et du rapport
    # ------------------------------------------------------------------
    def _build_domain(self):
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if not self.all_caisses:
            domain.append(('caisse_id', 'in', self.caisse_ids.ids))
        if not self.all_categories:
            domain.append(('categorie', 'in', self.categorie_ids.ids))
        if not self.all_motifs:
            domain.append(('motif_id', 'in', self.motif_ids.ids))

        if self.state_filter == 'posted':
            domain.append(('state', '=', 'posted'))
        elif self.state_filter == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.state_filter == 'cancel':
            domain.append(('state', '=', 'cancel'))
        elif self.state_filter == 'not_cancel':
            domain.append(('state', '!=', 'cancel'))
        # 'all' : pas de filtre
        return domain

    def _prepare_report_data(self):
        self.ensure_one()
        Depense = self.env['depenses.depense']
        domain = self._build_domain()
        depenses = Depense.search(domain, order='date asc, id asc')

        lines = []
        total = 0.0
        for d in depenses:
            lines.append({
                'date': d.date,
                'name': d.name or '',
                'caisse': d.caisse_id.name or '',
                'categorie': d.categorie.name or '',
                'motif': d.motif_id.name or '',
                'partner': d.partner_id.name or '',
                'description': d.description or '',
                'state': dict(d._fields['state'].selection).get(d.state, ''),
                'state_code': d.state,
                'montant': d.montant or 0.0,
            })
            total += d.montant or 0.0

        # Libellés pour l'en-tête (texte synthétisé : « Toutes » ou liste)
        caisses_label = (
            _("Toutes") if self.all_caisses
            else ", ".join(self.caisse_ids.mapped('name'))
        )
        categories_label = (
            _("Toutes") if self.all_categories
            else ", ".join(self.categorie_ids.mapped('name'))
        )
        motifs_label = (
            _("Tous") if self.all_motifs
            else ", ".join(self.motif_ids.mapped('name'))
        )
        state_label = dict(self._fields['state_filter'].selection).get(self.state_filter)

        return {
            'doc_ids': self.ids,
            'doc_model': self._name,
            'docs': self,
            'data': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'caisses_label': caisses_label,
                'categories_label': categories_label,
                'motifs_label': motifs_label,
                'state_label': state_label,
                'company_name': self.company_id.name,
                'currency_symbol': self.company_id.currency_id.symbol or '',
                'lines': lines,
                'total': total,
                'line_count': len(lines),
            },
        }

    # ------------------------------------------------------------------
    # Action principale
    # ------------------------------------------------------------------
    def action_print_report(self):
        self.ensure_one()
        data = self._prepare_report_data()
        return self.env.ref(
            'adi_expenses_treasury.action_report_depense_state'
        ).report_action(self, data=data)

    def action_view_filtered(self):
        """Ouvre la liste des frais filtrés (utile pour vérifier avant impression)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Frais filtrés'),
            'res_model': 'depenses.depense',
            'view_mode': 'tree,form',
            'domain': self._build_domain(),
            'context': {'search_default_group_by_categorie': 1},
        }
