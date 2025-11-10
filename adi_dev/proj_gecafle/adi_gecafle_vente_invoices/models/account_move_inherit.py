from odoo import models, fields, api, _
from  odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Lien vers le bon de vente source
    gecafle_vente_id = fields.Many2one(
        'gecafle.vente',
        string="Bon de vente source",
        readonly=True,
        ondelete='restrict'
    )

    # Informations du client GECAFLE
    gecafle_client_id = fields.Many2one(
        'gecafle.client',
        string="Client GECAFLE",
        related='gecafle_vente_id.client_id',
        store=True
    )

    # Champs de totaux - Exactement les mêmes noms que dans gecafle.vente
    total_poids_brut = fields.Float(
        string="Total Poids Brut",
        digits=(16, 2),
        compute='_compute_gecafle_totals',
        store=True
    )

    total_poids_colis = fields.Float(
        string="Total Poids Colis",
        digits=(16, 2),
        compute='_compute_gecafle_totals',
        store=True
    )

    total_poids_net = fields.Float(
        string="Total Poids Net",
        digits=(16, 2),
        compute='_compute_gecafle_totals',
        store=True
    )

    montant_total_commission = fields.Monetary(
        string="Montant Total Commission",
        compute='_compute_gecafle_totals',
        store=True,
        currency_field='currency_id',
        groups="adi_gecafle_ventes.group_gecafle_direction"
    )

    montant_total_emballages = fields.Monetary(
        string="Montant Colis",
        compute='_compute_gecafle_totals',
        store=True,
        currency_field='currency_id'
    )

    montant_total_consigne = fields.Monetary(
        string="Montant Consigne",
        compute='_compute_gecafle_totals',
        store=True,
        currency_field='currency_id'
    )

    montant_remise_globale = fields.Monetary(
        string="Montant Remise",
        compute='_compute_gecafle_totals',
        store=True,
        currency_field='currency_id'
    )

    montant_total_net = fields.Monetary(
        string="Montant Net",
        compute='_compute_gecafle_totals',
        store=True,
        currency_field='currency_id'
    )

    consigne_appliquee = fields.Boolean(
        string="Consigne Appliquée",
        compute='_compute_consigne_appliquee',
        store=True
    )

    @api.depends('gecafle_client_id.est_fidel')
    def _compute_consigne_appliquee(self):
        for move in self:
            if move.gecafle_client_id:
                move.consigne_appliquee = not move.gecafle_client_id.est_fidel
            else:
                move.consigne_appliquee = False

    @api.depends('gecafle_vente_id')
    def _compute_gecafle_totals(self):
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund'] and move.gecafle_vente_id:
                # Copier tous les totaux depuis le bon de vente
                vente = move.gecafle_vente_id
                move.total_poids_brut = vente.total_poids_brut
                move.total_poids_colis = vente.total_poids_colis
                move.total_poids_net = vente.total_poids_net
                move.montant_total_commission = vente.montant_total_commission
                move.montant_total_emballages = vente.montant_total_emballages
                move.montant_total_consigne = vente.montant_total_consigne
                move.montant_remise_globale = vente.montant_remise_globale
                move.montant_total_net = vente.montant_total_net
            else:
                move.total_poids_brut = 0
                move.total_poids_colis = 0
                move.total_poids_net = 0
                move.montant_total_commission = 0
                move.montant_total_emballages = 0
                move.montant_total_consigne = 0
                move.montant_remise_globale = 0
                move.montant_total_net = 0

    def action_view_gecafle_vente(self):
        """Ouvre le bon de vente source"""
        self.ensure_one()
        if not self.gecafle_vente_id:
            return False

        return {
            'name': _('Bon de vente source'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.vente',
            'res_id': self.gecafle_vente_id.id,
            'target': 'current',
        }

    def action_print_bon_vente(self):
        """Imprime le bon de vente depuis la facture"""
        self.ensure_one()
        if not self.gecafle_vente_id:
            raise UserError(_("Cette facture n'est pas liée à un bon de vente."))
        self.gecafle_vente_id.est_imprimee = True

        return self.env.ref('adi_gecafle_ventes.action_report_gecafle_bon_vente').report_action(self.gecafle_vente_id)

    def action_print_bon_vente_duplicata(self):
        """Imprime le duplicata du bon de vente depuis la facture"""
        self.ensure_one()
        if not self.gecafle_vente_id:
            raise UserError(_("Cette facture n'est pas liée à un bon de vente."))

        # Vérifier que le bon de vente a déjà été imprimé
        if not self.gecafle_vente_id.est_imprimee:
            raise UserError(
                _("Le bon de vente original n'a pas encore été imprimé. Veuillez d'abord imprimer l'original."))

        # Utiliser l'action de duplicata
        return self.env.ref('adi_gecafle_ventes.action_report_gecafle_bon_vente_duplicata').with_context(
            is_duplicata=True
        ).report_action(self.gecafle_vente_id)
