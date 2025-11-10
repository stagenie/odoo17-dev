# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

from odoo.exceptions import UserError, ValidationError


class GecafleVente(models.Model):
    _name = 'gecafle.vente'
    _description = 'Vente'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # pour le tracking si besoin

    # N° Souche (ou N° de Facture) qui s'incrémente automatiquement via un compteur défini dans res.company.

    name = fields.Char(
        string="N° Souche",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('gecafle.vente') or '/'
    )
    # Champ company_id avec valeur par défaut et index
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )

    def format_number(self, number):
        """Formate un nombre avec séparateur de milliers"""
        return '{:,.2f}'.format(number).replace(',', ' ')

    date_vente = fields.Datetime(
        string="Date/Heure de la Vente",
        default=fields.Datetime.now,
        required=True
    )
    client_id = fields.Many2one(
        'gecafle.client',
        string="Client",
        required=True
    )
    tel_mob_client = fields.Char(
        string="Téléphone/Mobile Client",
        related="client_id.tel_mob",
        readonly=True
    )
    region_id = fields.Many2one(
        'gecafle.region',
        string="Région",
        related="client_id.region_id",
        readonly=True
    )
    adresse = fields.Text(
        string="Adresse",
        related="client_id.adresse",
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string="Vendeur",
        default=lambda self: self.env.user,
        readonly=True
    )
    notes = fields.Text(
        string="Notes", translate=True,
        default=lambda self: self.env.company.conditions_ventes or ''
    )
    observation = fields.Text(string="Observation")
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('annule', 'Annulé')
    ], string="État", default='brouillon', tracking=True)


    """ """

    def action_print_bon_pese(self):
        """Imprime le bon de pesé"""
        self.ensure_one()
        return self.env.ref('adi_gecafle_ventes.action_report_bon_pese').report_action(self)

    def action_create_invoice(self):
        """Crée manuellement une facture pour cette vente"""
        self.ensure_one()

        # Vérifications
        if self.state != 'valide':
            raise UserError(_("La vente doit être validée avant de créer une facture."))

        if self.invoice_ids:
            raise UserError(_("Une facture existe déjà pour cette vente."))

        # Créer la facture
        invoice = self._create_invoice()

        # Message de confirmation
        self.message_post(body=_("Facture créée : %s") % invoice.name)

        # Ouvrir la facture créée
        return {
            'name': _('Facture Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }

    # Relation avec les lignes de détails
    detail_vente_ids = fields.One2many(
        'gecafle.details_ventes',
        'vente_id',
        string="Détails de vente"
    )
    # Relation avec les emballages
    detail_emballage_vente_ids = fields.One2many(
        'gecafle.details_emballage_vente',
        'vente_id',
        string="Emballages"
    )
    currency_id = fields.Many2one(
       'res.currency',
        string="Devise",
        readonly=True,
        #required=True,
        default=lambda self: self.env.company.currency_id
        )

    # Champs monétaires calculés
    montant_total_commission = fields.Monetary(
        string="Montant Total Commission",
        compute="_compute_totaux_vente",
        store=True, readonly=True,
        currency_field="currency_id",
        groups="adi_gecafle_ventes.group_gecafle_direction"
    )





    # Ajout du pourcentage de commission total
    pourcentage_total_commission = fields.Float(
        string="% Commission Total",
        compute="_compute_pourcentage_commission",
        store=True,
        digits=(5, 2),
        groups="adi_gecafle_ventes.group_gecafle_direction",
        help="Pourcentage moyen de commission sur la vente"
    )

    est_imprimee = fields.Boolean(
        string="Est imprimé",
        default=False,
        help="Indique si le bon de vente a été imprimé"
    )

    def action_imprimer_bon_vente(self):
        """Imprime le bon de vente et le marque comme imprimé"""
        self.ensure_one()
        # Marquer comme imprimé
        self.est_imprimee = True

        # Retourner l'action pour imprimer le rapport
        return self.env.ref('adi_gecafle_ventes.action_report_gecafle_bon_vente').report_action(self)

    def action_imprimer_duplicata(self):
        """Imprime un duplicata du bon de vente"""
        self.ensure_one()

        # Vérifier que le bon a déjà été imprimé
        if not self.est_imprimee:
            raise UserError(_("Vous devez d'abord imprimer le bon de vente original avant d'imprimer un duplicata."))

        # Utiliser le rapport dédié au duplicata
        return self.env.ref('adi_gecafle_ventes.action_report_gecafle_bon_vente_duplicata').report_action(self)

    def mark_as_printed(self):
        """Marque le bon comme imprimé après impression"""
        self.write({'est_imprimee': True})
        return True
    # Champ pour la remise
    montant_remise_globale = fields.Monetary(
        string="Montant Remise",
        currency_field="currency_id",
        default=0.0,
        help="Montant de la remise appliquée sur la vente, il ne doit pas dépasser le maximum autorisé "
    )

    @api.depends('montant_total_commission', 'montant_total_net')
    def _compute_pourcentage_commission(self):
        """Calcule le pourcentage moyen de commission"""
        for record in self:
            if record.montant_total_net  and record.montant_total_net!= 0:
                record.pourcentage_total_commission = (record.montant_total_commission / record.montant_total_net ) * 100
            else:
                record.pourcentage_total_commission = 0


    montant_total_emballages = fields.Monetary(
        string="Montant Colis",
        compute="_compute_totaux_vente",
        store=True, readonly=True,
        currency_field="currency_id"
    )
    montant_total_consigne = fields.Monetary(
        string="Montant Consigne",
        compute="_compute_totaux_vente",
        store=True, readonly=True,
        currency_field="currency_id",
        help="Montant total des emballages consignés (uniquement ceux rendus)"
    )
    montant_total_net = fields.Monetary(
        string="Montant Net",
        compute="_compute_totaux_vente",
        store=True, readonly=True,
        currency_field="currency_id"
    )
    montant_total_a_payer_calc = fields.Monetary(
        string="Montant Total à Payer (Calculé)",
        compute="_compute_totaux_vente",
        store=True, readonly=True,
        currency_field="currency_id"
    )
    montant_total_a_payer = fields.Monetary(
        string="Montant Total à Payer",
        default=0.0,
        store=True,
        readonly=True,
        compute="_compute_totaux_vente",
        currency_field="currency_id"
    )

    # Champs poids calculés
    total_poids_brut = fields.Float(
        string="Total Poids Brut",
        digits=(16, 2),
        compute="_compute_totaux_vente",
        store=True
    )
    total_poids_colis = fields.Float(
        string="Total Poids Colis",
        digits=(16, 2),
        compute="_compute_totaux_vente",
        store=True
    )
    total_poids_net = fields.Float(
        string="Total Poids Net",
        digits=(16, 2),
        compute="_compute_totaux_vente",
        store=True
    )

    # Description des emballages consignés
    emballages_consigne_desc = fields.Text(
        string="Description des Consignes",
        compute="_compute_emballages_consigne",
        store=True
    )

    # Devise (pour les champs monétaires)
    # Indicateur de consigne appliquée
    consigne_appliquee = fields.Boolean(
        string="Consigne Appliquée",
        compute="_compute_consigne_appliquee",
        help="Indique si la consigne est appliquée pour ce client"
    )

    @api.depends('client_id.est_fidel')
    def _compute_consigne_appliquee(self):
        for record in self:
            record.consigne_appliquee = not record.client_id.est_fidel

    # Nouveaux champs pour tracer les montants d'emballages
    montant_emballages_non_rendus = fields.Monetary(
        string="Montant Emballages Non Rendus",
        compute="_compute_totaux_vente",
        store=True,
        currency_field="currency_id",
        help="Montant des emballages jetables (non rendus)"
    )

    montant_emballages_rendus = fields.Monetary(
        string="Montant Emballages Rendus",
        compute="_compute_totaux_vente",
        store=True,
        currency_field="currency_id",
        help="Montant des emballages consignés (rendus)"
    )

    @api.depends('detail_vente_ids.montant_commission',
                 'detail_vente_ids.montant_net',
                 'detail_vente_ids.nombre_colis',
                 'detail_vente_ids.type_colis_id',
                 'client_id.est_fidel',
                 'montant_remise_globale',
                 'company_id.fideles_paient_emballages_non_rendus')
    def _compute_totaux_vente(self):
        """Calcule tous les totaux de la vente en tenant compte du statut fidèle et des emballages"""
        for vente in self:
            # Calcul des poids totaux
            vente.total_poids_brut = sum(vente.detail_vente_ids.mapped('poids_brut'))
            vente.total_poids_colis = sum(vente.detail_vente_ids.mapped('poids_colis'))
            vente.total_poids_net = sum(vente.detail_vente_ids.mapped('poids_net'))

            # Calcul des montants totaux
            vente.montant_total_commission = sum(vente.detail_vente_ids.mapped('montant_commission'))
            vente.montant_total_net = sum(vente.detail_vente_ids.mapped('montant_net'))

            # Calcul détaillé des emballages
            emballage_dict = {}
            for line in vente.detail_vente_ids:
                if line.type_colis_id:
                    emballage_id = line.type_colis_id.id
                    if emballage_id in emballage_dict:
                        emballage_dict[emballage_id] += line.nombre_colis
                    else:
                        emballage_dict[emballage_id] = line.nombre_colis

            montant_total_emballages = 0
            montant_total_consigne = 0
            montant_emballages_non_rendus = 0
            montant_emballages_rendus = 0  # AJOUT

            for emballage_id, qte in emballage_dict.items():
                emballage = self.env['gecafle.emballage'].browse(emballage_id)
                prix_emballage = emballage.price_unit

                # Montant total emballages
                montant_total_emballages += qte * prix_emballage

                # Séparer les emballages rendus et non rendus
                if not emballage.non_returnable:
                    # Emballages rendus (consignés)
                    montant_total_consigne += qte * prix_emballage
                    montant_emballages_rendus += qte * prix_emballage  # AJOUT
                else:
                    # Emballages non rendus (jetables)
                    montant_emballages_non_rendus += qte * prix_emballage

            vente.montant_total_emballages = montant_total_emballages
            vente.montant_total_consigne = montant_total_consigne
            vente.montant_emballages_non_rendus = montant_emballages_non_rendus  # ASSIGNATION
            vente.montant_emballages_rendus = montant_emballages_rendus  # AJOUT DE L'ASSIGNATION

            # Logique de calcul selon le type de client et le paramètre
            if vente.client_id.est_fidel:
                # Client fidèle
                montant_emballages_a_payer = 0

                # Vérifier si les clients fidèles doivent payer les emballages non rendus
                if vente.company_id.fideles_paient_emballages_non_rendus:
                    montant_emballages_a_payer = montant_emballages_non_rendus
                # Sinon, ils ne paient aucun emballage (montant reste à 0)

                vente.montant_total_a_payer_calc = vente.montant_total_net + montant_emballages_a_payer
            else:
                # Client non fidèle : paie tous les emballages
                vente.montant_total_a_payer_calc = vente.montant_total_net + vente.montant_total_emballages

            # Appliquer la remise
            vente.montant_total_a_payer = vente.montant_total_a_payer_calc - vente.montant_remise_globale

    @api.depends('detail_emballage_vente_ids.qte_sortantes',
                 'detail_emballage_vente_ids.emballage_id')
    def _compute_emballages_consigne(self):
        """Génère une description textuelle des emballages consignés"""
        for vente in self:
            emballages_groupes = {}

            # Regrouper les emballages rendus par type
            for line in vente.detail_emballage_vente_ids:
                if not line.emballage_id.non_returnable and line.qte_sortantes > 0:
                    emb_name = line.emballage_id.name
                    if emb_name in emballages_groupes:
                        emballages_groupes[emb_name] += line.qte_sortantes
                    else:
                        emballages_groupes[emb_name] = line.qte_sortantes

            # Formater la description
            descriptions = []
            for emb_name, qte in emballages_groupes.items():
                descriptions.append(f"{qte} {emb_name}")

            vente.emballages_consigne_desc = ", ".join(descriptions) if descriptions else ""

    """ """
    @api.onchange('montant_total_a_payer_calc')
    def _onchange_montant_total_a_payer_calc(self):
        """Met à jour le montant modifiable quand le montant calculé change"""
        if not self.montant_total_a_payer:
            self.montant_total_a_payer = self.montant_total_a_payer_calc

    @api.constrains('detail_vente_ids')
    def _check_vente_coherence(self):
        """Vérifie la cohérence des données de vente"""
        for record in self:
            if record:
                # Vérifier que toutes les lignes ont un prix unitaire
                for line in record.detail_vente_ids:
                    if line.prix_unitaire <= 0:
                        raise ValidationError(_(
                            "Le prix unitaire doit être supérieur à zéro pour le produit %s"
                        ) % line.produit_id.name)

                    if line.poids_brut <= 0:
                        raise ValidationError(_(
                            "Le poids brut doit être supérieur à zéro pour le produit %s"
                        ) % line.produit_id.name)
                    if line.poids_net <= 0:
                        raise ValidationError(_(
                            "Le poids net doit être supérieur à zéro pour le produit %s"
                        ) % line.produit_id.name)

    @api.model
    def create(self, vals):
        # Si le numéro de vente n'est pas fourni, on le crée automatiquement à partir d'un compteur
        if not vals.get('name') or vals.get('name') == '/':
            company = self.env.company
            new_name = company.sudo().increment_counter('vente_counter')
            vals['name'] = new_name

        # AJOUT : Vérifier le stock avant création
        if 'detail_vente_ids' in vals:
            self._check_stock_before_create(vals['detail_vente_ids'])

        # Création de l'enregistrement
        record = super(GecafleVente, self).create(vals)
        return record

    def _check_stock_before_create(self, detail_lines):
        """Vérifie le stock avant la création de la vente"""
        for line in detail_lines:
            if line[0] == 0:  # Création d'une nouvelle ligne
                line_vals = line[2]
                if 'detail_reception_id' in line_vals and 'nombre_colis' in line_vals:
                    detail_reception = self.env['gecafle.details_reception'].browse(
                        line_vals['detail_reception_id']
                    )
                    if detail_reception.qte_colis_disponibles < line_vals['nombre_colis']:
                        raise ValidationError(_(
                            "Stock insuffisant pour %s! Disponible: %s, Demandé: %s"
                        ) % (
                                                  detail_reception.designation_id.name,
                                                  detail_reception.qte_colis_disponibles,
                                                  line_vals['nombre_colis']
                                              ))

    def generate_emballage_lines(self):
        """
        Génère ou met à jour les lignes d'emballage basées sur les détails de vente.
        Regroupe les emballages de même type, peu importe la qualité des produits.
        """
        self.ensure_one()

        # Suppression des lignes d'emballage existantes
        self.detail_emballage_vente_ids.unlink()

        # Dictionnaire pour regrouper les emballages par type
        emballage_dict = {}

        # Parcourir les lignes de vente et regrouper les emballages
        for line in self.detail_vente_ids:
            if line.type_colis_id:
                emballage_id = line.type_colis_id.id
                if emballage_id in emballage_dict:
                    emballage_dict[emballage_id] += line.nombre_colis
                else:
                    emballage_dict[emballage_id] = line.nombre_colis

        # Créer les lignes d'emballage regroupées
        for emballage_id, qte in emballage_dict.items():
            if qte > 0:
                self.env['gecafle.details_emballage_vente'].create({
                    'vente_id': self.id,
                    'emballage_id': emballage_id,
                    'qte_sortantes': qte,
                    'qte_entrantes': 0,  # Par défaut, pas d'entrées
                })

        return True

    def action_confirm(self):
        """Valide la vente et met à jour les stocks disponibles avec verrouillage"""
        for record in self:
            if record.state == 'brouillon':
                # Verrouillage des lignes de réception concernées
                with self.env.cr.savepoint():
                    # Forcer le verrouillage avec FOR UPDATE
                    detail_reception_ids = record.detail_vente_ids.mapped('detail_reception_id.id')
                    if detail_reception_ids:
                        self.env.cr.execute("""
                            SELECT id FROM gecafle_details_reception 
                            WHERE id IN %s 
                            FOR UPDATE NOWAIT
                        """, (tuple(detail_reception_ids),))

                    # Vérification du stock disponible
                    for line in record.detail_vente_ids:
                        if line.nombre_colis > line.detail_reception_id.qte_colis_disponibles:
                            raise UserError(_(
                                "Stock insuffisant pour le produit %s (disponible: %s, demandé: %s)"
                            ) % (
                                                line.produit_id.name,
                                                line.detail_reception_id.qte_colis_disponibles,
                                                line.nombre_colis
                                            ))

                    # Mise à jour du stock pour chaque ligne de vente
                    for line in record.detail_vente_ids:
                        if line.reception_id.state == 'confirmee':
                            stock_entries = self.env['gecafle.stock'].search([
                                ('reception_id', '=', line.reception_id.id),
                                ('designation_id', '=', line.produit_id.id),
                                ('qualite_id', '=', line.qualite_id.id),
                                ('emballage_id', '=', line.type_colis_id.id),
                                ('qte_disponible', '>', 0)
                            ], order='id')

                            if stock_entries:
                                quantite_a_vendre = line.nombre_colis

                                for stock in stock_entries:
                                    if quantite_a_vendre <= 0:
                                        break

                                    quantite_prelevee = min(quantite_a_vendre, stock.qte_disponible)

                                    stock.with_context(force_stock=True).write({
                                        'qte_disponible': stock.qte_disponible - quantite_prelevee
                                    })

                                    quantite_a_vendre -= quantite_prelevee

                                if quantite_a_vendre > 0:
                                    raise UserError(_(
                                        "Impossible de trouver suffisamment de stock pour le produit %s. "
                                        "Manque: %s unités."
                                    ) % (line.produit_id.name, quantite_a_vendre))

                    # Génération des lignes d'emballage
                    record.generate_emballage_lines()

                    # Si le montant modifiable n'est pas défini, utiliser le calculé
                    if not record.montant_total_a_payer:
                        record.montant_total_a_payer = record.montant_total_a_payer_calc

                    # Changer l'état
                    record.state = 'valide'

        return True

    def action_confirm_back(self):
        """
            Valide la vente et met à jour les stocks disponibles:
            - Diminue la quantité disponible dans les lignes de réception
            - Génère les lignes d'emballage
            - Met à jour l'état de la vente
         """
        for record in self:
            if record.state == 'brouillon':
                # Vérification du stock disponible
                for line in record.detail_vente_ids:
                    if line.nombre_colis > line.detail_reception_id.qte_colis_disponibles:
                        raise UserError(_(
                            "Stock insuffisant pour le produit %s (disponible: %s, demandé: %s)"
                        ) % (     line.produit_id.name,
                                            line.detail_reception_id.qte_colis_disponibles,
                                            line.nombre_colis
                                        ))
            # Génération des lignes d'emballage
            record.generate_emballage_lines()
            # Si le montant modifiable n'est pas défini, utiliser le calculé
            if not record.montant_total_a_payer:
                record.montant_total_a_payer = record.montant_total_a_payer_calc
            # Changer l'état
            record.state = 'valide'
        return True

    def action_cancel(self):
        """Annule la vente et restaure le stock"""
        for record in self:

            # AJOUT : Vérifier s'il y a une facture
            if hasattr(record, 'invoice_ids') and record.invoice_ids:
                # Vérifier l'état des factures
                posted_invoices = record.invoice_ids.filtered(lambda i: i.state == 'posted')
                if posted_invoices:
                    raise UserError(_(
                        "Impossible d'annuler cette vente car elle a une ou plusieurs factures validées.\n"
                        "Factures concernées : %s\n"
                        "Pour annuler cette vente, vous devez d'abord créer un avoir pour les factures."
                    ) % ', '.join(posted_invoices.mapped('name')))

                # Si factures en brouillon
                draft_invoices = record.invoice_ids.filtered(lambda i: i.state == 'draft')
                if draft_invoices:
                    raise UserError(_(
                        "Impossible d'annuler cette vente car elle a des factures en brouillon.\n"
                        "Veuillez d'abord supprimer ou annuler ces factures : %s"
                    ) % ', '.join(draft_invoices.mapped('name')))

            if record.state != 'valide':
                continue

            # Journaliser l'action pour la traçabilité
            record.message_post(body=_("La vente a été annulée. Le stock a été restauré."))

            # Restaurer le stock si la vente était validée
            self._restore_stock_with_lock()

            # Changer l'état
            record.state = 'annule'

        return True

    def action_reset_draft(self):
        """Remet la vente en brouillon et restaure le stock"""
        for record in self:
            # AJOUT : Vérifier s'il y a une facture
            if hasattr(record, 'invoice_ids') and record.invoice_ids:
                raise UserError(_(
                    "Impossible de remettre en brouillon cette vente car elle a des factures associées.\n"
                    "Pour modifier cette vente, utilisez le système d'ajustement."
                ))

            if record.state != 'valide':
                continue

            # Journaliser l'action pour la traçabilité
            record.message_post(body=_("La vente a été remise en brouillon. Le stock a été restauré."))

            # Restaurer le stock pour chaque ligne de vente
            self._restore_stock()

            # Changer l'état
            record.state = 'brouillon'

        return True

    def unlink(self):
        """Empêche la suppression des ventes avec factures"""
        for record in self:
            # Vérifier l'état
            if record.state == 'valide':
                raise UserError(_(
                    "Impossible de supprimer une vente validée.\n"
                    "Vous devez d'abord l'annuler."
                ))

            # AJOUT : Vérifier s'il y a des factures
            if hasattr(record, 'invoice_ids') and record.invoice_ids:
                raise UserError(_(
                    "Impossible de supprimer cette vente car elle a des factures associées.\n"
                    "Vente : %s\n"
                    "Factures : %s"
                ) % (record.name, ', '.join(record.invoice_ids.mapped('name'))))




        return super(GecafleVente, self).unlink()

    def _restore_stock(self):
        """Méthode commune pour restaurer le stock"""
        self.ensure_one()

        for line in self.detail_vente_ids:
            # Rechercher les entrées de stock correspondantes
            stock_entries = self.env['gecafle.stock'].search([
                ('reception_id', '=', line.reception_id.id),
                ('designation_id', '=', line.produit_id.id),
                ('qualite_id', '=', line.qualite_id.id),
                ('emballage_id', '=', line.type_colis_id.id)
            ], order='id')

            # Variable pour suivre la quantité restante à restaurer
            qty_to_restore = line.nombre_colis

            # Parcourir les entrées de stock trouvées
            for stock in stock_entries:
                if qty_to_restore <= 0:
                    break

                # Calculer la quantité à restaurer dans cette entrée
                qty_restored = min(qty_to_restore, line.nombre_colis)

                # Mettre à jour le stock avec le contexte force_stock
                stock.with_context(force_stock=True).write({
                    'qte_disponible': stock.qte_disponible + qty_restored
                })

                # Enregistrer la restauration dans l'historique
                self.message_post(body=_(
                    "Stock restauré pour %s: +%d dans l'entrée %s"
                ) % (line.produit_id.name, qty_restored, stock.id))

                # Mettre à jour la quantité restante à restaurer
                qty_to_restore -= qty_restored

            # Si on n'a pas pu restaurer tout le stock (entrées supprimées), créer une nouvelle entrée
            if qty_to_restore > 0:
                # Recherche de la ligne de réception
                detail_reception = self.env['gecafle.details_reception'].search([
                    ('reception_id', '=', line.reception_id.id),
                    ('designation_id', '=', line.produit_id.id),
                    ('qualite_id', '=', line.qualite_id.id),
                    ('type_colis_id', '=', line.type_colis_id.id)
                ], limit=1)

                if detail_reception:
                    # Créer une nouvelle entrée de stock
                    new_stock = self.env['gecafle.stock'].with_context(force_stock=True).create({
                        'reception_id': line.reception_id.id,
                        'designation_id': line.produit_id.id,
                        'qualite_id': line.qualite_id.id,
                        'emballage_id': line.type_colis_id.id,
                        'qte_disponible': qty_to_restore
                    })

                    self.message_post(body=_(
                        "Nouvelle entrée de stock créée pour %s: +%d (ID: %s)"
                    ) % (line.produit_id.name, qty_to_restore, new_stock.id))

    # Ajout de commission effective
        # Nouveaux champs pour la marge effective
    marge_effective = fields.Monetary(
        string="Marge Effective",
        compute="_compute_marge_effective",
        store=True,
        currency_field="currency_id",
        groups="adi_gecafle_ventes.group_gecafle_direction"
        # Uniquement visible par la direction
    )
    pourcentage_marge_effective = fields.Float(
        string="% Marge Effective",
        compute="_compute_marge_effective",
        store=True,
        digits=(5, 2),
        groups="adi_gecafle_ventes.group_gecafle_direction"  # Uniquement visible par la direction
    )

    @api.depends('montant_total_net', 'montant_total_a_payer', 'montant_total_consigne', 'client_id.est_fidel')
    def _compute_marge_effective(self):
        """
        Calcule la marge effective en tenant compte des modifications du montant total à payer
        """
        for record in self:
            # Montant de base (montant net ou montant net + consigne selon le type de client)
            montant_base = record.montant_total_net
            if not record.client_id.est_fidel:
                montant_base += record.montant_total_consigne

            # Marge comptable (basée sur les lignes)
            marge_comptable = record.montant_total_commission

            # Calcul de la marge effective tenant compte des remises
            if montant_base and record.montant_total_a_payer:
                # Facteur de remise
                facteur_remise = record.montant_total_a_payer / montant_base if montant_base else 1

                # Marge effective = marge comptable ajustée par le facteur de remise
                record.marge_effective = marge_comptable * facteur_remise

                # Pourcentage de marge effective
                record.pourcentage_marge_effective = (
                                                                 record.marge_effective / record.montant_total_a_payer) * 100 if record.montant_total_a_payer else 0
            else:
                record.marge_effective = 0
                record.pourcentage_marge_effective = 0

        # Champ pour contrôler l'édition du montant total

    # Champs de paramètres de la société (en lecture seule)
    remise_max_autorisee = fields.Monetary(
        string="Remise Maximale Autorisée",
        related="company_id.remise_max_autorisee",
        readonly=True,
        currency_field="currency_id",  # Utiliser currency_id
        help="Montant maximal de remise autorisé sur une vente"
    )

    peut_modifier_prix = fields.Boolean(
        string="Peut modifier le prix",
        related="company_id.autoriser_modification_prix",
        readonly=True,
        help="Si coché, permet d'effectuer des remises globales"
    )

    # Calcul du montant à payer en fonction de la remise
    @api.depends('montant_total_a_payer_calc', 'montant_remise_globale')
    def _compute_montant_total_a_payer(self):
        for record in self:
            record.montant_total_a_payer = max(0, record.montant_total_a_payer_calc - record.montant_remise_globale)

    # Contrainte pour vérifier que la remise ne dépasse pas le maximum autorisé
    @api.constrains('montant_remise_globale')
    def _check_montant_remise_globale(self):
        for record in self:
            if not record.peut_modifier_prix and record.montant_remise_globale > 0:
                raise ValidationError(_("Vous n'êtes pas autorisé à appliquer des remises."))

            if record.montant_remise_globale > record.remise_max_autorisee:
                raise ValidationError(_(
                    "La remise de %.2f dépasse le montant maximal autorisé (%.2f)."
                ) % (record.montant_remise_globale, record.remise_max_autorisee))

            if record.montant_remise_globale > record.montant_total_a_payer_calc:
                raise ValidationError(_("La remise ne peut pas être supérieure au montant total."))

    # Ajouter la traçabilité pour les modifications de remise
    @api.onchange('montant_remise_globale')
    def _onchange_montant_remise_globale(self):
        if self.montant_remise_globale > 0:
            return {
                'warning': {
                    'title': 'Remise appliquée',
                    'message': f"Vous appliquez une remise de {self.montant_remise_globale:.2f}. "
                               f"Cette action sera enregistrée dans l'historique."
                }
            }

    # Surcharge de la méthode write pour enregistrer l'historique des remises
    def write(self, vals):
        """Surcharge pour protéger les ventes avec factures"""
        for record in self:
            if record.state == 'valide' and not self.env.context.get('allow_adjustment'):
                # Vérifier si des factures existent
                if hasattr(record, 'invoice_ids') and record.invoice_ids:
                    # Liste des champs toujours autorisés même avec facture
                    always_allowed = ['est_imprimee', 'state', 'notes', 'observation', 'show_payment_details']

                    # Vérifier si on tente de modifier des champs critiques
                    critical_fields = set(vals.keys()) - set(always_allowed)

                    if critical_fields:
                        raise UserError(_(
                            "Cette vente a des factures associées et ne peut plus être modifiée.\n"
                            "Pour la modifier, utilisez le système d'ajustement.\n"
                            "Factures : %s"
                        ) % ', '.join(record.invoice_ids.mapped('name')))

                # Vérifier si des récaps existent (code existant)
                has_recap = self.env['gecafle.reception.recap'].search_count([
                    ('sale_line_ids.vente_id', '=', record.id),
                    ('state', 'in', ['valide', 'facture'])
                ])

                if has_recap:
                    always_allowed = ['est_imprimee', 'state', 'notes', 'observation']
                    critical_fields = set(vals.keys()) - set(always_allowed)

                    if critical_fields:
                        raise UserError(_(
                            "Cette vente fait partie d'un récapitulatif producteur déjà validé.\n"
                            "Pour la modifier, utilisez la fonction 'Créer un ajustement'.\n"
                            "Cela permettra de tracer les modifications et gérer les impacts."
                        ))


            # Enregistrer l'historique des remises (code existant)
            for record in self:
                if 'montant_remise_globale' in vals and record.montant_remise_globale != vals['montant_remise_globale']:
                    old_remise = record.montant_remise_globale
                    new_remise = vals['montant_remise_globale']

                    record.message_post(body=_(
                        "Remise globale modifiée: de %.2f à %.2f (différence: %.2f)"
                    ) % (old_remise, new_remise, new_remise - old_remise))

        return super(GecafleVente, self).write(vals)
    # Champs pour le suivi des consignes


    # Ajouter cette nouvelle méthode
    def _restore_stock_with_lock(self):
        """Restaure le stock avec verrouillage transactionnel"""
        self.ensure_one()

        # Verrouiller les lignes de réception concernées
        detail_reception_ids = self.detail_vente_ids.mapped('detail_reception_id.id')
        if detail_reception_ids:
            self.env.cr.execute("""
                SELECT id FROM gecafle_details_reception 
                WHERE id IN %s 
                FOR UPDATE
            """, (tuple(detail_reception_ids),))

        # Procéder à la restauration
        for line in self.detail_vente_ids:
            line.detail_reception_id.qte_colis_vendus = max(0,
                                                            line.detail_reception_id.qte_colis_vendus - line.nombre_colis
                                                            )

            # Restaurer aussi dans les entrées de stock
            stock_entries = self.env['gecafle.stock'].search([
                ('reception_id', '=', line.reception_id.id),
                ('designation_id', '=', line.produit_id.id),
                ('qualite_id', '=', line.qualite_id.id),
                ('emballage_id', '=', line.type_colis_id.id)
            ], order='id')

            qty_to_restore = line.nombre_colis
            for stock in stock_entries:
                if qty_to_restore <= 0:
                    break

                stock.with_context(force_stock=True).write({
                    'qte_disponible': stock.qte_disponible + qty_to_restore
                })
                qty_to_restore = 0

    # Avoir clients
    avoir_ids = fields.One2many(
        'gecafle.avoir.client',
        'vente_id',
        string="Avoirs"
    )

    avoir_count = fields.Integer(
        string="Nombre d'avoirs",
        compute='_compute_avoir_count'
    )

    @api.depends('avoir_ids')
    def _compute_avoir_count(self):
        for vente in self:
            vente.avoir_count = len(vente.avoir_ids)

    def action_create_avoir(self):
        """Crée un avoir client pour cette vente"""
        self.ensure_one()

        if self.state != 'valide':
            raise ValidationError(_("Vous ne pouvez créer un avoir que pour une vente validée."))

        # Créer l'avoir en brouillon
        avoir = self.env['gecafle.avoir.client'].create({
            'vente_id': self.id,
            'date': fields.Date.today(),
            'type_avoir': 'non_vendu',
            'montant_avoir': 0.0,  # À renseigner manuellement
            'description': '',
        })

        # Ouvrir le formulaire de l'avoir
        return {
            'name': _('Avoir Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client',
            'res_id': avoir.id,
            'target': 'current',
        }

    def action_view_avoirs(self):
        """Affiche les avoirs liés à cette vente"""
        self.ensure_one()

        if self.avoir_count == 0:
            raise UserError(_("Aucun avoir n'est lié à cette vente."))

        if self.avoir_count == 1:
            return {
                'name': _('Avoir Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.avoir.client',
                'res_id': self.avoir_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Avoirs Clients'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'gecafle.avoir.client',
                'domain': [('id', 'in', self.avoir_ids.ids)],
                'target': 'current',
            }

