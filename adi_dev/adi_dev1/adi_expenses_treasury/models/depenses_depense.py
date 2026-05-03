# -*- coding: utf-8 -*-
"""
Extension du modèle `depenses.depense` pour intégration `adi_treasury`.

Ce module n'introduit AUCUN nouveau modèle : il étend en place
`depenses.depense` (défini dans `adi_expenses`) en lui ajoutant :
  * les mixins `mail.thread` et `mail.activity.mixin` (chatter + tracking)
  * les champs trésorerie (caisse, partenaire, motif, état, opération liée)
  * un workflow draft → posted → cancel → draft

Workflow :
    draft  --action_post--> posted  --action_cancel--> cancel  --action_draft--> draft

Au post, une `treasury.cash.operation` (type 'out', motif "Frais ADI") est
créée via la factory `create_manual_operation_with_closing` qui garantit
l'existence d'une clôture courante. L'opération est ensuite passée en
'posted' afin d'être prise en compte dans le solde et les totaux de clôture.

Annulation : refusée si la clôture liée est validée (intégrité comptable).
Suppression : refusée pour tout frais déjà comptabilisé.
"""
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class DepensesDepense(models.Model):
    _name = 'depenses.depense'
    _inherit = ['depenses.depense', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Référence séquentielle (FRAIS/AAAA/00001)
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        copy=False,
        default='/',
        help="Numéro auto-attribué à la création (séquence 'depenses.depense').",
    )

    # ------------------------------------------------------------------
    # Tracking sur les champs déjà existants (utile pour l'audit)
    # ------------------------------------------------------------------
    montant = fields.Float(tracking=True)
    categorie = fields.Many2one(tracking=True)

    # ------------------------------------------------------------------
    # Intégration trésorerie
    # ------------------------------------------------------------------
    caisse_id = fields.Many2one(
        'treasury.cash',
        string='Caisse',
        required=True,
        domain="[('state', '=', 'open')]",
        tracking=True,
        help="Caisse sur laquelle le frais sera décaissé.",
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        tracking=True,
        help="Bénéficiaire du paiement (optionnel).",
    )
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('posted', 'Comptabilisé'),
            ('cancel', 'Annulé'),
        ],
        string='État',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    motif_id = fields.Many2one(
        'treasury.operation.category',
        string='Motif',
        domain="[('operation_type', 'in', ['out', 'both'])]",
        default=lambda self: self.env.ref(
            'adi_expenses_treasury.category_frais_adi', raise_if_not_found=False),
        help="Motif de l'opération de trésorerie qui sera créée au post.",
    )
    treasury_operation_id = fields.Many2one(
        'treasury.cash.operation',
        string='Opération de trésorerie',
        readonly=True,
        copy=False,
    )
    treasury_closing_id = fields.Many2one(
        'treasury.cash.closing',
        related='treasury_operation_id.closing_id',
        string='Clôture',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Attribuer une référence séquentielle à la création.

        sudo() est utilisé pour next_by_code car le groupe de base n'a pas
        toujours les droits sur ir.sequence (même pattern que
        adi_treasury_sequence_fix).
        """
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'depenses.depense') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_post(self):
        """Comptabiliser le frais : créer et poster l'opération de trésorerie."""
        Operation = self.env['treasury.cash.operation']
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_(
                    "Seuls les frais en brouillon peuvent être comptabilisés."))

            # _check_closing_required lève une UserError si aucune clôture
            # draft|confirmed n'existe pour la caisse.
            expense.caisse_id._check_closing_required()

            motif = expense.motif_id
            if not motif:
                motif = self.env.ref('adi_expenses_treasury.category_frais_adi')

            description = _("Frais : %s — %s") % (
                expense.categorie.name,
                expense.description or '',
            )

            vals = {
                'cash_id': expense.caisse_id.id,
                'operation_type': 'out',
                'category_id': motif.id,
                'amount': expense.montant,
                'date': fields.Datetime.now(),
                'description': description,
                'reference': "FRAIS-%s" % expense.id,
                'partner_id': expense.partner_id.id or False,
                'is_manual': True,
            }
            operation = Operation.create_manual_operation_with_closing(vals)

            if operation.state == 'draft':
                operation.action_post()

            expense.write({
                'state': 'posted',
                'treasury_operation_id': operation.id,
            })
            expense.message_post(body=_(
                "Opération trésorerie créée : %s") % operation.name)

    def action_cancel(self):
        """Annuler un frais comptabilisé.

        Note : `treasury.cash.operation.action_cancel()` refuse toute
        opération attachée à un closing. Comme nos opérations sont créées
        via `create_manual_operation_with_closing`, elles ont toujours un
        closing_id. On bypass donc l'action standard et on écrit le state
        directement, après vérification que la clôture n'est pas validée.
        """
        for expense in self:
            if expense.state != 'posted':
                raise UserError(_(
                    "Seuls les frais comptabilisés peuvent être annulés."))

            operation = expense.treasury_operation_id
            if operation and operation.closing_id \
                    and operation.closing_id.state == 'validated':
                raise UserError(_(
                    "Impossible d'annuler : la clôture est validée."))

            if operation and operation.state == 'posted':
                operation.write({'state': 'cancel'})
                operation.message_post(body=_(
                    "Opération annulée suite à l'annulation du frais %s.") % expense.id)

            expense.state = 'cancel'

    def action_draft(self):
        """Remettre un frais annulé en brouillon."""
        for expense in self:
            if expense.state != 'cancel':
                raise UserError(_(
                    "Seuls les frais annulés peuvent être remis en brouillon."))
            expense.write({
                'state': 'draft',
                'treasury_operation_id': False,
            })

    def unlink(self):
        for expense in self:
            if expense.state == 'posted':
                raise UserError(_(
                    "Impossible de supprimer un frais comptabilisé. Annulez d'abord."))
        return super().unlink()
