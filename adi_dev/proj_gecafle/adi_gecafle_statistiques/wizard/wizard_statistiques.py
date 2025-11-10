# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import base64
import xlsxwriter
import io
from odoo.exceptions import UserError


class WizardGecafleStatistiques(models.TransientModel):
    _name = 'wizard.gecafle.statistiques'
    _description = 'Assistant de génération de rapports statistiques'

    # Champs de période
    date_debut = fields.Date(
        string="Date début",
        default=lambda self: fields.Date.today().replace(day=1),
        required=True
    )

    date_fin = fields.Date(
        string="Date fin",
        default=fields.Date.today,
        required=True
    )

    type_periode = fields.Selection([
        ('jour', 'Journalier'),
        ('semaine', 'Hebdomadaire'),
        ('mois', 'Mensuel'),
        ('trimestre', 'Trimestriel'),
        ('annee', 'Annuel'),
        ('personnalise', 'Personnalisé')
    ], string="Type de période", default='mois')

    # Filtres
    producteur_ids = fields.Many2many(
        'gecafle.producteur',
        string="Producteurs"
    )

    produit_ids = fields.Many2many(
        'gecafle.produit',
        string="Produits"
    )

    client_ids = fields.Many2many(
        'gecafle.client',
        string="Clients"
    )

    region_ids = fields.Many2many(
        'gecafle.region',
        string="Régions"
    )

    # Options du rapport
    type_rapport = fields.Selection([
        ('synthese', 'Rapport de synthèse'),
        ('detaille', 'Rapport détaillé'),
        ('comparatif', 'Rapport comparatif'),
        ('evolution', 'Évolution temporelle')
    ], string="Type de rapport", default='synthese', required=True)

    grouper_par = fields.Selection([
        ('produit', 'Par produit'),
        ('producteur', 'Par producteur'),
        ('client', 'Par client'),
        ('region', 'Par région'),
        ('date', 'Par date')
    ], string="Grouper par", default='produit')

    inclure_graphiques = fields.Boolean(
        string="Inclure graphiques",
        default=True
    )

    inclure_details = fields.Boolean(
        string="Inclure détails",
        default=False
    )

    format_export = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('html', 'HTML')
    ], string="Format d'export", default='pdf')

    envoyer_par_email = fields.Boolean(
        string="Envoyer par email",
        default=False
    )

    email_destinataire = fields.Char(
        string="Email destinataire"
    )

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for record in self:
            if record.date_debut > record.date_fin:
                raise UserError(_("La date de début doit être antérieure à la date de fin."))

    @api.onchange('type_periode')
    def _onchange_type_periode(self):
        """Ajuste automatiquement les dates selon le type de période"""
        if self.type_periode == 'jour':
            self.date_debut = fields.Date.today()
            self.date_fin = fields.Date.today()
        elif self.type_periode == 'semaine':
            today = fields.Date.today()
            self.date_debut = today - timedelta(days=today.weekday())
            self.date_fin = self.date_debut + timedelta(days=6)
        elif self.type_periode == 'mois':
            today = fields.Date.today()
            self.date_debut = today.replace(day=1)
            next_month = today.replace(day=28) + timedelta(days=4)
            self.date_fin = next_month - timedelta(days=next_month.day)
        elif self.type_periode == 'trimestre':
            today = fields.Date.today()
            quarter = (today.month - 1) // 3
            self.date_debut = datetime(today.year, quarter * 3 + 1, 1).date()
            if quarter == 3:
                self.date_fin = datetime(today.year, 12, 31).date()
            else:
                self.date_fin = datetime(today.year, (quarter + 1) * 3 + 1, 1).date() - timedelta(days=1)
        elif self.type_periode == 'annee':
            today = fields.Date.today()
            self.date_debut = datetime(today.year, 1, 1).date()
            self.date_fin = datetime(today.year, 12, 31).date()

    def action_generer_rapport(self):
        """Génère le rapport selon les paramètres"""
        self.ensure_one()

        # Construire le domaine de recherche
        domain = [
            ('date_vente', '>=', self.date_debut),
            ('date_vente', '<=', self.date_fin)
        ]

        if self.producteur_ids:
            domain.append(('producteur_id', 'in', self.producteur_ids.ids))
        if self.produit_ids:
            domain.append(('produit_id', 'in', self.produit_ids.ids))
        if self.client_ids:
            domain.append(('client_id', 'in', self.client_ids.ids))
        if self.region_ids:
            domain.append(('region_id', 'in', self.region_ids.ids))

        # Récupérer les données
        stats = self.env['gecafle.statistiques.ventes'].search(domain)

        if not stats:
            raise UserError(_("Aucune donnée trouvée pour les critères sélectionnés."))

        # Générer selon le format
        if self.format_export == 'excel':
            return self._generer_excel(stats)
        else:
            return self._generer_pdf(stats)

    def _generer_pdf(self, stats):
        """Génère le rapport PDF"""
        # Préparer les données pour le rapport
        data = {
            'wizard_id': self.id,
            'date_debut': self.date_debut,
            'date_fin': self.date_fin,
            'type_rapport': self.type_rapport,
            'grouper_par': self.grouper_par,
            'inclure_graphiques': self.inclure_graphiques,
            'inclure_details': self.inclure_details,
            'stats_ids': stats.ids,
        }

        # Retourner l'action du rapport
        return self.env.ref('adi_gecafle_statistiques.action_report_statistiques').report_action(self, data=data)

    def action_exporter_excel(self):
        """Exporte les statistiques en Excel"""
        self.ensure_one()

        # Construire le domaine
        domain = [
            ('date_vente', '>=', self.date_debut),
            ('date_vente', '<=', self.date_fin)
        ]

        if self.producteur_ids:
            domain.append(('producteur_id', 'in', self.producteur_ids.ids))
        if self.produit_ids:
            domain.append(('produit_id', 'in', self.produit_ids.ids))

        stats = self.env['gecafle.statistiques.ventes'].search(domain)

        if not stats:
            raise UserError(_("Aucune donnée à exporter."))

        return self._generer_excel(stats)

    def _generer_excel(self, stats):
        """Génère un fichier Excel avec les statistiques"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Feuille de synthèse
        worksheet = workbook.add_worksheet('Synthèse')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        # En-têtes
        headers = ['Date', 'Producteur', 'Produit', 'Qualité', 'Client',
                   'Nb Colis', 'Poids (kg)', 'Montant', 'Commission']

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Données
        row = 1
        for stat in stats:
            worksheet.write(row, 0, str(stat.date_vente))
            worksheet.write(row, 1, stat.producteur_id.name if stat.producteur_id else '')
            worksheet.write(row, 2, stat.produit_id.name if stat.produit_id else '')
            worksheet.write(row, 3, stat.qualite_id.name if stat.qualite_id else '')
            worksheet.write(row, 4, stat.client_id.name if stat.client_id else '')
            worksheet.write(row, 5, stat.nombre_colis)
            worksheet.write(row, 6, stat.poids_total)
            worksheet.write(row, 7, stat.montant_total)
            worksheet.write(row, 8, stat.montant_commission)
            row += 1

        workbook.close()
        output.seek(0)

        # Créer l'attachement
        attachment = self.env['ir.attachment'].create({
            'name': f'Statistiques_{self.date_debut}_{self.date_fin}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
