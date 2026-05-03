# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PrintConsumptionReportWizard(models.TransientModel):
    """Extension du wizard pour gérer la portée MP / Emballages / Films."""
    _inherit = 'ron.print.consumption.report.wizard'

    content_scope = fields.Selection(
        [
            ('consumption', 'Rapport de Consommation Globale (MP + Emballages/Films)'),
            ('all', 'Rapport Complet (MP + Emballages/Films + Récupérables)'),
            ('raw_material', 'Matières Premières uniquement'),
            ('packaging_only', 'Emballages/Films uniquement (coûts)'),
            ('recoverables_only', 'Rebuts/Pâte récupérables uniquement'),
        ],
        string='Portée du Rapport',
        default='consumption',
        required=True,
        help="Détermine ce qui apparaît dans le rapport :\n"
             "- Consommation Globale (défaut) : MP + emballages/films, sans récupérables\n"
             "- Rapport Complet : MP + emballages/films + rebuts/pâte récupérables\n"
             "- MP uniquement : comportement historique du module de base\n"
             "- Emballages/Films uniquement : seulement les coûts d'emballage et de films\n"
             "- Récupérables uniquement : rebuts récupérables + pâte récupérable",
    )

    compute_net_cost = fields.Boolean(
        string='Calculer le Coût Net',
        default=True,
        help="Si coché, le rapport affiche le Coût Net = Conso brute - Récupérables\n"
             "(les récupérables sont déduits du grand total).\n"
             "Sinon, les récupérables sont affichés à titre informatif sans "
             "impact sur le total consommation.",
    )

    @api.onchange('content_scope')
    def _onchange_content_scope(self):
        """En mode 'packaging_only' ou 'recoverables_only', MP/Carton n'a pas de sens."""
        if self.content_scope in ('packaging_only', 'recoverables_only'):
            self.include_mp_per_finished = False

    def _build_domain(self):
        """Ajoute le filtre catégorie selon la portée choisie."""
        domain = super()._build_domain()
        if self.content_scope == 'consumption':
            # Consommation globale = tout SAUF les récupérables.
            domain.append(
                ('consumption_category', 'in', ('raw_material', 'packaging', 'film'))
            )
        elif self.content_scope == 'raw_material':
            domain.append(('consumption_category', '=', 'raw_material'))
        elif self.content_scope == 'packaging_only':
            domain.append(('consumption_category', 'in', ('packaging', 'film')))
        elif self.content_scope == 'recoverables_only':
            domain.append(
                ('consumption_category', 'in', ('scrap_recoverable', 'paste_recoverable'))
            )
        return domain

    def _prepare_packaging_lines(self):
        """Agrège les emballages/films par sous-type sur la période.

        Retourne une liste de dicts prêts pour le rendu PDF, avec :
            subtype, category, quantity, unit_cost, total_cost
        """
        self.ensure_one()
        Analysis = self.env['ron.consumption.analysis']

        # Domaine de base sans le filtre catégorie ajouté par _build_domain
        # → on veut les emballages/films même si l'utilisateur a coché
        # "MP + Emballages" (scope='all').
        base_domain = [
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('consumption_category', 'in', ('packaging', 'film')),
        ]
        if self.production_type != 'all':
            base_domain.append(('production_type', '=', self.production_type))
        if self.only_done:
            base_domain.append(('production_state', '=', 'done'))

        groups = Analysis.read_group(
            domain=base_domain,
            fields=['consumption_subtype', 'consumption_category',
                    'quantity', 'total_cost'],
            groupby=['consumption_subtype', 'consumption_category'],
            lazy=False,
        )

        lines = []
        total_cost = 0.0
        total_qty = 0.0
        for g in groups:
            if not g.get('consumption_subtype'):
                continue
            qty = g.get('quantity') or 0.0
            cost = g.get('total_cost') or 0.0
            unit_cost = (cost / qty) if qty > 0 else 0.0
            lines.append({
                'subtype': g['consumption_subtype'],
                'category': g.get('consumption_category') or '',
                'quantity': qty,
                'unit_cost': unit_cost,
                'total_cost': cost,
            })
            total_cost += cost
            total_qty += qty

        # Tri stable par catégorie puis sous-type pour un PDF prévisible
        lines.sort(key=lambda l: (l['category'], l['subtype']))
        return lines, total_cost, total_qty

    def _prepare_recoverable_lines(self):
        """Agrège les rebuts/pâte récupérables par type + produit sur la période.

        Interroge directement ron.scrap.line pour conserver l'info produit
        (la vue SQL met product_id à NULL pour ne pas polluer les totaux MP
        du wizard parent).

        Retourne (lines, total_cost, total_weight) où chaque ligne contient :
            scrap_type, type_label, product_name, weight_kg, cost_per_kg, total_cost
        """
        self.ensure_one()
        ScrapLine = self.env['ron.scrap.line']

        domain = [
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to),
            ('daily_production_id.company_id', '=', self.company_id.id),
        ]
        if self.production_type != 'all':
            domain.append(('daily_production_id.production_type', '=', self.production_type))
        if self.only_done:
            domain.append(('daily_production_id.state', '=', 'done'))

        groups = ScrapLine.read_group(
            domain=domain,
            fields=['scrap_type', 'product_id', 'weight_kg', 'total_cost'],
            groupby=['scrap_type', 'product_id'],
            lazy=False,
        )

        type_labels = {
            'scrap_recoverable': 'Rebut Récupérable',
            'paste_recoverable': 'Pâte Récupérable',
        }

        lines = []
        total_cost = 0.0
        total_weight = 0.0
        for g in groups:
            scrap_type = g.get('scrap_type')
            if not scrap_type:
                continue
            weight = g.get('weight_kg') or 0.0
            cost = g.get('total_cost') or 0.0
            if weight <= 0:
                continue
            cost_per_kg = (cost / weight) if weight > 0 else 0.0
            product = (
                self.env['product.product'].browse(g['product_id'][0])
                if g.get('product_id') else False
            )
            lines.append({
                'scrap_type': scrap_type,
                'type_label': type_labels.get(scrap_type, scrap_type),
                'product_name': product.display_name if product else '',
                'product_default_code': (product.default_code or '') if product else '',
                'weight_kg': weight,
                'cost_per_kg': cost_per_kg,
                'total_cost': cost,
            })
            total_cost += cost
            total_weight += weight

        # Tri stable : Rebut avant Pâte, puis par produit pour un PDF prévisible
        type_order = {'scrap_recoverable': 0, 'paste_recoverable': 1}
        lines.sort(key=lambda l: (type_order.get(l['scrap_type'], 99), l['product_name']))
        return lines, total_cost, total_weight

    def _prepare_report_data(self):
        """Enrichit les données rapport avec emballages/films + récupérables."""
        result = super()._prepare_report_data()
        data = result['data']

        # Defaults communs : ces clés sont systématiquement présentes pour
        # éviter des t-if absents côté template.
        data.setdefault('compute_net_cost', self.compute_net_cost)

        # ============ consumption : MP + Emballages/Films (DÉFAUT) ============
        # Comportement "rapport de consommation globale" : pas de récupérables.
        if self.content_scope == 'consumption':
            packaging_lines, packaging_cost, packaging_qty = self._prepare_packaging_lines()
            gross_total = (data.get('grand_total_cost') or 0.0) + packaging_cost
            data.update({
                'content_scope': self.content_scope,
                'show_raw_material': True,
                'show_packaging': True,
                'show_recoverable': False,
                'packaging_lines': packaging_lines,
                'packaging_total_cost': packaging_cost,
                'packaging_total_qty': packaging_qty,
                'recoverable_lines': [],
                'recoverable_total_cost': 0.0,
                'recoverable_total_weight': 0.0,
                'gross_total_cost': gross_total,
                'combined_total_cost': gross_total,
                'net_total_cost': gross_total,
            })
            return result

        # ============ raw_material : MP seul ============
        if self.content_scope == 'raw_material':
            data.update({
                'content_scope': self.content_scope,
                'show_raw_material': True,
                'show_packaging': False,
                'show_recoverable': False,
                'packaging_lines': [],
                'packaging_total_cost': 0.0,
                'packaging_total_qty': 0.0,
                'recoverable_lines': [],
                'recoverable_total_cost': 0.0,
                'recoverable_total_weight': 0.0,
                'gross_total_cost': data.get('grand_total_cost') or 0.0,
                'combined_total_cost': data.get('grand_total_cost') or 0.0,
                'net_total_cost': data.get('grand_total_cost') or 0.0,
            })
            return result

        # ============ packaging_only : Emballages/Films seuls ============
        if self.content_scope == 'packaging_only':
            packaging_lines, packaging_cost, packaging_qty = self._prepare_packaging_lines()
            data.update({
                'lines': [],  # masque la section MP du template parent
                'grand_total_qty': 0.0,
                'grand_total_weight': 0.0,
                'grand_total_cost': 0.0,
                'line_count': 0,
                'content_scope': self.content_scope,
                'show_raw_material': False,
                'show_packaging': True,
                'show_recoverable': False,
                'packaging_lines': packaging_lines,
                'packaging_total_cost': packaging_cost,
                'packaging_total_qty': packaging_qty,
                'recoverable_lines': [],
                'recoverable_total_cost': 0.0,
                'recoverable_total_weight': 0.0,
                'gross_total_cost': packaging_cost,
                'combined_total_cost': packaging_cost,
                'net_total_cost': packaging_cost,
            })
            return result

        # ============ recoverables_only : Rebuts + Pâte seuls ============
        if self.content_scope == 'recoverables_only':
            recoverable_lines, recoverable_cost, recoverable_weight = (
                self._prepare_recoverable_lines()
            )
            data.update({
                'lines': [],
                'grand_total_qty': 0.0,
                'grand_total_weight': 0.0,
                'grand_total_cost': 0.0,
                'line_count': 0,
                'content_scope': self.content_scope,
                'show_raw_material': False,
                'show_packaging': False,
                'show_recoverable': True,
                'packaging_lines': [],
                'packaging_total_cost': 0.0,
                'packaging_total_qty': 0.0,
                'recoverable_lines': recoverable_lines,
                'recoverable_total_cost': recoverable_cost,
                'recoverable_total_weight': recoverable_weight,
                # En mode "récupérables seuls", l'idée même de "coût net" ne
                # s'applique pas → on expose la valeur des récupérables comme
                # total brut/combiné/net pour cohérence template.
                'gross_total_cost': recoverable_cost,
                'combined_total_cost': recoverable_cost,
                'net_total_cost': recoverable_cost,
            })
            return result

        # ============ all : MP + Emballages/Films + Récupérables ============
        packaging_lines, packaging_cost, packaging_qty = self._prepare_packaging_lines()
        recoverable_lines, recoverable_cost, recoverable_weight = (
            self._prepare_recoverable_lines()
        )
        gross_total = (data.get('grand_total_cost') or 0.0) + packaging_cost
        # combined_total_cost = total brut (compatibilité avec ancien template
        # qui n'avait pas la notion de récupérable) ;
        # net_total_cost = brut - récupérables si l'option est cochée.
        net_total = (gross_total - recoverable_cost) if self.compute_net_cost else gross_total
        data.update({
            'content_scope': self.content_scope,
            'show_raw_material': True,
            'show_packaging': True,
            'show_recoverable': True,
            'packaging_lines': packaging_lines,
            'packaging_total_cost': packaging_cost,
            'packaging_total_qty': packaging_qty,
            'recoverable_lines': recoverable_lines,
            'recoverable_total_cost': recoverable_cost,
            'recoverable_total_weight': recoverable_weight,
            'gross_total_cost': gross_total,
            'combined_total_cost': gross_total,
            'net_total_cost': net_total,
        })
        return result

    def action_open_analysis(self):
        """Ouvre l'analyse pré-filtrée avec un groupement adapté au scope choisi.

        Le module de base ne regroupe que par produit. Ici on tient compte
        des nouvelles dimensions (catégorie / sous-type) :
            - all                → catégorie + produit + mois
            - raw_material       → produit + mois (comme le base)
            - packaging_only     → catégorie + sous-type
            - recoverables_only  → catégorie + sous-type
        """
        action = super().action_open_analysis()

        if self.content_scope in ('consumption', 'all'):
            action['context'] = {
                'search_default_group_consumption_category': 1,
                'search_default_group_product': 1,
                'search_default_group_month': 1,
            }
        elif self.content_scope in ('packaging_only', 'recoverables_only'):
            action['context'] = {
                'search_default_group_consumption_category': 1,
                'search_default_group_consumption_subtype': 1,
                'search_default_group_month': 1,
            }
        # 'raw_material' garde le contexte fixé par le wizard parent
        # (search_default_group_product=1) — comportement historique.

        return action
