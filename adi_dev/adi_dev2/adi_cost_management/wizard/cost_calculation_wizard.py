# -*- coding: utf-8 -*-
# Part of ADI Cost Management Module
# Copyright (C) 2024 ADICOPS (<https://adicops-dz.com>)

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging
import xlsxwriter
import io
import base64

_logger = logging.getLogger(__name__)


class AdiCostCalculationWizard(models.TransientModel):
    """
    Assistant de calcul des coûts de production.

    Ce wizard permet de :
    - Calculer les coûts pour une période donnée
    - Filtrer par produits, catégories ou états
    - Lancer des calculs en masse
    - Générer des rapports d'analyse
    - Exporter les données en Excel
    """

    _name = 'adi.cost.calculation.wizard'
    _description = 'Assistant de Calcul des Coûts de Production'

    # ================== PÉRIODE ==================

    date_from = fields.Date(
        'Date Début',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help="Date de début de la période à analyser"
    )

    date_to = fields.Date(
        'Date Fin',
        required=True,
        default=fields.Date.today,
        help="Date de fin de la période à analyser"
    )

    period_type = fields.Selection([
        ('custom', 'Personnalisé'),
        ('today', "Aujourd'hui"),
        ('week', 'Cette Semaine'),
        ('month', 'Ce Mois'),
        ('quarter', 'Ce Trimestre'),
        ('year', 'Cette Année'),
        ('last_month', 'Mois Dernier'),
        ('last_quarter', 'Trimestre Dernier'),
        ('last_year', 'Année Dernière')
    ],
        'Type de Période',
        default='month',
        help="Sélection rapide de période prédéfinie"
    )

    # ================== FILTRES ==================

    product_ids = fields.Many2many(
        'product.product',
        'wizard_product_rel',
        'wizard_id',
        'product_id',
        string='Produits',
        domain="[('type', '=', 'product')]",
        help="Laisser vide pour tous les produits"
    )

    product_category_ids = fields.Many2many(
        'product.category',
        'wizard_category_rel',
        'wizard_id',
        'category_id',
        string='Catégories de Produits',
        help="Filtrer par catégories de produits"
    )

    state_filter = fields.Selection([
        ('all', 'Tous'),
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé')
    ],
        'État des Productions',
        default='all',
        help="Filtrer par état des productions"
    )

    include_scraps = fields.Boolean(
        'Inclure les Rebuts',
        default=True,
        help="Inclure l'impact des rebuts dans le calcul"
    )

    scrap_type_filter = fields.Selection([
        ('all', 'Tous'),
        ('finished', 'Produits Finis'),
        ('packaging', 'Emballages'),
        ('raw', 'Matières Premières')
    ],
        'Type de Rebuts',
        default='all',
        help="Filtrer par type de rebuts"
    )

    # ================== OPTIONS DE CALCUL ==================

    calculation_method = fields.Selection([
        ('daily', 'Par Jour'),
        ('weekly', 'Par Semaine'),
        ('monthly', 'Par Mois'),
        ('global', 'Global')
    ],
        'Méthode de Calcul',
        default='daily',
        required=True,
        help="Granularité du calcul des coûts"
    )

    update_product_cost = fields.Boolean(
        'Mettre à Jour les Prix de Revient',
        default=False,
        help="Mettre à jour automatiquement les prix de revient des produits"
    )

    create_missing_records = fields.Boolean(
        'Créer les Enregistrements Manquants',
        default=True,
        help="Créer automatiquement les productions journalières manquantes"
    )

    # ================== OPTIONS DE RAPPORT ==================

    generate_report = fields.Boolean(
        'Générer un Rapport',
        default=True,
        help="Générer un rapport détaillé après le calcul"
    )

    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('both', 'PDF et Excel')
    ],
        'Format du Rapport',
        default='pdf'
    )

    send_by_email = fields.Boolean(
        'Envoyer par Email',
        default=False,
        help="Envoyer le rapport par email après génération"
    )

    email_recipients = fields.Char(
        'Destinataires Email',
        help="Adresses email séparées par des virgules"
    )

    # ================== RÉSULTATS ==================

    result_count = fields.Integer(
        'Nombre de Productions',
        readonly=True,
        help="Nombre de productions trouvées"
    )

    result_message = fields.Text(
        'Résultat du Calcul',
        readonly=True
    )

    # ================== MÉTHODES ONCHANGE ==================

    @api.onchange('period_type')
    def _onchange_period_type(self):
        """Ajuster les dates selon le type de période sélectionné"""
        today = fields.Date.today()

        if self.period_type == 'today':
            self.date_from = self.date_to = today

        elif self.period_type == 'week':
            # Début de semaine (lundi)
            start_week = today - timedelta(days=today.weekday())
            self.date_from = start_week
            self.date_to = today

        elif self.period_type == 'month':
            self.date_from = today.replace(day=1)
            self.date_to = today

        elif self.period_type == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            self.date_from = today.replace(month=quarter_month, day=1)
            self.date_to = today

        elif self.period_type == 'year':
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today

        elif self.period_type == 'last_month':
            first_day_current = today.replace(day=1)
            last_day_previous = first_day_current - timedelta(days=1)
            self.date_from = last_day_previous.replace(day=1)
            self.date_to = last_day_previous

        elif self.period_type == 'last_quarter':
            current_quarter = ((today.month - 1) // 3)
            if current_quarter == 0:
                # Dernier trimestre de l'année précédente
                year = today.year - 1
                self.date_from = date(year, 10, 1)
                self.date_to = date(year, 12, 31)
            else:
                quarter_month = (current_quarter - 1) * 3 + 1
                self.date_from = today.replace(month=quarter_month, day=1)
                # Dernier jour du trimestre
                last_month = quarter_month + 2
                if last_month == 12:
                    self.date_to = today.replace(month=12, day=31)
                else:
                    next_quarter = today.replace(month=last_month + 1, day=1)
                    self.date_to = next_quarter - timedelta(days=1)

        elif self.period_type == 'last_year':
            self.date_from = date(today.year - 1, 1, 1)
            self.date_to = date(today.year - 1, 12, 31)

    @api.onchange('product_category_ids')
    def _onchange_product_category_ids(self):
        """Filtrer les produits selon les catégories sélectionnées"""
        if self.product_category_ids:
            # Récupérer tous les produits des catégories sélectionnées
            products = self.env['product.product'].search([
                ('categ_id', 'child_of', self.product_category_ids.ids),
                ('type', '=', 'product')
            ])
            return {
                'domain': {
                    'product_ids': [('id', 'in', products.ids)]
                }
            }

    # ================== MÉTHODES PRINCIPALES ==================

    def action_calculate(self):
        """Lance le calcul des coûts pour la période sélectionnée"""
        self.ensure_one()

        # Validation des dates
        if self.date_from > self.date_to:
            raise ValidationError(_('La date de début doit être antérieure à la date de fin.'))

        # Construction du domaine de recherche
        domain = [
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to)
        ]

        # Filtre par produits
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        elif self.product_category_ids:
            products = self.env['product.product'].search([
                ('categ_id', 'child_of', self.product_category_ids.ids),
                ('type', '=', 'product')
            ])
            domain.append(('product_id', 'in', products.ids))

        # Filtre par état
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        # Recherche des productions
        productions = self.env['adi.daily.production'].search(domain)
        self.result_count = len(productions)

        if not productions and self.create_missing_records:
            # Créer les enregistrements manquants
            productions = self._create_missing_productions()

        # Calcul pour chaque production
        results = {
            'total_cost': 0,
            'total_scrap': 0,
            'total_qty': 0,
            'updated': 0,
            'errors': []
        }

        for production in productions:
            try:
                # Recalcul des coûts
                production.action_calculate_cost()

                # Mise à jour des totaux
                results['total_cost'] += production.total_cost_with_scrap
                results['total_scrap'] += production.total_scrap_cost
                results['total_qty'] += production.qty_good

                # Mise à jour du prix de revient si demandé
                if self.update_product_cost and production.state == 'validated':
                    if production.unit_cost_real > 0:
                        production.product_id.sudo().standard_price = production.unit_cost_real
                        results['updated'] += 1

            except Exception as e:
                _logger.error(f"Erreur lors du calcul pour {production.name}: {str(e)}")
                results['errors'].append(f"{production.name}: {str(e)}")

        # Génération du message de résultat
        self.result_message = self._generate_result_message(results)

        # Génération des rapports si demandé
        if self.generate_report:
            return self._generate_reports(productions)

        # Ouverture de la vue d'analyse
        return self._open_analysis_view()

    def _create_missing_productions(self):
        """Créer les productions journalières manquantes"""
        productions = self.env['adi.daily.production']

        # Recherche des OF terminés dans la période
        mrp_domain = [
            ('date_finished', '>=', self.date_from),
            ('date_finished', '<=', self.date_to),
            ('state', '=', 'done')
        ]

        if self.product_ids:
            mrp_domain.append(('product_id', 'in', self.product_ids.ids))

        mrp_orders = self.env['mrp.production'].search(mrp_domain)

        # Grouper par jour et produit
        grouped_orders = {}
        for order in mrp_orders:
            date_key = order.date_finished.date()
            product_key = order.product_id.id

            if date_key not in grouped_orders:
                grouped_orders[date_key] = {}
            if product_key not in grouped_orders[date_key]:
                grouped_orders[date_key][product_key] = []

            grouped_orders[date_key][product_key].append(order)

        # Créer les productions journalières
        for date_key, products in grouped_orders.items():
            for product_id, orders in products.items():
                # Vérifier si la production existe déjà
                existing = self.env['adi.daily.production'].search([
                    ('production_date', '=', date_key),
                    ('product_id', '=', product_id)
                ], limit=1)

                if not existing:
                    # Créer la nouvelle production
                    vals = {
                        'production_date': date_key,
                        'product_id': product_id,
                        'production_ids': [(6, 0, orders.ids)],
                        'state': 'draft'
                    }
                    production = self.env['adi.daily.production'].create(vals)
                    productions |= production

                    _logger.info(f"Production créée: {production.name}")

        return productions

    def _generate_result_message(self, results):
        """Générer le message de résultat du calcul"""
        lines = [
            f"=== RÉSULTATS DU CALCUL ===",
            f"Période : {self.date_from} au {self.date_to}",
            f"Productions traitées : {self.result_count}",
            f"",
            f"📊 TOTAUX:",
            f"• Quantité produite : {results['total_qty']:.2f} unités",
            f"• Coût total : {results['total_cost']:,.2f} DA",
            f"• Coût des rebuts : {results['total_scrap']:,.2f} DA"
        ]

        if results['total_qty'] > 0:
            avg_cost = results['total_cost'] / results['total_qty']
            lines.append(f"• Coût moyen/unité : {avg_cost:.2f} DA")

        if results['updated'] > 0:
            lines.append(f"")
            lines.append(f"✅ {results['updated']} prix de revient mis à jour")

        if results['errors']:
            lines.append(f"")
            lines.append(f"⚠️ ERREURS:")
            for error in results['errors'][:5]:  # Limiter à 5 erreurs
                lines.append(f"  • {error}")
            if len(results['errors']) > 5:
                lines.append(f"  ... et {len(results['errors']) - 5} autres erreurs")

        return "\n".join(lines)

    def _generate_reports(self, productions):
        """Générer les rapports demandés"""
        if self.report_format in ['pdf', 'both']:
            # Génération du rapport PDF avec le bon nom de template
            return {
                'type': 'ir.actions.report',
                'report_name': 'adi_cost_management.report_cost_analysis_document',
                'report_type': 'qweb-pdf',
                'data': None,
                'docids': productions.ids,
                'context': {
                    'active_model': 'adi.daily.production',
                    'active_ids': productions.ids,
                }
            }

        if self.report_format in ['excel', 'both']:
            # Génération du rapport Excel
            return self._generate_excel_report(productions)

        return self._open_analysis_view()

    def _generate_excel_report(self, productions):
        """Générer un rapport Excel détaillé"""
        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B8BBE',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'align': 'center',
            'border': 1
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00 DA',
            'align': 'right',
            'border': 1
        })

        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'align': 'center',
            'border': 1
        })

        # Feuille principale
        sheet = workbook.add_worksheet('Analyse des Coûts')
        sheet.set_column('A:A', 12)  # Date
        sheet.set_column('B:B', 15)  # Référence
        sheet.set_column('C:C', 30)  # Produit
        sheet.set_column('D:F', 15)  # Quantités
        sheet.set_column('G:K', 18)  # Coûts

        # En-têtes
        headers = [
            'Date', 'Référence', 'Produit',
            'Qté Produite', 'Qté Rebuts', 'Qté Bonne',
            'Coût Production', 'Coût Rebuts', 'Coût Total',
            'P.R. Théorique', 'P.R. Réel', 'Taux Rebut'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Données
        row = 1
        total_qty = 0
        total_cost = 0
        total_scrap = 0

        for prod in productions:
            # Calcul des rebuts
            scrap_qty = sum(
                s.qty_units for s in prod.scrap_ids
                if s.scrap_type == 'finished'
            )
            scrap_rate = (scrap_qty / prod.qty_produced * 100) if prod.qty_produced else 0

            sheet.write(row, 0, prod.production_date, date_format)
            sheet.write(row, 1, prod.name)
            sheet.write(row, 2, prod.product_id.name)
            sheet.write(row, 3, prod.qty_produced)
            sheet.write(row, 4, scrap_qty)
            sheet.write(row, 5, prod.qty_good)
            sheet.write(row, 6, prod.total_production_cost, money_format)
            sheet.write(row, 7, prod.total_scrap_cost, money_format)
            sheet.write(row, 8, prod.total_cost_with_scrap, money_format)
            sheet.write(row, 9, prod.unit_cost_theoretical, money_format)
            sheet.write(row, 10, prod.unit_cost_real, money_format)
            sheet.write(row, 11, scrap_rate / 100, percent_format)

            total_qty += prod.qty_good
            total_cost += prod.total_cost_with_scrap
            total_scrap += prod.total_scrap_cost

            row += 1

        # Totaux
        row += 1
        sheet.write(row, 2, 'TOTAUX', header_format)
        sheet.write(row, 5, total_qty, header_format)
        sheet.write(row, 7, total_scrap, money_format)
        sheet.write(row, 8, total_cost, money_format)

        # Feuille des rebuts détaillés
        if self.include_scraps:
            scrap_sheet = workbook.add_worksheet('Détail Rebuts')

            # En-têtes rebuts
            scrap_headers = [
                'Date', 'Type', 'Produit', 'Quantité (kg)',
                'Coût/kg', 'Coût Total', 'Raison'
            ]

            for col, header in enumerate(scrap_headers):
                scrap_sheet.write(0, col, header, header_format)

            # Données rebuts
            scrap_row = 1
            for prod in productions:
                for scrap in prod.scrap_ids:
                    scrap_sheet.write(scrap_row, 0, scrap.scrap_date, date_format)
                    scrap_sheet.write(scrap_row, 1, dict(scrap._fields['scrap_type'].selection).get(scrap.scrap_type))
                    scrap_sheet.write(scrap_row, 2, scrap.product_id.name)
                    scrap_sheet.write(scrap_row, 3, scrap.qty_kg)
                    scrap_sheet.write(scrap_row, 4, scrap.cost_per_kg, money_format)
                    scrap_sheet.write(scrap_row, 5, scrap.total_cost, money_format)
                    scrap_sheet.write(scrap_row, 6, scrap.reason or '')
                    scrap_row += 1

        # Graphique (si possible)
        try:
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name': 'Coût de Production',
                'categories': f'=Analyse des Coûts!$A$2:$A${row - 1}',
                'values': f'=Analyse des Coûts!$G$2:$G${row - 1}',
            })
            chart.set_title({'name': 'Évolution des Coûts de Production'})
            chart.set_x_axis({'name': 'Date'})
            chart.set_y_axis({'name': 'Coût (DA)'})
            sheet.insert_chart('N2', chart)
        except:
            pass  # Si le graphique échoue, continuer sans

        workbook.close()
        output.seek(0)

        # Créer l'attachement
        attachment = self.env['ir.attachment'].create({
            'name': f'Analyse_Couts_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Envoyer par email si demandé
        if self.send_by_email and self.email_recipients:
            self._send_report_by_email(attachment)

        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _send_report_by_email(self, attachment):
        """Envoyer le rapport par email"""
        template = self.env.ref('adi_cost_management.email_template_cost_report', False)

        if not template:
            # Créer un template simple si inexistant
            template_vals = {
                'name': 'Rapport Analyse des Coûts',
                'model_id': self.env['ir.model'].search([('model', '=', 'adi.cost.calculation.wizard')], limit=1).id,
                'subject': f"Rapport d'Analyse des Coûts - {self.date_from} au {self.date_to}",
                'body_html': """
                    <p>Bonjour,</p>
                    <p>Veuillez trouver ci-joint le rapport d'analyse des coûts pour la période du ${object.date_from} au ${object.date_to}.</p>
                    <p>Cordialement,<br/>
                    ${user.name}</p>
                """,
                'email_to': self.email_recipients,
                'attachment_ids': [(4, attachment.id)]
            }
            template = self.env['mail.template'].create(template_vals)
        else:
            template.attachment_ids = [(4, attachment.id)]

        template.send_mail(self.id, force_send=True)

        self.env['mail.mail'].sudo().search([
            ('model', '=', self._name),
            ('res_id', '=', self.id)
        ]).send()

    def _open_analysis_view(self):
        """Ouvrir la vue d'analyse après le calcul"""
        domain = [
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to)
        ]

        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        return {
            'type': 'ir.actions.act_window',
            'name': f'Analyse des Coûts ({self.date_from} - {self.date_to})',
            'res_model': 'adi.cost.analysis',
            'view_mode': 'pivot,graph,tree',
            'domain': domain,
            'context': {
                'search_default_group_product': 1,
                'pivot_measures': ['qty_produced', 'qty_good', 'total_cost', 'unit_cost_real'],
                'pivot_row_groupby': ['product_id'],
                'pivot_column_groupby': ['production_date:month'],
            }
        }

    # ================== MÉTHODES UTILITAIRES ==================

    @api.model
    def action_open_scheduled_calculation(self):
        """Action pour ouvrir le wizard depuis une action planifiée"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Calcul Automatique des Coûts',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_period_type': 'today',
                'default_update_product_cost': True,
                'default_generate_report': False
            }
        }

    @api.model
    def cron_calculate_daily_costs(self):
        """Méthode pour le calcul automatique journalier (cron)"""
        wizard = self.create({
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
            'update_product_cost': True,
            'generate_report': False,
            'create_missing_records': True
        })

        wizard.action_calculate()

        _logger.info(f"Calcul automatique des coûts effectué pour le {fields.Date.today()}")
