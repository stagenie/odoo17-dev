from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from  odoo.exceptions import UserError

class GecafleReception(models.Model):
    _name = 'gecafle.reception'
    _description = 'Réception des Producteurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']



    name = fields.Char(
        string="N° de Réception",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('gecafle.reception') or '/'
    )
    reception_date = fields.Datetime(
        string="Date Heure de Réception",
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    state = fields.Selection(
        [
            ('brouillon', 'Brouillon'),
            ('confirmee', 'Confirmée'),
            ('annulee', 'Annulée'),
        ],
        string="État",
        default='brouillon',
        tracking=True
    )
    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        required=True,
        ondelete='restrict',

    )
    # context={'default_create': False}

    @api.onchange('producteur_id')
    def _onchange_producteur_id(self):
        if self.producteur_id:
            # Réinitialisation du champ One2many
            self.details_reception_ids = [(5, 0, 0)]

    adresse_producteur = fields.Text(
        string="Adresse du Producteur",
        related='producteur_id.address',
        readonly=True
    )
    phone_producteur = fields.Char(
        string="Téléphone du Producteur",
        related='producteur_id.phone',
        readonly=True
    )
    avance_producteur = fields.Monetary(
        string="Montant Avance Producteur",
        currency_field='currency_id',
        compute='_compute_payment_amounts',
        store=True,
        readonly=True,
        help="Ce champ est automatiquement calculé depuis les paiements d'avance producteur validés liés à cette réception."
    )
    verse_a = fields.Char(
        string="Versé à",
        help="Par défaut le nom du producteur, peut être modifié",
        default=""
    )
    observations = fields.Text(string="Observations")
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id.id
    )

    # Méthode pour imprimer le Bon de Réception (format A5)
    def action_print_bon_reception(self):
        self.ensure_one()
        # Marquer la réception comme imprimée

        # Retourner l'action du rapport défini ci-dessous
        return self.env.ref('adi_gecafle_receptions.action_report_bon_reception').report_action(self)

    def action_print_duplicata(self):
        """Imprime le bon de réception avec la mention DUPLICATA."""
        self.ensure_one()
        # Utiliser le rapport dédié au duplicata
        return self.env.ref('adi_gecafle_receptions.action_report_bon_reception_duplicata').report_action(self)

    # Nouveau champ pour marquer l'impression

    est_imprimee = fields.Boolean(string="Imprimée ?", default=False)

    regrouper_lignes = fields.Boolean(
        string="Regrouper les lignes similaires",
        default=True,
        help="Si coché, les lignes ayant la même désignation, qualité et type de colis seront regroupées (les quantités seront additionnées)."
    )

    def group_details_lines(self):

        #Regroupe les lignes de détails dans la réception en sommant la quantité de colis reçus
        #lorsque la désignation, la qualité et le type de colis sont identiques.

        for reception in self:
            if reception.regrouper_lignes:
                seen = {}
                # On stocke ici les lignes à supprimer après le regroupement.
                lines_to_delete = self.env['gecafle.details_reception']
                for line in reception.details_reception_ids:
                    # La clé est composée de la désignation, de la qualité (si renseignée) et du type de colis.
                    key = (
                        line.designation_id.id,
                        line.qualite_id.id if line.qualite_id else False,
                        line.type_colis_id.id,
                    )
                    if key in seen:
                        # On met à jour la quantité sur la première ligne enregistrée
                        seen_line = seen[key]
                        seen_line.qte_colis_recue += line.qte_colis_recue
                        # On ajoute la ligne en doublon à la liste des lignes à supprimer
                        lines_to_delete |= line
                    else:
                        seen[key] = line
                if lines_to_delete:
                    lines_to_delete.unlink()
        return True


    @api.model
    def create(self, vals):
        # Si le numéro de réception n'est pas renseigné ou vaut la valeur par défaut
        if not vals.get('name') or vals.get('name') == '/':
            company = self.env.company
            # Utilisation du compteur reception_counter défini dans le module adi_gecafle_base_stock
            new_name = company.sudo().increment_counter('reception_counter')
            vals['name'] = new_name
        # Initialiser "versé à" avec le nom du producteur s'il est fourni
        if vals.get('producteur_id') and not vals.get('verse_a'):
            producteur = self.env['gecafle.producteur'].browse(vals.get('producteur_id'))
            vals['verse_a'] = producteur.name
        # Création de l'enregistrement
        record = super(GecafleReception, self).create(vals)
        # Appel automatique du regroupement des lignes de réception et des emballages
        record.group_details_lines()
        record._group_and_create_emballage_details()
        return record

    def action_confirm(self):
        """
        Fonction à appeler lors du clic sur le bouton 'Confirmer'.
        Ici, vous pouvez ajouter des validations ou d'autres logiques métier.
        """
        for rec in self:
            # Exemple de validation : Vérifier qu'il existe au moins une ligne de réception.
            # if not rec.details_reception_ids:
            #     raise UserError(_("Veuillez saisir au moins un détail de réception."))

            #rec.group_details_lines()
            rec.state = 'confirmee'
            rec.group_details_lines()
            rec._group_and_create_emballage_details()
            rec._generate_stock_entries()
            if rec.avance_producteur > 0:
                rec._create_advance_payment()
        return True

    def action_cancel(self):
        """
        Fonction à appeler lors du clic sur le bouton 'Annuler'.
        Vous pouvez ajouter des contrôles pour empêcher l'annulation si nécessaire.
        """
        for rec in self:
            for stock in rec.stock_ids:
                stock.with_context(force_stock=True).unlink()  # Suppression des destockages associés pour chaque stock lié, en utilisant le contexte
            rec.stock_ids.with_context(force_stock=True).unlink()
            rec.state = 'annulee'

        return True

    def action_reset_to_draft(self):
        for rec in self:
            # Suppression des destockages associés pour chaque stock lié, en utilisant le contexte
            for stock in rec.stock_ids:
                stock.with_context(force_stock=True).unlink()  #
            rec.stock_ids.with_context(force_stock=True).unlink()
            rec.write({'state': 'brouillon'})

            rec.state = 'brouillon'
        return True

    details_reception_ids = fields.One2many(
        'gecafle.details_reception',
        'reception_id',
        string="Détails de Réception"
    )

    details_emballage_reception_ids = fields.One2many(
        'gecafle.details_emballage_reception',
        'reception_id',
        string='Détails des Emballages'
    )

    # Lignes de stock générées à partir de la réception
    stock_ids = fields.One2many(
        'gecafle.stock',
        'reception_id',
        string="Stocks associés",
        readonly=True
    )

    # Champ pour afficher le nombre de stock généré (pour le smart button)
    stock_count = fields.Integer(
        string="Stock",
        compute="_compute_stock_count",
        store=True
    )

    @api.depends('stock_ids')
    def _compute_stock_count(self):
        for rec in self:
            rec.stock_count = len(rec.stock_ids)

    def _generate_stock_entries(self):
        """
        Génère les entrées de stock à partir des lignes de réception.
        Prend en compte les ventes déjà réalisées sur les réceptions en brouillon.
        """
        for rec in self:
            # Verrouillage des lignes de réception
            if rec.details_reception_ids:
                self.env.cr.execute("""
                            SELECT id FROM gecafle_details_reception 
                            WHERE reception_id = %s 
                            FOR UPDATE
                        """, (rec.id,))

            # Suppression des anciennes entrées de stock pour cette réception
            rec.stock_ids.with_context(force_stock=True).unlink()


            # Vérifier d'abord que toutes les quantités reçues sont cohérentes avec les ventes
            for line in rec.details_reception_ids:
                if line.qte_colis_recue < (line.qte_colis_vendus + line.qte_colis_destockes):
                    raise UserError(_(
                        "La quantité reçue (%s) ne peut pas être inférieure à la somme des quantités "
                        "déjà vendues (%s) et destockées (%s) pour le produit %s"
                    ) % (
                                        line.qte_colis_recue,
                                        line.qte_colis_vendus,
                                        line.qte_colis_destockes,
                                        line.designation_id.name
                                    ))

            grouped = {}
            # Parcourir les lignes de réception
            for line in rec.details_reception_ids:
                # Calculer la quantité disponible pour le stock
                qte_disponible = line.qte_colis_recue - line.qte_colis_vendus - line.qte_colis_destockes

                # Ne créer de stock que si la quantité disponible est positive
                if qte_disponible > 0:
                    # Clé de regroupement : produit, qualité et emballage
                    key = (
                        line.designation_id.id,
                        line.qualite_id.id if line.qualite_id else False,
                        line.type_colis_id.id
                    )
                    grouped.setdefault(key, 0)
                    grouped[key] += qte_disponible

            # Création d'une entrée de stock par groupe
            for key, qte in grouped.items():
                designation_id, qualite_id, emballage_id = key
                self.env['gecafle.stock'].with_context(force_stock=True).create({
                    'reception_id': rec.id,
                    'designation_id': designation_id,
                    'qualite_id': qualite_id,
                    'emballage_id': emballage_id,
                    'qte_disponible': qte,
                })





    def write(self, vals):
        res = super(GecafleReception, self).write(vals)
        self.group_details_lines()
        self._group_and_create_emballage_details()
        return res

    def _group_details_lines(self):

        # Regroupe les lignes de détails en sommant la quantité de colis reçus
        # lorsque la désignation, la qualité et le type de colis sont identiques.

        grouped_lines = {}
        for line in self.details_reception_ids:
            key = (line.designation_id.id, line.qualite_id.id, line.type_colis_id.id)
            if key in grouped_lines:
                grouped_lines[key].qte_colis_recue += line.qte_colis_recue
            else:
                grouped_lines[key] = line

        # Remplacer les lignes par les lignes regroupées
        self.details_reception_ids = [(5, 0, 0)]  # Supprime toutes les lignes existantes
        self.details_reception_ids = [(0, 0, {
            'designation_id': line.designation_id.id,
            'qualite_id': line.qualite_id.id,
            'type_colis_id': line.type_colis_id.id,
            'qte_colis_recue': line.qte_colis_recue,
            # Ajoutez d'autres champs si nécessaire
        }) for line in grouped_lines.values()]

    def _group_and_create_emballage_details(self):
        for rec in self:
            # Calculer la somme des quantités pour chaque emballage à partir des détails de réception
            grouped_data = {}
            for detail in rec.details_reception_ids:
                emballage_id = detail.type_colis_id.id
                grouped_data.setdefault(emballage_id, 0)
                grouped_data[emballage_id] += detail.qte_colis_recue

            # Pour chaque emballage dans le regroupement
            for emballage_id, total_qte in grouped_data.items():
                # Chercher une ligne auto générée pour cet emballage
                auto_line = rec.details_emballage_reception_ids.filtered(
                    lambda l: l.emballage_id.id == emballage_id and l.auto_generated
                )
                if auto_line:
                    # Mise à jour de la ligne auto générée existante
                    auto_line.write({
                        'qte_entrantes': total_qte,
                        'qte_sortantes': total_qte,
                    })
                else:
                    # S'il n'y a pas de ligne auto générée, vérifier si une ligne (manuelle) existe déjà
                    existing_line = rec.details_emballage_reception_ids.filtered(
                        lambda l: l.emballage_id.id == emballage_id
                    )
                    if not existing_line:
                        # Aucune ligne existante pour cet emballage, on crée une ligne auto générée
                        self.env['gecafle.details_emballage_reception'].create({
                            'reception_id': rec.id,
                            'emballage_id': emballage_id,
                            'qte_entrantes': total_qte,
                            'qte_sortantes': total_qte,
                            'auto_generated': True,
                        })
                    # Sinon, il existe déjà une ligne (manuelle) pour cet emballage :
                    # on ne touche pas à cette ligne pour préserver la modification manuelle.

            # Supprimer les lignes auto générées dont l'emballage n'est plus présent dans grouped_data
            lines_to_remove = rec.details_emballage_reception_ids.filtered(
                lambda l: l.auto_generated and l.emballage_id.id not in grouped_data
            )
            lines_to_remove.unlink()

    """ """
    # Champs pour les opérations d'emballage producteur
    emballage_producteur_ids = fields.One2many(
        'gecafle.emballage.producteur',
        'reception_id',
        string="Opérations Emballage"
    )

    emballage_producteur_count = fields.Integer(
        string="Opérations Emballage",
        compute='_compute_emballage_producteur_count'
    )

    @api.depends('emballage_producteur_ids')
    def _compute_emballage_producteur_count(self):
        for record in self:
            record.emballage_producteur_count = len(record.emballage_producteur_ids)

    def action_create_emballage_producteur(self):
        """Crée une opération emballage producteur VIDE pour cette réception"""
        self.ensure_one()

        # Créer l'opération emballage SANS lignes pré-remplies
        emballage_op = self.env['gecafle.emballage.producteur'].create({
            'producteur_id': self.producteur_id.id,
            'reception_id': self.id,
            'date_heure_operation': fields.Datetime.now(),
            'observation': '',  # Vide
            # PAS de lignes pré-remplies
        })

        # Ouvrir le formulaire vide de l'opération créée
        return {
            'name': _('Opération Emballage Producteur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.emballage.producteur',
            'res_id': emballage_op.id,
            'target': 'current',
        }

    def action_view_emballage_producteur(self):
        """Affiche les opérations emballage liées à cette réception"""
        self.ensure_one()

        if self.emballage_producteur_count == 0:
            raise UserError(_("Aucune opération emballage n'est liée à cette réception."))

        if self.emballage_producteur_count == 1:
            return {
                'name': _('Opération Emballage Producteur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.emballage.producteur',
                'res_id': self.emballage_producteur_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Opérations Emballage Producteur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'gecafle.emballage.producteur',
                'domain': [('id', 'in', self.emballage_producteur_ids.ids)],
                'target': 'current',
            }
        # Champs pour l'avance


    payment_ids = fields.One2many(
        'account.payment',
        'reception_id',
        string="Paiements",
        help="Paiements liés à cette réception"
    )

    payment_count = fields.Integer(
        string="Nombre de paiements",
        compute='_compute_payment_count'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    @api.depends('payment_ids', 'payment_ids.move_id.state', 'payment_ids.amount', 'payment_ids.is_advance_producer')
    def _compute_payment_amounts(self):
        """Calcule le montant total des avances producteur validées"""
        for record in self:
            # Calculer la somme des paiements avance producteur validés
            total_avance = sum(
                payment.amount
                for payment in record.payment_ids
                if payment.is_advance_producer and payment.move_id and payment.move_id.state == 'posted'
            )
            record.avance_producteur = total_avance

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for record in self:
            record.payment_count = len(record.payment_ids)



    def _create_advance_payment(self):
        """Crée un paiement fournisseur pour l'avance producteur (si n'existe pas déjà)"""
        self.ensure_one()

        # Vérifier si un paiement d'avance producteur existe déjà pour cette réception
        existing_payment = self.env['account.payment'].search([
            ('reception_id', '=', self.id),
            ('is_advance_producer', '=', True),
        ], limit=1)

        if existing_payment:
            # Paiement existe déjà, ne pas le créer en double
            return existing_payment

        # Obtenir ou créer le partner
        partner = self._get_or_create_partner()

        # Créer le paiement
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',  # Paiement sortant (vers fournisseur)
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': self.avance_producteur,
            'date': fields.Date.today(),
            'ref': _('Avance Réception %s') % self.name,
            'reception_id': self.id,  # Lien vers la réception
            'is_advance_producer': True,  # Marquer comme avance producteur
        })
        # AJOUT : Valider automatiquement le paiement
        payment.action_post()

        # Message dans le chatter
        self.message_post(
            body=_("Paiement d'avance créé : %s DA pour le producteur %s") % (
                self.avance_producteur,
                self.producteur_id.name
            )
        )

        return payment

    def action_create_advance_payment(self):
        """
        Ouvre le formulaire d'un paiement d'avance producteur existant,
        ou crée un nouveau s'il n'existe pas.
        """
        self.ensure_one()

        # Chercher s'il existe déjà un paiement avance producteur pour cette réception
        existing_payment = self.env['account.payment'].search([
            ('reception_id', '=', self.id),
            ('is_advance_producer', '=', True),
        ], limit=1)

        if existing_payment:
            # Ouvrir le paiement existant
            return {
                'name': _('Enregistrer Avance Producteur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'res_id': existing_payment.id,
                'target': 'current',
            }

        # Aucun paiement existant, créer un nouveau
        partner = self._get_or_create_partner()

        # Ouvrir le formulaire de création de paiement avec contexte pré-rempli
        return {
            'name': _('Enregistrer Avance Producteur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'context': {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': partner.id,
                'default_amount': self.avance_producteur,
                'default_date': fields.Date.today(),
                'default_ref': _('Avance Réception %s') % self.name,
                'default_reception_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_is_advance_producer': True,  # Marquer comme avance producteur
            },
            'target': 'current',
        }

    def _get_or_create_partner(self):
        """Recherche ou crée un res.partner pour le producteur"""
        self.ensure_one()

        # Rechercher un partner existant
        partner = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        if not partner:
            # Créer le partner
            partner = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        return partner

    def action_view_payments(self):
        """Affiche les paiements liés à cette réception"""
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_payments_payable')

        if self.payment_count > 1:
            action['domain'] = [('reception_id', '=', self.id)]
        elif self.payment_count == 1:
            action['views'] = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            action['res_id'] = self.payment_ids[0].id
        else:
            action['context'] = {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': self._get_or_create_partner().id,
                'default_reception_id': self.id,
                'default_ref': _('Paiement Réception %s') % self.name,
            }

        return action


class GecafleDetailsReception(models.Model):
    _name = 'gecafle.details_reception'
    _description = 'Détails Réception des Producteurs'


    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True,
        ondelete='cascade'
    )

    num_seq = fields.Integer(
        string="N° Séquentiel",
       compute="_compute_num_seq",
        store=True
    )



    producteur_id = fields.Many2one(
        related='reception_id.producteur_id',
        string="Producteur",
        store=True
    )



    date_reception = fields.Datetime(
        related='reception_id.reception_date',
        string="Date de Réception",
        store=True
    )
    designation_id = fields.Many2one(
        'gecafle.produit',
        string="Désignation",
        required=True,
        domain="[('producteur_id', '=', producteur_id)]"
    )


    # 
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type de Colis",
        required=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité",
        required=True
    )
    observation = fields.Text(
        string="Observation"
    )

    qte_colis_recue = fields.Integer(
        string="Quantité Reçus",
        required=True,
        default=1,
    )
    qte_colis_vendus = fields.Integer(
        string="Quantité Vendus",
        readonly=True,
        default=0,
    )
    qte_colis_destockes = fields.Integer(
        string="Quantité Destockés",
        readonly=True,
        default=0,
    )
    qte_colis_disponibles = fields.Integer(
        string="Quantité Disponible",
        compute="_compute_qte_disponible",
        store=True,
    )

    # Statut de la réception parente
    state = fields.Selection(related="reception_id.state", store=True)

    @api.depends('qte_colis_recue',
                 'qte_colis_vendus',
                 'qte_colis_destockes')
    def _compute_qte_disponible(self):
        """Calcule la quantité disponible en temps réel"""
        for record in self:
            record.qte_colis_disponibles = (
                    record.qte_colis_recue -
                    record.qte_colis_vendus -
                    record.qte_colis_destockes
            )

    def vendre(self, quantite):
        """
        Enregistre une vente sur cette ligne de réception
        """
        self.ensure_one()
        if quantite <= 0:
            raise ValidationError(_("La quantité à vendre doit être positive"))

        if self.qte_colis_disponibles < quantite:
            raise ValidationError(_("Stock insuffisant pour le produit! Disponible: %s, Demandé: %s")
                                  % (self.qte_colis_disponibles, quantite))

        self.qte_colis_vendus += quantite
        return True





    @api.onchange('qte_colis_recue')
    def _onchange_qte_colis_recue(self):
        if self.qte_colis_recue is not None and self.qte_colis_recue <= 0:
            return {
                'warning': {
                    'title': _("Quantité invalide"),
                    'message': _("La quantité reçue doit être strictement supérieure à zéro.",)
                }
            }

    @api.constrains('qte_colis_recue')
    def _check_qte_positive(self):
        for record in self:
            if record.qte_colis_recue <= 0:
                raise ValidationError(_("La quantité reçue doit être strictement supérieure à zéro."))

    # enlecer
    @api.depends('reception_id.details_reception_ids')
    def _compute_num_seq(self):
        for rec in self:
            if rec.reception_id:
                details = rec.reception_id.details_reception_ids.sorted(
                    key=lambda r: (r.create_date if r.create_date else datetime.min, r.id or 0)
                )
                for index, line in enumerate(details, start=1):
                    if line == rec:
                        rec.num_seq = index
                        break
            else:
                rec.num_seq = 0



class DetailsEmballageReception(models.Model):
    _name = 'gecafle.details_emballage_reception'
    _description = 'Détails des Emballages de Réception'

    reception_id = fields.Many2one(
        'gecafle.reception',
        string='Réception',
        required=True,
        ondelete='cascade'
    )

    auto_generated = fields.Boolean(
        string="Généré automatiquement",
        default=False,
    )

    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string='Emballage',
        required=True
    )
    qte_entrantes = fields.Integer(
        string='Quantité Entrante',
        required=True,
        default=1
    )
    qte_sortantes = fields.Integer(
        string='Quantité Sortante',
        required=True,
        default=1
    )

    def write(self, vals):
        # Si l'utilisateur modifie les quantités sur une ligne qui était auto générée,
        # on passe automatiquement le flag auto_generated à False afin que cette ligne ne soit plus
        # écrasée par le regroupement automatique.
        if ('qte_entrantes' in vals or 'qte_sortantes' in vals):
            vals['auto_generated'] = False
        return super(DetailsEmballageReception, self).write(vals)
