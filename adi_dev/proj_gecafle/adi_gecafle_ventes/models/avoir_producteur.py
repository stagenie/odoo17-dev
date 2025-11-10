# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleAvoirProducteur(models.Model):
    _name = 'gecafle.avoir.producteur'
    _description = 'Avoir Producteur'
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
        ('annule', 'Annulé'),
    ], string="État", default='brouillon', tracking=True)

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        required=True,
        readonly=True,
        states={'brouillon': [('readonly', False)]}
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception source",
        readonly=True,
        domain=[('state', '=', 'confirmee')]
    )

    # Lien vers l'avoir client source
    avoir_client_id = fields.Many2one(
        'gecafle.avoir.client',
        string="Avoir client source",
        readonly=True,
        ondelete='cascade'
    )

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente source",
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
        required=True
    )

    # Montant simple sans calcul
    montant_total = fields.Monetary(
        string="Montant Total",
        required=True,
        currency_field='currency_id',
        tracking=True
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

    notes = fields.Text(string="Notes internes")

    # Champ pour la note de crédit liée
    credit_note_id = fields.Many2one(
        'account.move',
        string="Note de crédit",
        readonly=True,
        copy=False,
        help="Note de crédit (avoir) créée à partir de cet avoir producteur"
    )

    # Champs pour le suivi du paiement
    credit_note_state = fields.Selection(
        string="État de la note de crédit",
        related='credit_note_id.state',
        readonly=True,
        store=True
    )

    credit_note_payment_state = fields.Selection(
        string="État de paiement",
        related='credit_note_id.payment_state',
        readonly=True,
        store=True
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

    # Compteur pour le smart button
    credit_note_count = fields.Integer(
        string="Notes de crédit",
        compute='_compute_credit_note_count'
    )

    @api.depends('credit_note_id')
    def _compute_credit_note_count(self):
        for record in self:
            record.credit_note_count = 1 if record.credit_note_id else 0

    @api.depends('credit_note_id', 'credit_note_id.amount_residual', 'montant_total')
    def _compute_amount_paid(self):
        for record in self:
            if record.credit_note_id:
                record.credit_note_amount_paid = record.montant_total - record.credit_note_amount_residual
            else:
                record.credit_note_amount_paid = 0

    @api.depends('credit_note_payment_state')
    def _compute_is_paid(self):
        for record in self:
            record.is_paid = record.credit_note_payment_state == 'paid'

    @api.model
    def create(self, vals):
        """Création simple de l'avoir producteur sans liaison automatique"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.avoir.producteur') or 'AVP/'

        # Créer l'avoir simplement
        avoir = super(GecafleAvoirProducteur, self).create(vals)

        # Message de création
        avoir.message_post(
            body=_("Avoir producteur créé : %s DA") % avoir.montant_total,
            subtype_xmlid='mail.mt_note'
        )

        return avoir

    def action_validate(self):
        """Valide l'avoir producteur"""
        for record in self:
            if record.state == 'brouillon':
                record.state = 'valide'
                # Créer automatiquement la note de crédit si configuré
                if not record.credit_note_id:
                    record._create_credit_note()

                record.message_post(
                    body=_("Avoir validé"),
                    subtype_xmlid='mail.mt_note'
                )

    def action_draft(self):
        """Remet l'avoir en brouillon"""
        for record in self:
            if record.state == 'annule':
                record.state = 'brouillon'

    @api.constrains('montant_total')
    def _check_montant_positif(self):
        for record in self:
            if record.montant_total <= 0:
                raise ValidationError(_("Le montant de l'avoir doit être positif."))

    def _create_credit_note(self):
        """Crée une note de crédit (avoir) dans la comptabilité"""
        self.ensure_one()

        # Rechercher ou créer le partner pour le producteur
        partner = self._get_or_create_partner()

        # Créer la note de crédit avec la référence vers l'avoir producteur
        credit_note_vals = {
            'move_type': 'in_refund',  # Avoir fournisseur
            'partner_id': partner.id,
            'invoice_date': self.date,
            'ref': self.name,
            'invoice_origin': _("Avoir producteur %s") % self.name,
            'invoice_line_ids': [(0, 0, {
                'name': self.description or _("Avoir sur marchandises"),
                'quantity': 1,
                'price_unit': self.montant_total,
            })],
        }

        credit_note = self.env['account.move'].create(credit_note_vals)
        self.credit_note_id = credit_note.id

        return credit_note

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

    def action_view_vendor_credit(self):
        """Ouvre la note de crédit liée"""
        self.ensure_one()

        if not self.credit_note_id:
            # Si pas de note de crédit, la créer
            credit_note = self._create_credit_note()
            self.credit_note_id = credit_note.id

        # Ouvrir la vue formulaire de la note de crédit
        return {
            'name': _('Note de crédit'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.credit_note_id.id,
            'target': 'current',
        }

    def action_print_avoir(self):
        """Imprime l'avoir producteur"""
        self.ensure_one()
        return self.env.ref('adi_gecafle_ventes.action_report_avoir_producteur').report_action(self)

    def action_cancel(self):
        """Annule l'avoir avec contrôles stricts"""
        for record in self:
            if record.state not in ('brouillon', 'valide'):
                continue

            # Vérifier la note de crédit
            if record.credit_note_id:
                if record.credit_note_id.state == 'posted':
                    raise UserError(_(
                        "Impossible d'annuler l'avoir %s car la note de crédit associée est validée. "
                        "Vous devez d'abord annuler la note de crédit dans la comptabilité."
                    ) % record.name)

            record.state = 'annule'
            record.message_post(
                body=_("Avoir annulé par %s") % self.env.user.name,
                message_type='notification'
            )

    is_linked_to_recap = fields.Boolean(
        string="Temp field",
        default=False,
        store=False  # Important : ne pas stocker en base
    )
