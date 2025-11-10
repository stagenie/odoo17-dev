# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GecafleRecapPrintWizard(models.TransientModel):
    _name = 'gecafle.recap.print.wizard'
    _description = "Assistant d'impression avec tri et regroupement"

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True
    )

    # Options de tri
    sort_by = fields.Selection([
        ('default', 'Par défaut'),
        ('quality_asc', 'Qualité (meilleure → moins bonne)'),
        ('quality_desc', 'Qualité (moins bonne → meilleure)'),
        ('price_asc', 'Prix unitaire (croissant)'),
        ('price_desc', 'Prix unitaire (décroissant)'),
        ('product', 'Produit (alphabétique)'),
        ('weight', 'Poids net (décroissant)'),
    ], string="Trier par", default='quality_asc', required=True)

    # Options de regroupement
    group_by = fields.Selection([
        ('none', 'Aucun regroupement'),
        ('product', 'Par produit'),
        ('quality', 'Par qualité'),
        ('price', 'Par tranche de prix'),
        ('type_colis', 'Par type de colis'),
    ], string="Regrouper par", default='none', required=True)

    # Options d'affichage
    show_commission_pct = fields.Boolean(
        string="Afficher % commission",
        default=True
    )

    show_subtotals = fields.Boolean(
        string="Afficher sous-totaux",
        default=True,
        help="Affiche les sous-totaux par groupe"
    )

    show_details = fields.Boolean(
        string="Afficher détails ventes",
        default=False
    )

    report_type = fields.Selection([
        ('simple', 'Bordereau simple'),
        ('with_commission', 'Bordereau avec commissions'),
        ('sale_details', 'Détails des ventes'),
        ('sale_details_commission', 'Détails avec commissions'),
    ], string="Type de rapport", default='simple', required=True)

    @api.onchange('group_by')
    def _onchange_group_by(self):
        """Active automatiquement les sous-totaux si regroupement"""
        if self.group_by != 'none':
            self.show_subtotals = True

    def _get_sorted_lines(self):
        """Retourne les lignes triées selon l'option sélectionnée"""
        lines = self.recap_id.recap_line_ids

        if self.sort_by == 'quality_asc':
            # Tri par classification de qualité (1=meilleur)
            lines = lines.sorted(key=lambda l: (
                l.qualite_id.classification if l.qualite_id and l.qualite_id.classification else 999,
                l.produit_id.name if l.produit_id else ''
            ))
        elif self.sort_by == 'quality_desc':
            # Tri inverse par qualité
            lines = lines.sorted(key=lambda l: (
                -(l.qualite_id.classification if l.qualite_id and l.qualite_id.classification else -999),
                l.produit_id.name if l.produit_id else ''
            ))
        elif self.sort_by == 'price_asc':
            # Tri par prix unitaire croissant
            lines = lines.sorted(key=lambda l: l.prix_unitaire)
        elif self.sort_by == 'price_desc':
            # Tri par prix unitaire décroissant
            lines = lines.sorted(key=lambda l: -l.prix_unitaire)
        elif self.sort_by == 'product':
            # Tri alphabétique par produit
            lines = lines.sorted(key=lambda l: l.produit_id.name if l.produit_id else '')
        elif self.sort_by == 'weight':
            # Tri par poids net décroissant
            lines = lines.sorted(key=lambda l: -l.poids_net)

        return lines

    def _get_grouped_lines(self):
        """Retourne les lignes regroupées selon l'option sélectionnée"""
        lines = self._get_sorted_lines()

        if self.group_by == 'none':
            return [('', lines)]

        grouped = {}

        for line in lines:
            if self.group_by == 'product':
                key = line.produit_id.name if line.produit_id else 'Sans produit'
            elif self.group_by == 'quality':
                key = line.qualite_id.name if line.qualite_id else 'Sans qualité'
            elif self.group_by == 'price':
                # Regroupement par tranches de prix
                prix = line.prix_unitaire
                if prix < 50:
                    key = '0-50 DA'
                elif prix < 100:
                    key = '50-100 DA'
                elif prix < 200:
                    key = '100-200 DA'
                else:
                    key = '200+ DA'
            elif self.group_by == 'type_colis':
                key = line.type_colis_id.name if line.type_colis_id else 'Sans emballage'
            else:
                key = ''

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(line)

        # Trier les clés pour un affichage cohérent
        sorted_groups = sorted(grouped.items())
        return sorted_groups

    def action_print_report(self):
        """Lance l'impression avec les options sélectionnées"""
        self.ensure_one()

        if self.recap_id.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant impression."))

        # Préparer les données pour le rapport
        grouped_lines = self._get_grouped_lines()

        # Déterminer le nom du rapport selon le type
        report_name = {
            'simple': 'adi_gecafle_ventes.report_reception_recap_wizard',
            'with_commission': 'adi_gecafle_ventes.report_reception_recap_commission_wizard',
            'sale_details': 'adi_gecafle_ventes.report_reception_sale_details_wizard',
            'sale_details_commission': 'adi_gecafle_ventes.report_reception_sale_details_commission_wizard',
        }.get(self.report_type, 'adi_gecafle_ventes.report_reception_recap_wizard')

        # Passer les données au contexte
        return self.env.ref(report_name).report_action(
            self.recap_id,
            data={
                'grouped_lines': grouped_lines,
                'show_commission_pct': self.show_commission_pct,
                'show_subtotals': self.show_subtotals,
                'group_by': self.group_by,
                'sort_by': self.sort_by,
                'wizard_id': self.id,
            }
        )

    def action_preview(self):
        """Prévisualise le rapport avant impression"""
        return self.action_print_report()
