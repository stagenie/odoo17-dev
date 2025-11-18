# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleAvoirClient(models.Model):
    _name = 'gecafle.avoir.client'
    _description = 'Avoir Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    name = fields.Char(
        string="Numéro",
        readonly=True,
        copy=False,
        default='Nouveau'
    )

    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('comptabilise', 'Comptabilisé'),
        ('annule', 'Annulé'),
    ], string="État", default='brouillon', tracking=True)

    # Dans models/avoir_client.py, ajouter ces méthodes :

    def unlink(self):
        """Empêche la suppression d'avoirs dans certains cas"""
        for record in self:
            # Interdire la suppression si l'avoir n'est pas en brouillon
            if record.state != 'brouillon':
                raise UserError(_(
                    "Impossible de supprimer l'avoir %s car il n'est pas en brouillon (état: %s)."
                ) % (record.name, dict(self._fields['state'].selection).get(record.state)))

            # Interdire si une note de crédit existe
            if record.credit_note_id:
                raise UserError(_(
                    "Impossible de supprimer l'avoir %s car une note de crédit comptable existe (%s)."
                ) % (record.name, record.credit_note_id.name))

            # Interdire si des avoirs producteurs existent
            if record.avoir_producteur_ids:
                raise UserError(_(
                    "Impossible de supprimer l'avoir %s car il a généré %d avoir(s) producteur(s)."
                ) % (record.name, len(record.avoir_producteur_ids)))

        return super().unlink()

    def action_cancel(self):
        """Annule l'avoir avec contrôles stricts"""
        for record in self:
            if record.state == 'annule':
                continue

            # Vérifier la note de crédit
            if record.credit_note_id:
                if record.credit_note_id.state == 'posted':
                    raise UserError(_(
                        "Impossible d'annuler l'avoir %s car la note de crédit est validée.\n"
                        "Vous devez d'abord annuler la note de crédit dans la comptabilité."
                    ) % record.name)

                if record.credit_note_id.payment_state in ('paid', 'partial'):
                    raise UserError(_(
                        "Impossible d'annuler l'avoir %s car des paiements ont été enregistrés."
                    ) % record.name)

            # Vérifier les avoirs producteurs
            if record.avoir_producteur_ids:
                non_annules = record.avoir_producteur_ids.filtered(lambda a: a.state != 'annule')
                if non_annules:
                    raise UserError(_(
                        "Impossible d'annuler l'avoir client %s.\n"
                        "Les avoirs producteurs suivants doivent d'abord être annulés : %s"
                    ) % (record.name, ', '.join(non_annules.mapped('name'))))

            # Si tout est OK, annuler
            record.state = 'annule'
            record.message_post(body=_("Avoir annulé par %s") % self.env.user.name)

    @api.constrains('montant_avoir')
    def _check_montant_coherence(self):
        """Vérifie la cohérence du montant avec les avoirs producteurs"""
        for record in self:
            if record.avoir_producteur_ids and record.state != 'brouillon':
                total_producteurs = sum(record.avoir_producteur_ids.mapped('montant_total'))
                if abs(total_producteurs - record.montant_avoir) > 0.01:
                    raise ValidationError(_(
                        "Le montant de l'avoir client (%s) ne correspond pas au total des avoirs producteurs (%s)"
                    ) % (record.montant_avoir, total_producteurs))


    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente source",
        required=True,
        readonly=True,
        ondelete='restrict'
    )

    client_id = fields.Many2one(
        'gecafle.client',
        string="Client",
        related='vente_id.client_id',
        store=True,
        readonly=True
    )

    type_avoir = fields.Selection([
        ('non_vendu', 'Marchandise non vendue'),
        ('qualite', 'Problème de qualité'),
        ('perte', 'Perte/Détérioration'),
        ('accord_commercial', 'Accord commercial'),
        ('consigne', 'Retour consigne'),
    ], string="Type d'avoir", required=True, default='non_vendu')

    description = fields.Text(
        string="Description",
        required=True,
        help="Décrivez la raison de l'avoir"
    )

    # Montants
    montant_vente_origine = fields.Monetary(
        string="Montant vente d'origine",
        related='vente_id.montant_total_a_payer',
        readonly=True,
        currency_field='currency_id'
    )

    montant_avoir = fields.Monetary(
        string="Montant de l'avoir",
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    generer_avoirs_producteurs = fields.Boolean(
        string="Générer avoirs producteurs",
        default=True,
        help="Si coché, génère automatiquement les avoirs pour chaque producteur"
    )

    # Avoirs producteurs générés
    avoir_producteur_ids = fields.One2many(
        'gecafle.avoir.producteur',
        'avoir_client_id',
        string="Avoirs producteurs",
        readonly=True
    )

    avoir_producteur_count = fields.Integer(
        string="Nombre d'avoirs producteurs",
        compute='_compute_avoir_producteur_count'
    )

    # Note de crédit comptable
    credit_note_id = fields.Many2one(
        'account.move',
        string="Note de crédit",
        readonly=True,
        copy=False
    )

    # AJOUT : Champs manquants pour le suivi du paiement
    credit_note_count = fields.Integer(
        string="Notes de crédit",
        compute='_compute_credit_note_count'
    )

    credit_note_state = fields.Selection(
        string="État note de crédit",
        related='credit_note_id.state',
        readonly=True
    )

    credit_note_payment_state = fields.Selection(
        string="État paiement",
        related='credit_note_id.payment_state',
        readonly=True
    )

    credit_note_amount_residual = fields.Monetary(
        string="Montant restant dû",
        related='credit_note_id.amount_residual',
        readonly=True,
        currency_field='currency_id'
    )

    credit_note_amount_paid = fields.Monetary(
        string="Montant payé",
        compute='_compute_amount_paid',
        currency_field='currency_id'
    )

    is_paid = fields.Boolean(
        string="Est payé",
        compute='_compute_is_paid',
        store=True
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

    # Champ pour marquer l'impression
    est_imprimee = fields.Boolean(
        string="Est imprimé",
        default=False
    )

    @api.depends('avoir_producteur_ids')
    def _compute_avoir_producteur_count(self):
        for record in self:
            record.avoir_producteur_count = len(record.avoir_producteur_ids)

    @api.depends('credit_note_id')
    def _compute_credit_note_count(self):
        for record in self:
            record.credit_note_count = 1 if record.credit_note_id else 0

    @api.depends('credit_note_id', 'credit_note_id.amount_residual', 'montant_avoir')
    def _compute_amount_paid(self):
        for record in self:
            if record.credit_note_id:
                record.credit_note_amount_paid = record.montant_avoir - record.credit_note_amount_residual
            else:
                record.credit_note_amount_paid = 0

    @api.depends('credit_note_payment_state')
    def _compute_is_paid(self):
        for record in self:
            record.is_paid = record.credit_note_payment_state == 'paid'

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.avoir.client') or 'AVC/'
        return super().create(vals)

    @api.constrains('montant_avoir', 'montant_vente_origine')
    def _check_montant_avoir(self):
        for record in self:
            if record.montant_avoir > record.montant_vente_origine:
                raise ValidationError(_("Le montant de l'avoir ne peut pas dépasser le montant de la vente d'origine."))

    def action_validate(self):
        """Valide l'avoir et génère les avoirs producteurs si demandé"""
        for record in self:
            if record.state == 'brouillon':
                record.state = 'valide'

                # Générer les avoirs producteurs si l'option est activée
                if record.generer_avoirs_producteurs:
                    record._generer_avoirs_producteurs()

                # Message de confirmation
                record.message_post(body=_("Avoir client validé. Montant : %s") % record.montant_avoir)

    def _generer_avoirs_producteurs(self):
        """Génère automatiquement les avoirs producteurs avec répartition égale"""
        self.ensure_one()

        # Récupérer tous les producteurs uniques de la vente
        producteurs = self.vente_id.detail_vente_ids.mapped('producteur_id')

        if not producteurs:
            return

        # Calculer le montant par producteur (répartition égale)
        montant_par_producteur = self.montant_avoir / len(producteurs)

        # Créer un avoir pour chaque producteur
        for producteur in producteurs:
            self.env['gecafle.avoir.producteur'].create({
                'producteur_id': producteur.id,
                'avoir_client_id': self.id,
                'vente_id': self.vente_id.id,
                'date': self.date,
                'type_avoir': self.type_avoir,
                'description': _("Avoir suite à %s - Vente %s") % (self.description, self.vente_id.name),
                'montant_total': montant_par_producteur,
            })

    def action_cancel(self):
        """Annule l'avoir"""
        for record in self:
            if record.state in ('brouillon', 'valide'):
                # Vérifier si une note de crédit existe
                if record.credit_note_id:
                    if record.credit_note_id.state == 'posted':
                        raise UserError(_(
                            "Impossible d'annuler cet avoir car la note de crédit associée est validée. "
                            "Vous devez d'abord annuler la note de crédit dans la comptabilité."
                        ))

                record.state = 'annule'
                record.message_post(body=_("Avoir client annulé"))

    def action_draft(self):
        """Remet l'avoir en brouillon"""
        for record in self:
            if record.state == 'annule':
                record.state = 'brouillon'

    def action_print_avoir(self):
        """Imprime l'avoir client"""
        self.ensure_one()

        return self.env.ref('adi_gecafle_ventes.action_report_avoir_client').report_action(self)

    def action_create_credit_note(self):
        """Crée une note de crédit client dans la comptabilité"""
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("L'avoir doit être validé avant de créer une note de crédit."))

        if self.credit_note_id:
            raise UserError(_("Une note de crédit existe déjà pour cet avoir."))

        # Rechercher ou créer le partner
        partner = self._get_or_create_partner()

        # Rechercher le compte comptable approprié
        account = self._get_credit_note_account()

        # Créer la note de crédit
        credit_note_vals = {
            'move_type': 'out_refund',  # Avoir client
            'partner_id': partner.id,
            'invoice_date': self.date,
            'ref': self.name,
            'invoice_origin': _("Avoir client %s - Vente %s") % (self.name, self.vente_id.name),
            'narration': _("Type d'avoir: %s\nMotif: %s") % (
                dict(self._fields['type_avoir'].selection).get(self.type_avoir),
                self.description
            ),
            'invoice_line_ids': [(0, 0, {
                'name': _("Avoir - %s") % self.description,
                'quantity': 1,
                'price_unit': self.montant_avoir,
                'account_id': account.id,
            })],
        }

        credit_note = self.env['account.move'].create(credit_note_vals)
        self.credit_note_id = credit_note.id
        self.state = 'comptabilise'

        # Message de confirmation
        self.message_post(body=_("Note de crédit créée : %s") % credit_note.name)

        return {
            'name': _('Note de crédit'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': credit_note.id,
            'target': 'current',
        }

    def _get_or_create_partner(self):
        """Recherche ou crée un res.partner pour le client"""
        self.ensure_one()

        # Rechercher un partner existant
        partner = self.env['res.partner'].search([
            ('name', '=', self.client_id.name),
            ('customer_rank', '>', 0)
        ], limit=1)

        if not partner:
            # Créer le partner
            partner = self.env['res.partner'].create({
                'name': self.client_id.name,
                'phone': self.client_id.tel_mob,
                'street': self.client_id.adresse,
                'customer_rank': 1,
                'is_company': False,
                'lang': 'fr_FR' if self.client_id.langue_client == 'fr' else 'ar_DZ',
            })

        return partner

    def _get_credit_note_account(self):
        """Retourne le compte comptable pour la note de crédit"""
        # Rechercher le compte de revenus par défaut
        account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not account:
            raise UserError(_("Aucun compte de revenus trouvé. Veuillez configurer la comptabilité."))

        return account

    def action_view_credit_note(self):
        """Affiche la note de crédit liée à l'avoir"""
        self.ensure_one()

        if not self.credit_note_id:
            raise UserError(_("Aucune note de crédit n'est liée à cet avoir."))

        return {
            'name': _('Note de crédit'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.credit_note_id.id,
            'target': 'current',
        }

    def action_register_payment(self):
        """Ouvre l'assistant de paiement pour la note de crédit"""
        self.ensure_one()

        if not self.credit_note_id:
            raise UserError(_("Aucune note de crédit n'est liée à cet avoir."))

        if self.credit_note_id.state != 'posted':
            raise UserError(_("La note de crédit doit être validée avant d'enregistrer un paiement."))

        return self.credit_note_id.action_register_payment()

    def action_view_vendor_credits(self):
        """Affiche les avoirs producteurs liés à cet avoir client"""
        self.ensure_one()

        if not self.avoir_producteur_ids:
            raise UserError(_("Aucun avoir producteur n'a été généré pour cet avoir client."))

        # Si un seul avoir producteur, ouvrir directement le formulaire
        if len(self.avoir_producteur_ids) == 1:
            return {
                'name': _('Avoir Producteur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.avoir.producteur',
                'res_id': self.avoir_producteur_ids[0].id,
                'target': 'current',
            }
        else:
            # Si plusieurs avoirs producteurs, ouvrir la liste
            return {
                'name': _('Avoirs Producteurs'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'gecafle.avoir.producteur',
                'domain': [('id', 'in', self.avoir_producteur_ids.ids)],
                'target': 'current',
                'context': {
                    'default_avoir_client_id': self.id,
                    'default_vente_id': self.vente_id.id if self.vente_id else False,
                }
            }
