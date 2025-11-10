# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleConsigneRetour(models.Model):
    _name = 'gecafle.consigne.retour'
    _description = 'Retour de Consigne'
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
        ('avoir_cree', 'Avoir créé'),
        ('annule', 'Annulé'),
    ], string="État", default='brouillon', tracking=True)

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente source",
        required=False,
        domain="[('state', '=', 'valide'), ('consigne_appliquee', '=', True), ('etat_consigne', '!=', 'rendu')]",
        ondelete='restrict'
    )

    client_id = fields.Many2one(
        'gecafle.client',
        string="Client",
        compute='_compute_client_id',
        store=True,
        readonly=False,
        required=False
    )

    # Lignes de retour
    retour_line_ids = fields.One2many(
        'gecafle.consigne.retour.line',
        'retour_id',
        string="Emballages à retourner",
        copy=False
    )

    # Montants
    montant_total_consigne = fields.Monetary(
        string="Montant total consigne",
        compute='_compute_montants',
        store=True,
        currency_field='currency_id'
    )

    montant_a_rembourser = fields.Monetary(
        string="Montant à rembourser",
        compute='_compute_montants',
        store=True,
        currency_field='currency_id'
    )

    avoir_client_id = fields.Many2one(
        'gecafle.avoir.client',
        string="Avoir client",
        readonly=True,
        copy=False
    )

    # IMPORTANT : Récupérer la note de crédit depuis l'avoir client
    credit_note_id = fields.Many2one(
        'account.move',
        string="Note de crédit",
        compute='_compute_credit_note_info',
        store=True,
        help="Note de crédit comptable créée pour le remboursement"
    )

    credit_note_count = fields.Integer(
        string="Notes de crédit",
        compute='_compute_credit_note_count'
    )

    # État de paiement depuis l'avoir client
    # État de paiement depuis l'avoir client
    credit_note_state = fields.Selection(
        string="État note de crédit",
        related='credit_note_id.state',
        readonly=True,
        store=True
    )

    credit_note_payment_state = fields.Selection(
        string="État paiement",
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

    notes = fields.Text(
        string="Notes",
        help="Notes internes sur le retour"
    )

    # NOUVELLE MÉTHODE : Récupérer les infos de paiement depuis l'avoir client
    @api.depends('avoir_client_id', 'avoir_client_id.credit_note_id')
    def _compute_credit_note_info(self):
        for record in self:
            if record.avoir_client_id and record.avoir_client_id.credit_note_id:
                record.credit_note_id = record.avoir_client_id.credit_note_id.id
            else:
                record.credit_note_id = False

    @api.depends('credit_note_id', 'credit_note_id.amount_residual', 'montant_a_rembourser')
    def _compute_amount_paid(self):
        for record in self:
            if record.credit_note_id:
                record.credit_note_amount_paid = record.montant_a_rembourser - (record.credit_note_amount_residual or 0)
            else:
                record.credit_note_amount_paid = 0

    @api.depends('credit_note_payment_state')
    def _compute_is_paid(self):
        for record in self:
            record.is_paid = record.credit_note_payment_state == 'paid'

    @api.depends('credit_note_id')
    def _compute_credit_note_count(self):
        for record in self:
            record.credit_note_count = 1 if record.credit_note_id else 0

    # Méthodes de contrôle et suppression
    def unlink(self):
        """Empêche la suppression des retours de consigne"""
        for record in self:
            if record.state != 'brouillon':
                raise UserError(_(
                    "Impossible de supprimer le retour %s car il n'est pas en brouillon."
                ) % record.name)

            if record.avoir_client_id:
                raise UserError(_(
                    "Impossible de supprimer le retour %s car un avoir client a été créé."
                ) % record.name)

            if record.credit_note_id:
                raise UserError(_(
                    "Impossible de supprimer le retour %s car une note de crédit existe."
                ) % record.name)

        return super().unlink()

    def action_cancel(self):
        """Annule le retour avec vérifications"""
        for record in self:
            if record.state == 'annule':
                continue

            # Interdire si avoir créé
            if record.state == 'avoir_cree':
                raise UserError(_(
                    "Impossible d'annuler le retour %s car l'avoir a été créé.\n"
                    "Vous devez d'abord annuler l'avoir client."
                ) % record.name)

            # Vérifier la note de crédit
            if record.credit_note_id and record.credit_note_id.state != 'draft':
                raise UserError(_(
                    "Impossible d'annuler le retour %s car la note de crédit est validée."
                ) % record.name)

            # Vérifier l'état de la vente
            if record.vente_id and record.vente_id.etat_consigne == 'rendu':
                # Remettre l'état de consigne à non rendu
                record.vente_id.with_context(allow_adjustment=True).write({
                    'etat_consigne': 'non_rendu'
                })

            record.state = 'annule'
            record.message_post(body=_("Retour annulé"))

    @api.constrains('retour_line_ids')
    def _check_lines_coherence(self):
        """Vérifie la cohérence des lignes de retour"""
        for record in self:
            if record.state != 'brouillon':
                # Interdire la modification des lignes après validation
                if self._context.get('check_lines_modification'):
                    raise ValidationError(_(
                        "Impossible de modifier les lignes après validation du retour."
                    ))

    @api.model
    def create(self, vals):
        """Création avec gestion du numéro et des lignes"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.consigne.retour') or 'RC/'

        # Si on a une vente_id mais pas de lignes, les créer automatiquement
        if vals.get('vente_id') and not vals.get('retour_line_ids'):
            vente = self.env['gecafle.vente'].browse(vals['vente_id'])
            lines_data = self._prepare_lines_from_vente(vente)
            if lines_data:
                vals['retour_line_ids'] = lines_data

        return super().create(vals)

    def write(self, vals):
        """Override write pour gérer le changement de vente"""
        # Si on change la vente_id, recréer les lignes
        if 'vente_id' in vals and vals['vente_id']:
            for record in self:
                if record.state == 'brouillon':
                    # Supprimer les lignes existantes
                    record.retour_line_ids.unlink()
                    # Créer les nouvelles lignes
                    vente = self.env['gecafle.vente'].browse(vals['vente_id'])
                    lines_data = record._prepare_lines_from_vente(vente)
                    if lines_data:
                        vals['retour_line_ids'] = lines_data

        return super().write(vals)

    def _prepare_lines_from_vente(self, vente):
        """Prépare les données des lignes à partir d'une vente"""
        lines = []

        if not vente or not vente.consigne_appliquee:
            return lines

        # Créer les lignes à partir des emballages de la vente
        for emb in vente.detail_emballage_vente_ids:
            if emb.qte_sortantes > 0 and not emb.emballage_id.non_returnable:
                line_vals = {
                    'emballage_id': emb.emballage_id.id,
                    'qte_consignee': emb.qte_sortantes,
                    'qte_retournee': emb.qte_sortantes,
                    'prix_unitaire': emb.emballage_id.price_unit,
                }
                lines.append((0, 0, line_vals))

        return lines

    @api.depends('vente_id', 'vente_id.client_id')
    def _compute_client_id(self):
        for record in self:
            if record.vente_id and record.vente_id.client_id:
                record.client_id = record.vente_id.client_id

    @api.depends('retour_line_ids.montant_total')
    def _compute_montants(self):
        for record in self:
            record.montant_total_consigne = sum(record.retour_line_ids.mapped('montant_total'))
            record.montant_a_rembourser = record.montant_total_consigne

    @api.onchange('vente_id')
    def _onchange_vente_id(self):
        """Charge automatiquement les emballages de la vente pour l'affichage"""
        # Nettoyer les lignes existantes
        self.retour_line_ids = [(5, 0, 0)]

        if not self.vente_id:
            return

        # Mettre à jour le client
        self.client_id = self.vente_id.client_id

        # Vérifier si la vente a des consignes appliquées
        if not self.vente_id.consigne_appliquee:
            return {
                'warning': {
                    'title': _('Attention'),
                    'message': _('Cette vente n\'a pas de consigne appliquée.')
                }
            }

        # Créer les lignes temporaires pour l'affichage
        lines = self._prepare_lines_from_vente(self.vente_id)
        if lines:
            self.retour_line_ids = lines
        else:
            return {
                'warning': {
                    'title': _('Information'),
                    'message': _('Aucun emballage consigné trouvé pour cette vente.')
                }
            }

    @api.constrains('client_id', 'state')
    def _check_client_required(self):
        """Vérifie que le client est renseigné lors de la validation"""
        for record in self:
            if record.state in ['valide', 'avoir_cree'] and not record.client_id:
                raise ValidationError(_("Le client est obligatoire pour valider le retour de consigne."))

    @api.constrains('retour_line_ids')
    def _check_lines_required(self):
        """Vérifie qu'il y a au moins une ligne avec emballage"""
        for record in self:
            for line in record.retour_line_ids:
                if not line.emballage_id:
                    raise ValidationError(_("Toutes les lignes doivent avoir un emballage défini."))

    def action_validate(self):
        """Valide le retour de consigne"""
        self.ensure_one()

        if self.state != 'brouillon':
            raise UserError(_("Seul un retour en brouillon peut être validé."))

        if not self.retour_line_ids:
            raise UserError(_("Aucun emballage à retourner."))

        # Vérifier qu'au moins un emballage est retourné
        if sum(self.retour_line_ids.mapped('qte_retournee')) == 0:
            raise UserError(_("Aucune quantité retournée."))

        # Vérifier le client
        if not self.client_id:
            raise UserError(_("Veuillez sélectionner un client avant de valider."))

        self.state = 'valide'

        # Message de confirmation
        self.message_post(
            body=_("Retour de consigne validé. Montant à rembourser : %s") % self.montant_a_rembourser
        )

    def action_create_avoir(self):
        """Crée l'avoir client pour le remboursement"""
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("Le retour doit être validé avant de créer l'avoir."))

        if self.avoir_client_id:
            raise UserError(_("Un avoir a déjà été créé pour ce retour."))

        if not self.vente_id:
            raise UserError(_("La création d'avoir sans vente n'est pas encore implémentée."))

        # Créer l'avoir client
        avoir = self.env['gecafle.avoir.client'].create({
            'vente_id': self.vente_id.id,
            'date': self.date,
            'type_avoir': 'consigne',  # Type consigne
            'description': _("Remboursement consigne - Retour N° %s\nEmballages retournés : %s") % (
                self.name,
                ', '.join(['%s x %s' % (l.qte_retournee, l.emballage_id.name) for l in self.retour_line_ids if
                           l.qte_retournee > 0])
            ),
            'montant_avoir': self.montant_a_rembourser,
            'generer_avoirs_producteurs': False,
        })

        self.avoir_client_id = avoir.id
        self.state = 'avoir_cree'

        # Mettre à jour l'état de consigne de la vente
        if self.vente_id:
            self.vente_id.with_context(allow_adjustment=True).write({
                'etat_consigne': 'rendu'
            })

        # Message de confirmation
        self.message_post(
            body=_("Avoir client créé : %s") % avoir.name,
            partner_ids=self.client_id.ids
        )

        # Ouvrir l'avoir créé
        return {
            'name': _('Avoir Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client',
            'res_id': avoir.id,
            'target': 'current',
        }

    def action_draft(self):
        """Remet le retour en brouillon"""
        for record in self:
            if record.state != 'annule':
                raise UserError(_("Seul un retour annulé peut être remis en brouillon."))

            record.state = 'brouillon'

    def action_view_avoir(self):
        """Affiche l'avoir lié"""
        self.ensure_one()

        if not self.avoir_client_id:
            raise UserError(_("Aucun avoir n'est lié à ce retour."))

        return {
            'name': _('Avoir Client'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client',
            'res_id': self.avoir_client_id.id,
            'target': 'current',
        }

    def action_view_credit_note(self):
        """Affiche la note de crédit liée (depuis l'avoir client)"""
        self.ensure_one()

        if not self.credit_note_id:
            raise UserError(_("Aucune note de crédit n'est liée à ce retour."))

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
            raise UserError(_("Aucune note de crédit n'est liée à ce retour."))

        if self.credit_note_id.state != 'posted':
            raise UserError(_("La note de crédit doit être validée avant d'enregistrer un paiement."))

        return self.credit_note_id.action_register_payment()
