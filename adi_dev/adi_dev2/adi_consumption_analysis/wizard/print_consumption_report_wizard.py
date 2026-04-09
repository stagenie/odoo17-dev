# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PrintConsumptionReportWizard(models.TransientModel):
    """
    Wizard pour imprimer un rapport PDF des consommations de matières
    premières sur une période donnée.

    L'utilisateur peut :
    - choisir une période (date début / date fin)
    - sélectionner tous les articles ou seulement certains
    - filtrer par type de production (SOLO/CLASSICO, Sandwich GF)
    - activer la métrique MP / Produit Fini
    """
    _name = 'ron.print.consumption.report.wizard'
    _description = 'Wizard Impression Rapport Consommations'

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

    all_products = fields.Boolean(
        string='Tous les Articles',
        default=True,
        help="Si coché, inclut tous les articles consommés sur la période.",
    )

    product_ids = fields.Many2many(
        'product.product',
        string='Articles',
        help="Liste des articles à inclure (si 'Tous les Articles' est décoché).",
    )

    production_type = fields.Selection(
        [
            ('all', 'Tous'),
            ('solo_classico', 'SOLO / CLASSICO'),
            ('sandwich_gf', 'Sandwich Grand Format'),
        ],
        string='Type de Production',
        default='all',
        required=True,
    )

    include_mp_per_finished = fields.Boolean(
        string='Inclure MP / Produit Fini',
        default=True,
        help="Ajoute la métrique kg consommés par carton produit pour chaque article.",
    )

    only_done = fields.Boolean(
        string='Productions Terminées Uniquement',
        default=False,
        help="Si coché, exclut les productions en brouillon et confirmées.",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_("La date de début doit être antérieure à la date de fin."))

    def _build_domain(self):
        """Construit le domaine de recherche sur ron.consumption.analysis."""
        self.ensure_one()
        domain = [
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        if not self.all_products and self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.production_type != 'all':
            domain.append(('production_type', '=', self.production_type))
        if self.only_done:
            domain.append(('production_state', '=', 'done'))
        return domain

    def _prepare_report_data(self):
        """Prépare les données à afficher dans le rapport PDF."""
        self.ensure_one()
        Analysis = self.env['ron.consumption.analysis']
        domain = self._build_domain()

        # Agréger par produit : une ligne par article
        groups = Analysis.read_group(
            domain=domain,
            fields=[
                'product_id',
                'product_uom_id',
                'quantity',
                'weight_kg',
                'total_cost',
                'total_cartons_produced',
            ],
            groupby=['product_id'],
            orderby='product_id',
            lazy=False,
        )

        # Récupérer le total de cartons produits sur la période pour le ratio
        # MP/produit fini. On fait un read_group par production_id pour éviter
        # le double-comptage (une production peut avoir N lignes MP).
        prod_groups = Analysis.read_group(
            domain=domain,
            fields=['production_id', 'total_cartons_produced:max'],
            groupby=['production_id'],
            lazy=False,
        )
        total_cartons = sum(
            (g.get('total_cartons_produced') or 0.0) for g in prod_groups
        )

        lines = []
        grand_total_weight = 0.0
        grand_total_cost = 0.0
        grand_total_qty = 0.0

        for g in groups:
            if not g.get('product_id'):
                continue
            product_id = g['product_id'][0]
            product = self.env['product.product'].browse(product_id)
            weight = g.get('weight_kg') or 0.0
            cost = g.get('total_cost') or 0.0
            qty = g.get('quantity') or 0.0

            lines.append({
                'product_name': product.display_name,
                'product_default_code': product.default_code or '',
                'uom_name': product.uom_id.name,
                'quantity': qty,
                'weight_kg': weight,
                'total_cost': cost,
                'mp_per_carton': (weight / total_cartons) if total_cartons > 0 else 0.0,
            })

            grand_total_weight += weight
            grand_total_cost += cost
            grand_total_qty += qty

        return {
            'doc_ids': self.ids,
            'doc_model': self._name,
            'docs': self,
            'data': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'production_type': dict(self._fields['production_type'].selection).get(
                    self.production_type
                ),
                'production_type_code': self.production_type,
                'all_products': self.all_products,
                'only_done': self.only_done,
                'include_mp_per_finished': self.include_mp_per_finished,
                'company_name': self.company_id.name,
                'currency_symbol': self.company_id.currency_id.symbol or '',
                'lines': lines,
                'total_cartons': total_cartons,
                'grand_total_weight': grand_total_weight,
                'grand_total_cost': grand_total_cost,
                'grand_total_qty': grand_total_qty,
                'line_count': len(lines),
            },
        }

    def action_print_report(self):
        """Lance l'impression du rapport PDF."""
        self.ensure_one()
        data = self._prepare_report_data()
        return self.env.ref(
            'adi_consumption_analysis.action_report_consumption_period'
        ).report_action(self, data=data)

    def action_open_analysis(self):
        """Ouvre la vue d'analyse préfiltrée avec les critères du wizard."""
        self.ensure_one()
        action = self.env.ref(
            'adi_consumption_analysis.action_ron_consumption_analysis'
        ).read()[0]
        action['domain'] = self._build_domain()
        action['context'] = {
            'search_default_group_product': 1,
        }
        return action
