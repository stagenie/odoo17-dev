from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    recap_id = fields.Many2one(
        'gecafle.reception.recap',
        string="Récapitulatif Source",
        readonly=True,
        ondelete='restrict'
    )

    recap_count = fields.Integer(
        string="Récapitulatifs",
        compute='_compute_recap_count'
    )

    @api.depends('recap_id')
    def _compute_recap_count(self):
        for record in self:
            record.recap_count = 1 if record.recap_id else 0

    def action_view_recap_source(self):
        """Ouvre le récapitulatif source de cette facture"""
        self.ensure_one()

        if not self.recap_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _("Cette facture n'est pas liée à un récapitulatif."),
                    'type': 'info',
                }
            }

        return {
            'name': _('Récapitulatif Source'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.reception.recap',
            'res_id': self.recap_id.id,
            'target': 'current',
        }

    def action_print_vendor_invoice(self):
        """Imprime directement la facture fournisseur"""
        self.ensure_one()

        # S'assurer que c'est bien une facture fournisseur
        if self.move_type != 'in_invoice':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _("Cette action n'est disponible que pour les factures fournisseur."),
                    'type': 'danger',
                }
            }

        # Retourner l'action d'impression standard d'Odoo
        return self.env.ref('account.account_invoices').report_action(self)


    """ Ajouter les avais producteur liés """
    avoir_producteur_id = fields.Many2one(
        'gecafle.avoir.producteur',
        string="Avoir producteur source",
        readonly=True,
        ondelete='restrict'
    )

    avoir_producteur_count = fields.Integer(
        string="Avoir producteur",
        compute='_compute_avoir_producteur_count'
    )

    @api.depends('avoir_producteur_id')
    def _compute_avoir_producteur_count(self):
        for record in self:
            record.avoir_producteur_count = 1 if record.avoir_producteur_id else 0

    def action_print_avoir_producteur(self):
        """Imprime l'avoir producteur lié"""
        self.ensure_one()
        if not self.avoir_producteur_id:
            return False

        return self.avoir_producteur_id.action_print_avoir()