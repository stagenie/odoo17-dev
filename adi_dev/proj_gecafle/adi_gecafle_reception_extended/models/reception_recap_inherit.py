# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class GecafleReceptionRecapExtended(models.Model):
    _inherit = 'gecafle.reception.recap'

    # Champs existants
    observation = fields.Text(
        string="Observations",
        help="Notes et observations concernant ce récapitulatif"
    )

    # Champs pour transport et emballages - SIMPLIFIÉS
    transport = fields.Monetary(
        string="Transport",
        currency_field='currency_id',
        compute='_compute_financial_details',
        store=True,
        help="Frais de transport depuis la réception"
    )

    montant_total_emballage_achete = fields.Monetary(
        string="Total Emballages Achetés",
        currency_field='currency_id',
        compute='_compute_financial_details',
        store=True,
        help="Montant des emballages achetés depuis la réception"
    )

    avance_producteur = fields.Monetary(
        string="Avance Producteur",
        currency_field='currency_id',
        compute='_compute_financial_details',
        store=True,
        help="Avance producteur depuis la réception"
    )
    # NOUVEAU : Ajout du paiement emballage
    paiement_emballage = fields.Monetary(
        string="Paiement Emballage",
        currency_field='currency_id',
        compute='_compute_financial_details',
        store=True,
        help="Paiement emballage depuis la réception"
    )

    # Nouveau champ calculé pour net à payer
    net_a_payer = fields.Monetary(
        string="Net à Payer",
        currency_field='currency_id',
        compute='_compute_net_a_payer',
        store=True
    )


    # Champ pour les destockages
    destockage_line_ids = fields.One2many(
        'gecafle.destockage',
        compute='_compute_destockage_lines',
        string="Produits destockés"
    )

    has_destockage = fields.Boolean(
        string="A des produits destockés",
        compute='_compute_destockage_lines',
        store=True
    )

    def action_open_print_wizard(self):
        """Ouvre le wizard d'impression avec options"""
        self.ensure_one()

        return {
            'name': _('Options d\'impression du bordereau'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.bordereau.print.wizard',
            'target': 'new',
            'context': {
                'default_recap_id': self.id,
            }
        }

    @api.depends('reception_id')
    def _compute_destockage_lines(self):
        """Récupère les lignes de destockage liées à cette réception"""
        for record in self:
            if record.reception_id:
                destockages = self.env['gecafle.destockage'].search([
                    ('reception_id', '=', record.reception_id.id)
                ])
                record.destockage_line_ids = destockages
                record.has_destockage = bool(destockages)
            else:
                record.destockage_line_ids = False
                record.has_destockage = False

    def action_create_vendor_invoice(self):
        """Override pour inclure transport et emballages dans la facture"""
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant de créer une facture."))

        if self.invoice_id:
            raise UserError(_("Une facture existe déjà pour ce récapitulatif."))

        # Créer ou trouver le partner
        vendor = self._get_or_create_partner()

        # Préparer les lignes de facture
        invoice_lines = []

        # Ligne 1 : Total des ventes
        invoice_lines.append((0, 0, {
            'name': _("Vente de produits agricoles - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': self.total_ventes,
        }))

        # Ligne 2 : Commission (négatif)
        invoice_lines.append((0, 0, {
            'name': _("Commission sur ventes (-%s%%)") % (self.producteur_id.fruit_margin if self.producteur_id else 0),
            'quantity': 1,
            'price_unit': -self.total_commission,
        }))

        # Ligne 3 : Transport (négatif si existe)
        if self.transport > 0:
            invoice_lines.append((0, 0, {
                'name': _("Frais de transport"),
                'quantity': 1,
                'price_unit': -self.transport,
            }))

        # Ligne 4 : Emballages achetés (positif si existe)
        if self.montant_total_emballage_achete > 0:
            invoice_lines.append((0, 0, {
                'name': _("Emballages achetés au producteur"),
                'quantity': 1,
                'price_unit': self.montant_total_emballage_achete,
            }))

        # Ligne 5 : Avance (négatif si existe)
        if self.avance_producteur > 0:
            invoice_lines.append((0, 0, {
                'name': _("Avance producteur sur réception"),
                'quantity': 1,
                'price_unit': -self.avance_producteur,
            }))

        # Calcul du net à payer
        net_a_payer = (self.total_ventes
                       - self.total_commission
                       - self.transport
                       - self.avance_producteur
                       + self.montant_total_emballage_achete)

        # Créer la facture
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': _("Bordereau N° %s - Folio %s") % (self.name,
                                                                 self.reception_id.name if self.reception_id else ''),
            'ref': _("Bordereau N° %s") % self.name,
            'recap_id': self.id,
            'invoice_line_ids': invoice_lines,
            'narration': _("""
                Récapitulatif %s
                ================
                Total ventes: %s
                Commission: -%s
                Transport: -%s
                Emballages achetés: +%s
                Avance: -%s
                ----------------
                Net à payer: %s
            """) % (
                self.name,
                self.total_ventes,
                self.total_commission,
                self.transport or 0,
                self.montant_total_emballage_achete or 0,
                self.avance_producteur or 0,
                net_a_payer
            )
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        self.state = 'facture'

        self.message_post(body=_("""
            Facture fournisseur créée avec succès.

            Détails:
            - Total ventes: %s
            - Commission: -%s
            - Transport: -%s
            - Emballages: +%s
            - Avance: -%s
            - Net à payer: %s
        """) % (
            self.total_ventes,
            self.total_commission,
            self.transport or 0,
            self.montant_total_emballage_achete or 0,
            self.avance_producteur or 0,
            net_a_payer
        ))

        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }

    def _get_or_create_partner(self):
        """Helper pour créer ou trouver le partner"""
        self.ensure_one()

        partner = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        return partner

    # Méthodes pour le tri et regroupement (existantes)
    def get_lines_sorted_by_price_desc(self, grouped=False):
        """Retourne les lignes triées par prix décroissant"""
        self.ensure_one()

        if not self.recap_line_ids:
            return []

        if grouped:
            return self._get_visually_grouped_lines()
        else:
            lines = []
            for line in self.recap_line_ids:
                lines.append({
                    'produit_name': line.produit_id.name if line.produit_id else '',
                    'qualite_name': line.qualite_id.name if line.qualite_id else '',
                    'type_colis_name': line.type_colis_id.name if line.type_colis_id else '',
                    'nombre_colis': line.nombre_colis or 0,
                    'poids_net': line.poids_net or 0.0,
                    'prix_unitaire': line.prix_unitaire or 0.0,
                    'montant_vente': line.montant_vente or 0.0,
                    'taux_commission': line.taux_commission or 0.0,
                    'montant_commission': line.montant_commission or 0.0,
                })

            return sorted(lines, key=lambda x: float(x.get('prix_unitaire', 0)), reverse=True)

    def _get_visually_grouped_lines(self):
        """Regroupe visuellement les lignes par produit"""
        grouped_by_product = {}

        for line in self.recap_line_ids:
            product_key = line.produit_id.name if line.produit_id else 'Sans produit'

            if product_key not in grouped_by_product:
                grouped_by_product[product_key] = []

            grouped_by_product[product_key].append({
                'produit_name': line.produit_id.name if line.produit_id else '',
                'qualite_name': line.qualite_id.name if line.qualite_id else '',
                'type_colis_name': line.type_colis_id.name if line.type_colis_id else '',
                'nombre_colis': line.nombre_colis or 0,
                'poids_net': line.poids_net or 0.0,
                'prix_unitaire': line.prix_unitaire or 0.0,
                'montant_vente': line.montant_vente or 0.0,
                'taux_commission': line.taux_commission or 0.0,
                'montant_commission': line.montant_commission or 0.0,
                'product_group': product_key,
                'is_first_of_group': False,
            })

        for product_key in grouped_by_product:
            grouped_by_product[product_key] = sorted(
                grouped_by_product[product_key],
                key=lambda x: float(x.get('prix_unitaire', 0)),
                reverse=True
            )

            if grouped_by_product[product_key]:
                grouped_by_product[product_key][0]['is_first_of_group'] = True

        sorted_products = sorted(
            grouped_by_product.keys(),
            key=lambda p: (
                -max([l['prix_unitaire'] for l in grouped_by_product[p]]) if grouped_by_product[p] else 0,
                p
            )
        )

        result = []
        for product_key in sorted_products:
            result.extend(grouped_by_product[product_key])

        return result
