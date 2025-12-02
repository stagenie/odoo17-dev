# -*- coding: utf-8 -*-
from odoo import models,fields,api,_

from odoo.exceptions import UserError


class GecafleVente(models.Model):
    _inherit = 'gecafle.vente'


    show_payment_details = fields.Boolean(
        string="Afficher les détails de paiement",
        default=False,
        help="Affiche les détails des paiements sur le bon de vente"
    )

    # Champs pour la gestion des factures
    invoice_ids = fields.One2many(
        'account.move',
        'gecafle_vente_id',
        string="Factures"
    )

    invoice_count = fields.Integer(
        string="Nombre de factures",
        compute='_compute_invoice_count'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string="Facture principale",
        compute='_compute_invoice_id',
        store = True,
    )

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for vente in self:
            vente.invoice_count = len(vente.invoice_ids)

    @api.depends('invoice_ids')
    def _compute_invoice_id(self):
        for vente in self:
            vente.invoice_id = vente.invoice_ids[:1]

    def action_confirm(self):
        """Surcharge pour créer automatiquement la facture"""
        res = super().action_confirm()
        """ 
        
        """

        for vente in self:
            if vente.state == 'valide' and not vente.invoice_ids:
                invoice = vente._create_invoice()
                #invoice.action_post()
                # Ouvrir directement la facture créée
                return {
                    'name': _('Facture Client'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'target': 'current',
                }

        return res

    def _create_invoice(self):
        """Crée une facture client à partir du bon de vente"""
        self.ensure_one()

        partner = self._get_or_create_partner()

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'ref': _("Bon de vente %s") % self.name,
            'gecafle_vente_id': self.id,
            'narration': self.notes or '',
            'invoice_line_ids': []
        }

        # Créer les lignes de produits
        for line in self.detail_vente_ids:
            invoice_line_vals = self._prepare_product_invoice_line(line)
            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # MODIFICATION : Gestion des emballages selon le type de client
        if self.client_id.est_fidel:
            # Client fidèle : facturer uniquement les emballages non rendus si le paramètre est activé
            if self.company_id.fideles_paient_emballages_non_rendus and self.montant_emballages_non_rendus > 0:
                emballage_line_vals = {
                    'name': _("Emballages non rendus (jetables)"),
                    'quantity': 1,
                    'price_unit': self.montant_emballages_non_rendus,
                    'gecafle_line_type': 'emballage',
                }
                invoice_vals['invoice_line_ids'].append((0, 0, emballage_line_vals))
        else:
            # Client non fidèle : facturer tous les emballages
            if self.montant_total_emballages > 0:
                emballage_line_vals = self._prepare_emballage_line()
                invoice_vals['invoice_line_ids'].append((0, 0, emballage_line_vals))

        # Ajouter la ligne de remise si applicable
        if self.montant_remise_globale > 0:
            remise_line_vals = self._prepare_remise_line()
            invoice_vals['invoice_line_ids'].append((0, 0, remise_line_vals))

        # Créer et valider la facture
        invoice = self.env['account.move'].create(invoice_vals)
        #invoice.action_post()

        return invoice

    def _get_or_create_partner(self):
        """Recherche ou crée un res.partner pour le client GECAFLE"""
        self.ensure_one()

        # Rechercher un partner existant par nom et téléphone
        domain = [('name', '=', self.client_id.name)]
        if self.client_id.tel_mob:
            domain.append(('phone', '=', self.client_id.tel_mob))

        partner = self.env['res.partner'].search(domain, limit=1)

        if not partner:
            # Créer le partner
            partner = self.env['res.partner'].create({
                'name': self.client_id.name,
                'phone': self.client_id.tel_mob,
                'street': self.client_id.adresse,
                'customer_rank': 1,
                'lang': 'fr_FR' if self.client_id.langue_client == 'fr' else 'ar_SA',
            })

        return partner

    def _prepare_product_invoice_line(self, sale_line):
        """Prépare les valeurs pour une ligne de facture produit"""
        return {
            'name': _("%s - %s - %s") % (
                sale_line.produit_id.name,
                sale_line.qualite_id.name or '',
                sale_line.type_colis_id.name
            ),
            'quantity': sale_line.poids_net,
            'price_unit': sale_line.prix_unitaire,
            'gecafle_detail_vente_id': sale_line.id,
            'gecafle_line_type': 'produit',
            # Copie de tous les champs avec les mêmes noms
            'producteur_id': sale_line.producteur_id.id,
            'gecafle_produit_id': sale_line.produit_id.id,
            'qualite_id': sale_line.qualite_id.id if sale_line.qualite_id else False,
            'type_colis_id': sale_line.type_colis_id.id,
            'nombre_colis': sale_line.nombre_colis,
            'poids_brut': sale_line.poids_brut,
            'poids_colis': sale_line.poids_colis,
            'poids_net': sale_line.poids_net,
            'prix_unitaire': sale_line.prix_unitaire,
            'montant_net': sale_line.montant_net,
            'taux_commission': sale_line.taux_commission,
            'montant_commission': sale_line.montant_commission,
        }

    def _prepare_emballage_line(self):
        """Prépare la ligne pour les emballages consignés"""
        return {
            'name': _("Emballages consignés"),
            'quantity': 1,
            'price_unit': self.montant_total_emballages,
            'gecafle_line_type': 'emballage',
        }

    def _prepare_remise_line(self):
        """Prépare la ligne de remise"""
        return {
            'name': _("Remise commerciale"),
            'quantity': 1,
            'price_unit': -self.montant_remise_globale,
            'gecafle_line_type': 'remise',
        }

    def action_view_invoice(self):
        """Affiche la facture liée"""
        self.ensure_one()

        if not self.invoice_ids:
            raise UserError(_("Aucune facture n'est liée à ce bon de vente."))

        if len(self.invoice_ids) == 1:
            return {
                'name': _('Facture Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': self.invoice_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Factures Clients'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'target': 'current',
            }

        # Champ pour le bandeau d'état de facturation/paiement
    invoice_status_badge = fields.Selection([
        ('facture', 'مفوتر'),
        ('paiement_partiel', 'دفع جزئي'),
        ('paye', 'مدفوع'),
    ], string="Badge Facturation", compute='_compute_invoice_status_badge', store=True)

    @api.depends('invoice_id', 'invoice_id.state', 'invoice_id.payment_state')
    def _compute_invoice_status_badge(self):
        """Calcule le badge à afficher selon l'état de facturation/paiement"""
        for record in self:
            if not record.invoice_id or record.invoice_id.state == 'cancel':
                record.invoice_status_badge = False
            elif record.invoice_id.payment_state == 'paid':
                record.invoice_status_badge = 'paye'
            elif record.invoice_id.payment_state == 'partial':
                record.invoice_status_badge = 'paiement_partiel'
            else:
                # Facture créée mais non payée (not_paid, in_payment)
                record.invoice_status_badge = 'facture'

    # Nouveaux champs pour les informations de paiement
    payment_state = fields.Selection(
        string="État du paiement",
        related='invoice_id.payment_state',
        store=True
    )

    invoice_payment_state = fields.Selection(
        string="État paiement facture",
        related='invoice_id.payment_state'
    )

    amount_total_signed = fields.Monetary(
        string="Montant total facturé",
        compute='_compute_payment_info',
        currency_field='currency_id'
    )

    amount_residual_signed = fields.Monetary(
        string="Montant restant à payer",
        compute='_compute_payment_info',
        currency_field='currency_id'
    )

    amount_paid = fields.Monetary(
        string="Montant payé",
        compute='_compute_payment_info',
        currency_field='currency_id'
    )

    payment_percentage = fields.Float(
        string="Pourcentage payé",
        compute='_compute_payment_info'
    )

    # Champs pour récupérer les détails des paiements
    payment_ids = fields.Many2many(
        'account.payment',
        string="Paiements",
        compute='_compute_payment_ids'
    )

    payment_count = fields.Integer(
        string="Nombre de paiements",
        compute='_compute_payment_ids'
    )

    @api.depends('invoice_id', 'invoice_id.amount_total_signed', 'invoice_id.amount_residual_signed')
    def _compute_payment_info(self):
        for record in self:
            if record.invoice_id:
                record.amount_total_signed = record.invoice_id.amount_total_signed
                record.amount_residual_signed = record.invoice_id.amount_residual_signed
                record.amount_paid = record.amount_total_signed - record.amount_residual_signed

                if record.amount_total_signed:
                    # Ne PAS multiplier par 100 car le widget "percentage" le fait automatiquement
                    record.payment_percentage = record.amount_paid / record.amount_total_signed
                else:
                    record.payment_percentage = 0
            else:
                record.amount_total_signed = 0
                record.amount_residual_signed = 0
                record.amount_paid = 0
                record.payment_percentage = 0

    @api.depends('invoice_id')
    def _compute_payment_ids(self):
        for record in self:
            if record.invoice_id:
                payments = record.invoice_id._get_reconciled_payments()
                record.payment_ids = payments
                record.payment_count = len(payments)
            else:
                record.payment_ids = False
                record.payment_count = 0

    def action_view_payments(self):
        """Affiche les paiements liés à la facture"""
        self.ensure_one()

        if not self.invoice_id:
            raise UserError(_("Aucune facture n'est liée à ce bon de vente."))

        if self.payment_count == 0:
            raise UserError(_("Aucun paiement n'a été enregistré pour cette vente."))

        if self.payment_count == 1:
            return {
                'name': _('Paiement'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'res_id': self.payment_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Paiements'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'account.payment',
                'domain': [('id', 'in', self.payment_ids.ids)],
                'target': 'current',
            }



    """"""
    # Champs pour les opérations d'emballage client
    emballage_client_ids = fields.One2many(
        'gecafle.emballage.client',
        'vente_id',
        string="Opérations Emballage"
    )

    emballage_client_count = fields.Integer(
        string="Opérations Emballage",
        compute='_compute_emballage_client_count'
    )

    @api.depends('emballage_client_ids')
    def _compute_emballage_client_count(self):
        for record in self:
            record.emballage_client_count = len(record.emballage_client_ids)

    def action_create_emballage_client(self):
        """Crée une opération emballage client VIDE pour cette vente"""
        self.ensure_one()

        # Créer l'opération emballage SANS lignes pré-remplies
        emballage_op = self.env['gecafle.emballage.client'].create({
            'client_id': self.client_id.id,
            'vente_id': self.id,
            'date_heure_operation': fields.Datetime.now(),
            'observation': '',  # Vide
            # PAS de lignes pré-remplies
        })

        # Ouvrir le formulaire vide de l'opération créée
        return {
            'name': _('Opération Emballage Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.emballage.client',
            'res_id': emballage_op.id,
            'target': 'current',
        }

    def action_view_emballage_client(self):
        """Affiche les opérations emballage liées à cette vente"""
        self.ensure_one()

        if self.emballage_client_count == 0:
            raise UserError(_("Aucune opération emballage n'est liée à cette vente."))

        if self.emballage_client_count == 1:
            return {
                'name': _('Opération Emballage Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.emballage.client',
                'res_id': self.emballage_client_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Opérations Emballage Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'gecafle.emballage.client',
                'domain': [('id', 'in', self.emballage_client_ids.ids)],
                'target': 'current',
            }


class InheritedGecafleDetailsVentes(models.Model):
    _inherit = 'gecafle.details_ventes'

    # Dans detail_ventes.py, ajoutez cette méthode alternative
    def action_view_reception_popup(self):
        """Ouvre la réception dans un popup modal"""
        self.ensure_one()

        if not self.reception_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Aucune réception liée à cette ligne'),
                    'type': 'info',
                }
            }

        # Vue formulaire spécifique pour l'affichage en popup
        return {
            'name': _('Réception: %s') % self.reception_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.reception',
            'res_id': self.reception_id.id,
            'target': 'new',
            'flags': {
                'mode': 'readonly',  # Ouvrir en lecture seule
            },
            'context': {
                'create': False,
                'delete': False,
                'edit': False,
                'form_view_initial_mode': 'view',
            }
        }
