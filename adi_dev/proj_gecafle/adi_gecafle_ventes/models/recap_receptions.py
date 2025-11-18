from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class GecafleReceptionRecap(models.Model):
    _name = 'gecafle.reception.recap'
    _description = "Récapitulatif des ventes d'une réception"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'


    """" Vérification des données """

    @api.constrains('reception_id')
    def _check_reception_state(self):
        """Vérifie que la réception est dans un état approprié"""
        for record in self:
            if record.reception_id.state not in ['confirmee']:
                raise ValidationError(_(
                    "Un récapitulatif ne peut être créé que pour une réception confirmée"
                ))

    def unlink(self):
        """Empêche la suppression de récapitulatifs validés ou facturés"""
        for record in self:
            if record.state in ['valide', 'facture']:
                raise UserError(_(
                    "Impossible de supprimer le récapitulatif %s car il est %s. "
                    "Vous devez d'abord l'annuler."
                ) % (record.name, dict(self._fields['state'].selection).get(record.state)))

            if record.invoice_id:
                raise UserError(_(
                    "Impossible de supprimer le récapitulatif %s car il a une facture associée."
                ) % record.name)

            if record.bon_achat_id:
                raise UserError(_(
                    "Impossible de supprimer le récapitulatif %s car il a un bon d'achat associé."
                ) % record.name)

        return super().unlink()

    #  Cration d'une facture Production à partir du récapitulatif
    # Ajouter ces nouveaux champs
    invoice_id = fields.Many2one(
        'account.move',
        string="Facture Fournisseur",
        readonly=True,
        copy=False
    )


    invoice_count = fields.Integer(
        string="Factures",
        compute='_compute_invoice_count'
    )

    def _compute_invoice_count(self):
        for record in self:
            # Compter simplement si une facture existe
            record.invoice_count = 1 if record.invoice_id else 0

    def action_create_vendor_invoice(self):
        """Crée une facture fournisseur détaillée à partir du récapitulatif"""
        self.ensure_one()

        # Vérifier que le récapitulatif est validé
        if self.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant de créer une facture."))

        # Vérifier qu'il n'existe pas déjà une facture
        if self.invoice_count > 0:
            raise UserError(_("Une facture existe déjà pour ce récapitulatif."))

        # Rechercher le compte fournisseur pour ce producteur
        vendor = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        # Si le fournisseur n'existe pas, le créer
        if not vendor:
            vendor = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        # Préparer la description de la facture
        narration_text = _("Facture créée depuis le récapitulatif %s\n"
                           "Total ventes: %s\n"
                           "Commission: %s\n"
                           "Net à payer: %s") % (
                             self.name,
                             self.total_ventes,
                             self.total_commission,
                             self.net_a_payer
                         )

        # Créer la facture fournisseur avec la référence au récap
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': _("Bordereau N° %s - Folio %s") % (self.name, self.reception_id.name),
            'ref': _("Bordereau N° %s") % self.name,
            'recap_id': self.id,  # Lien vers le récapitulatif
            'narration': narration_text,
            'invoice_line_ids': [],
        }

        # Ligne 1 : Montant total des ventes
        invoice_line_vals = {
            'name': _("Vente de produits agricoles - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': self.total_ventes,
        }
        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # Ligne 2 : Déduction pour la commission
        commission_line_vals = {
            'name': _("Commission sur ventes - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': -self.total_commission,  # Négatif pour déduire
        }
        invoice_vals['invoice_line_ids'].append((0, 0, commission_line_vals))

        # PAS DE LIGNE POUR LES AVANCES - Elles seront gérées dans la comptabilité

        # Créer la facture
        invoice = self.env['account.move'].create(invoice_vals)

        # Lier la facture au récapitulatif
        self.invoice_id = invoice.id
        self.state = 'facture'

        # Message de confirmation
        message_body = _("Facture fournisseur créée avec succès.\n\n"
                         "Détails:\n"
                         "- Total ventes: %s\n"
                         "- Commission: %s\n"
                         "- Net à payer: %s") % (
                           self.total_ventes,
                           self.total_commission,
                           self.net_a_payer
                       )

        self.message_post(body=message_body)

        # Ouvrir la facture créée
        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }

    def action_view_invoice(self):
        """Affiche la facture liée au récapitulatif"""
        self.ensure_one()

        if self.invoice_id:
            return {
                'name': _('Facture Fournisseur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'target': 'current',
            }
        else:
            # Si pas de facture, afficher un message
            raise UserError(_("Aucune facture n'est liée à ce récapitulatif."))

    ##  informations de paiement
    # AJOUT DES NOUVEAUX CHAMPS POUR L'ÉTAT DE PAIEMENT
    avance_reception = fields.Monetary(
        string="Avance versée",
        compute='_compute_avance',
        currency_field='currency_id'
    )

    net_apres_avance = fields.Monetary(
        string="Net après avance",
        compute='_compute_avance',
        currency_field='currency_id'
    )

    @api.depends('net_a_payer', 'reception_id')
    def _compute_avance(self):
        for record in self:
            avance = record.reception_id.montant_avance if hasattr(record.reception_id, 'montant_avance') else 0.0
            record.avance_reception = avance
            record.net_apres_avance = record.net_a_payer - avance

    payment_amount_total = fields.Monetary(
        string="Montant total",
        compute='_compute_payment_info',
        currency_field='currency_id'
        # store=True
    )
    payment_state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé')
    ], string="État de paiement", compute='_compute_payment_state', store=True)

    payment_amount_due = fields.Monetary(
        string="Montant dû",
        compute='_compute_payment_info',
        currency_field='currency_id'
    )

    payment_amount_paid = fields.Monetary(
        string="Montant payé",
        compute='_compute_payment_info',
        currency_field='currency_id'
    )

    payment_percentage = fields.Float(
        string="% Payé",
        compute='_compute_payment_info',
        digits=(5, 2)
    )

    # AJOUT DES MÉTHODES DE CALCUL POUR L'ÉTAT DE PAIEMENT
    @api.depends('state', 'invoice_id.payment_state', 'bon_achat_id.state', 'net_a_payer')
    def _compute_payment_state(self):
        """Calcule l'état de paiement basé sur la facture ou le bon d'achat"""
        for record in self:
            if record.state == 'brouillon':
                record.payment_state = 'not_paid'
            elif record.invoice_id:
                # Si une facture existe, on se base sur son état de paiement
                if record.invoice_id.payment_state == 'paid':
                    record.payment_state = 'paid'
                elif record.invoice_id.payment_state == 'partial':
                    record.payment_state = 'partial'
                else:
                    record.payment_state = 'not_paid'
            elif record.bon_achat_id:
                # Si un bon d'achat existe, on se base sur son état
                if record.bon_achat_id.state == 'paye':
                    record.payment_state = 'paid'
                else:
                    record.payment_state = 'not_paid'
            else:
                # Si le récap est validé mais sans facture ni bon d'achat
                record.payment_state = 'not_paid'

    @api.depends('net_a_payer', 'invoice_id', 'invoice_id.amount_residual', 'bon_achat_id', 'bon_achat_id.state')
    def _compute_payment_info(self):
        """Calcule les montants de paiement"""
        for record in self:
            total_amount = record.net_a_payer
            amount_paid = 0
            record.payment_amount_total = 0

            if record.invoice_id:
                # Pour une facture, calculer le montant payé
                amount_paid = total_amount - record.invoice_id.amount_residual
            elif record.bon_achat_id and record.bon_achat_id.state == 'paye':
                # Pour un bon d'achat payé, tout est payé
                amount_paid = total_amount

            record.payment_amount_due = total_amount - amount_paid
            record.payment_amount_paid = amount_paid
            # Ne PAS multiplier par 100 car le widget "percentage" le fait automatiquement
            record.payment_percentage = (amount_paid / total_amount) if total_amount else 0
            record.payment_amount_total = record.payment_amount_due + record.payment_amount_paid

    """ """
    bon_achat_id = fields.Many2one(
        'gecafle.bon.achat',
        string="Bon d'Achat",
        readonly=True,
        copy=False
    )

    bon_achat_count = fields.Integer(
        string="Bons d'Achat",
        compute='_compute_bon_achat_count'
    )

    def _compute_bon_achat_count(self):
        for record in self:
            record.bon_achat_count = self.env['gecafle.bon.achat'].search_count([
                ('recap_id', '=', record.id)
            ])

    def action_create_bon_achat(self):
        """Crée un bon d'achat à partir du récapitulatif"""
        self.ensure_one()

        # Vérifier que le récapitulatif est validé et qu'il n'existe pas déjà un bon d'achat
        if self.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant de créer un bon d'achat."))

        if self.bon_achat_count > 0:
            raise UserError(_("Un bon d'achat existe déjà pour ce récapitulatif."))

        # Créer le bon d'achat
        bon_achat = self.env['gecafle.bon.achat'].create({
            'producteur_id': self.producteur_id.id,
            'reception_id': self.reception_id.id,
            'recap_id': self.id,
            'date': fields.Date.today(),
            'line_ids': [(0, 0, {
                'name': _("Montant bordereau N° %s") % self.reception_id.name,
                'quantite': 1,
                'prix_unitaire': self.net_a_payer,
            })]
        })

        # Mettre à jour la référence dans le récapitulatif
        self.bon_achat_id = bon_achat.id

        # Ouvrir le bon d'achat
        return {
            'name': _('Bon d\'Achat'),
            'view_mode': 'form',
            'res_model': 'gecafle.bon.achat',
            'res_id': bon_achat.id,
            'type': 'ir.actions.act_window',
        }

    def action_view_bon_achat(self):
        """Affiche le bon d'achat lié au récapitulatif"""
        self.ensure_one()

        bon_achat = self.env['gecafle.bon.achat'].search([
            ('recap_id', '=', self.id)
        ], limit=1)

        if bon_achat:
            return {
                'name': _('Bon d\'Achat'),
                'view_mode': 'form',
                'res_model': 'gecafle.bon.achat',
                'res_id': bon_achat.id,
                'type': 'ir.actions.act_window',
            }

        return {
            'name': _('Bons d\'Achat'),
            'view_mode': 'tree,form',
            'res_model': 'gecafle.bon.achat',
            'domain': [('recap_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_recap_id': self.id},
        }

    name = fields.Char(string="Référence", readonly=True, copy=False, default='Nouveau')
    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception source",
        required=True,
        readonly=True
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        related='reception_id.producteur_id',
        store=True,
        readonly=True
    )
    date_reception = fields.Datetime(
        string="Date réception",
        related='reception_id.reception_date',
        store=True,
        readonly=True
    )
    date_creation = fields.Date(
        string="Date récapitulatif",
        default=fields.Date.context_today,
        readonly=True
    )
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('facture', 'Facturé'),
    ], string="État", default='brouillon', tracking=True)

    # Lignes du récapitulatif (regroupement par produit/qualité/prix)
    recap_line_ids = fields.One2many(
        'gecafle.reception.recap.line',
        'recap_id',
        string="Lignes récapitulatives"
    )

    # Lignes originales de la réception
    original_line_ids = fields.One2many(
        'gecafle.reception.recap.original',
        'recap_id',
        string="Lignes de réception"
    )

    # Lignes de vente associées
    sale_line_ids = fields.One2many(
        'gecafle.reception.recap.sale',
        'recap_id',
        string="Détails des ventes"
    )

    # Totaux
    total_ventes = fields.Monetary(
        string="Total des ventes",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_commission = fields.Monetary(
        string="Total commission",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    net_a_payer = fields.Monetary(
        string="Net à payer",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='company_id.currency_id',
        readonly=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.reception.recap') or 'REC/'
        return super().create(vals)

    @api.depends('recap_line_ids.montant_vente', 'recap_line_ids.montant_commission')
    def _compute_totals(self):
        for record in self:
            record.total_ventes = sum(line.montant_vente for line in record.recap_line_ids)
            record.total_commission = sum(line.montant_commission for line in record.recap_line_ids)
            record.net_a_payer = record.total_ventes - record.total_commission

    def generate_recap_lines(self):
        """Génère les lignes récapitulatives depuis les ventes"""
        self.ensure_one()

        # Supprimer les lignes existantes
        self.recap_line_ids.unlink()

        # Dictionnaire pour regrouper par produit/qualité/prix
        grouped_lines = {}

        # Récupérer toutes les lignes de vente liées à cette réception
        sale_lines = self.env['gecafle.details_ventes'].search([
            ('reception_id', '=', self.reception_id.id),
            ('vente_id.state', '=', 'valide')
        ])

        for line in sale_lines:
            # Clé de regroupement: (produit_id, qualité_id, prix_kg)
            key = (line.produit_id.id, line.qualite_id.id if line.qualite_id else False, line.prix_unitaire)

            if key not in grouped_lines:
                grouped_lines[key] = {
                    'produit_id': line.produit_id.id,
                    'qualite_id': line.qualite_id.id if line.qualite_id else False,
                    'type_colis_id': line.type_colis_id.id,
                    'prix_unitaire': line.prix_unitaire,
                    'nombre_colis': 0,
                    'poids_net': 0.0,
                    'montant_vente': 0.0,
                    'taux_commission': line.taux_commission,
                    'montant_commission': 0.0,
                }

            grouped_lines[key]['nombre_colis'] += line.nombre_colis
            grouped_lines[key]['poids_net'] += line.poids_net
            grouped_lines[key]['montant_vente'] += line.montant_net
            grouped_lines[key]['montant_commission'] += line.montant_commission

        # Créer les lignes récapitulatives
        for values in grouped_lines.values():
            self.env['gecafle.reception.recap.line'].create({
                'recap_id': self.id,
                'produit_id': values['produit_id'],
                'qualite_id': values['qualite_id'],
                'type_colis_id': values['type_colis_id'],
                'prix_unitaire': values['prix_unitaire'],
                'nombre_colis': values['nombre_colis'],
                'poids_net': values['poids_net'],
                'montant_vente': values['montant_vente'],
                'taux_commission': values['taux_commission'],
                'montant_commission': values['montant_commission'],
            })

    def generate_original_lines(self):
        """Copie les lignes de réception originales"""
        self.ensure_one()

        # Supprimer les lignes existantes
        self.original_line_ids.unlink()

        # Récupérer les lignes de réception
        for line in self.reception_id.details_reception_ids:
            self.env['gecafle.reception.recap.original'].create({
                'recap_id': self.id,
                'designation_id': line.designation_id.id,
                'qualite_id': line.qualite_id.id if line.qualite_id else False,
                'type_colis_id': line.type_colis_id.id,
                #  'poids_colis': line.poids_colis,
                #  'qte_colis_recue': line.qte_colis_recue,
                #  'poids_brut': line.poids_brut,
                #  'poids_net': line.poids_net,
                'qte_colis_vendus': line.qte_colis_vendus,
                'qte_colis_destockes': line.qte_colis_destockes,
            })

    def generate_sale_lines(self):
        """Copie les lignes de vente liées"""
        self.ensure_one()

        # Supprimer les lignes existantes
        self.sale_line_ids.unlink()

        # Récupérer toutes les lignes de vente liées à cette réception
        sale_lines = self.env['gecafle.details_ventes'].search([
            ('reception_id', '=', self.reception_id.id),
            ('vente_id.state', '=', 'valide')
        ])

        for line in sale_lines:
            self.env['gecafle.reception.recap.sale'].create({
                'recap_id': self.id,
                'vente_id': line.vente_id.id,
                'client_id': line.vente_id.client_id.id,
                'date_vente': line.vente_id.date_vente,
                'produit_id': line.produit_id.id,
                'qualite_id': line.qualite_id.id if line.qualite_id else False,
                'type_colis_id': line.type_colis_id.id,
                'nombre_colis': line.nombre_colis,
                'poids_net': line.poids_net,
                'prix_unitaire': line.prix_unitaire,
                'montant_net': line.montant_net,
                'taux_commission': line.taux_commission,
                'montant_commission': line.montant_commission,
            })

    def action_validate(self):
        """Valide le récapitulatif"""
        self.ensure_one()
        self.state = 'valide'

    #   Nous allons ajouté un bouton qui mène vers la reception pour voir les détails des ventes
    # Ajouter une méthode pour naviguer vers la réception
    def action_view_reception(self):
        """Ouvre la réception source en vue formulaire"""
        self.ensure_one()

        return {
            'name': _('Réception source'),
            'view_mode': 'form',
            'res_model': 'gecafle.reception',
            'res_id': self.reception_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',  # Ouvre dans l'onglet actuel
        }


class GecafleReceptionRecapLine(models.Model):
    _name = 'gecafle.reception.recap.line'
    _description = "Ligne récapitulative des ventes"

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True,
        ondelete='cascade'
    )
    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        required=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type colis",
        required=True
    )
    prix_unitaire = fields.Float(
        string="Prix/Unitaire",
        digits=(10, 2)
    )
    nombre_colis = fields.Integer(
        string="Nombre de colis",
        default=0
    )
    poids_net = fields.Float(
        string="Poids net",
        digits=(10, 2)
    )
    montant_vente = fields.Monetary(
        string="Montant vente",
        currency_field='currency_id'
    )
    taux_commission = fields.Float(
        string="Taux commission (%)",
        digits=(5, 2)
    )
    montant_commission = fields.Monetary(
        string="Montant commission",
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='recap_id.currency_id'
    )


class GecafleReceptionRecapOriginal(models.Model):
    _name = 'gecafle.reception.recap.original'
    _description = "Ligne de réception originale"

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True,
        ondelete='cascade'
    )
    designation_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        required=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type colis",
        required=True
    )
    poids_colis = fields.Float(
        string="Poids colis",
        digits=(10, 2)
    )
    qte_colis_recue = fields.Integer(
        string="Qté reçue",
        default=0
    )
    poids_brut = fields.Float(
        string="Poids brut",
        digits=(10, 2)
    )
    poids_net = fields.Float(
        string="Poids net",
        digits=(10, 2)
    )
    qte_colis_vendus = fields.Integer(
        string="Qté vendue",
        default=0
    )
    qte_colis_destockes = fields.Integer(
        string="Qté destockée",
        default=0
    )


class GecafleReceptionRecapSale(models.Model):
    _name = 'gecafle.reception.recap.sale'
    _description = "Détail des ventes par réception"

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif",
        required=True,
        ondelete='cascade'
    )
    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True
    )
    client_id = fields.Many2one(
        'gecafle.client',
        string="Client"
    )
    date_vente = fields.Datetime(
        string="Date vente"
    )
    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        required=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type colis"
    )
    nombre_colis = fields.Integer(
        string="Nombre de colis",
        default=0
    )
    poids_net = fields.Float(
        string="Poids net",
        digits=(10, 2)
    )
    prix_unitaire = fields.Float(
        string="Prix/Unitaire",
        digits=(10, 2)
    )
    montant_net = fields.Monetary(
        string="Montant net",
        currency_field='currency_id'
    )
    taux_commission = fields.Float(
        string="Taux commission (%)",
        digits=(5, 2)
    )
    montant_commission = fields.Monetary(
        string="Montant commission",
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='recap_id.currency_id'
    )

