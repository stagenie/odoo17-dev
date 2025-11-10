from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleReception(models.Model):
    _inherit = 'gecafle.reception'


    # Ajout du controle pour les réceptions qui ont une récap
    # Champ existant
    # Champ calculé pour indiquer si des ventes sont liées à cette réception
    has_linked_sales = fields.Boolean(
        string="A des ventes liées",
        compute="_compute_has_linked_sales",
        store=True,
        help="Indique si cette réception est liée à des ventes actives"
    )

    # Champ pour afficher les ventes liées
    linked_sale_ids = fields.Many2many(
        'gecafle.vente',
        string="Ventes liées",
        compute="_compute_linked_sales",
        help="Ventes liées à cette réception"
    )

    # Compteur pour le Smart Button
    linked_sale_count = fields.Integer(
        string="Nombre de ventes",
        compute="_compute_linked_sale_count",
        help="Nombre de ventes liées à cette réception"
    )

    # AJOUT DES NOUVEAUX CHAMPS POUR L'ÉTAT DE PAIEMENT
    payment_state = fields.Selection([
        ('not_invoiced', 'Non facturé'),
        ('unpaid', 'Non payé'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé')
    ], string="État de paiement", compute='_compute_payment_state', store=True)

    payment_amount_total = fields.Monetary(
        string="Montant total",
        compute='_compute_payment_info',
        currency_field='currency_id'
        # store=True
    )
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

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('details_reception_ids.detail_vente_ids.vente_id.state')
    def _compute_has_linked_sales(self):
        """Vérifie si la réception a des ventes liées non annulées"""
        for record in self:
            sales_count = self.env['gecafle.details_ventes'].search_count([
                ('reception_id', '=', record.id),
                ('vente_id.state', '!=', 'annule')
            ])
            record.has_linked_sales = sales_count > 0

    @api.depends('details_reception_ids.detail_vente_ids.vente_id')
    def _compute_linked_sales(self):
        """Récupère la liste des ventes liées à cette réception"""
        for record in self:
            sales = self.env['gecafle.details_ventes'].search([
                ('reception_id', '=', record.id),
                ('vente_id.state', '!=', 'annule')
            ]).mapped('vente_id')
            record.linked_sale_ids = [(6, 0, sales.ids)]

    @api.depends('details_reception_ids.detail_vente_ids.vente_id.state')
    def _compute_linked_sale_count(self):
        """Calcule le nombre de ventes liées pour le Smart Button"""
        for record in self:
            vente_ids = record.details_reception_ids.mapped('detail_vente_ids').filtered(
                lambda v: v.vente_id.state != 'annule'
            ).mapped('vente_id.id')
            record.linked_sale_count = len(set(vente_ids))

    # AJOUT DES MÉTHODES DE CALCUL POUR L'ÉTAT DE PAIEMENT
    @api.depends('recap_ids.state', 'recap_ids.invoice_id.payment_state',
                 'recap_ids.bon_achat_id.state', 'recap_ids.net_a_payer')
    def _compute_payment_state(self):
        """Calcule l'état de paiement basé sur le récapitulatif et ses documents"""
        for record in self:
            if not record.recap_ids:
                record.payment_state = 'not_invoiced'
            else:
                # Prendre le dernier récapitulatif validé
                valid_recaps = record.recap_ids.filtered(lambda r: r.state in ['valide', 'facture'])
                if not valid_recaps:
                    record.payment_state = 'not_invoiced'
                else:
                    recap = valid_recaps[-1]  # Dernier récap

                    # Vérifier l'état de la facture fournisseur
                    if recap.invoice_id:
                        if recap.invoice_id.payment_state == 'paid':
                            record.payment_state = 'paid'
                        elif recap.invoice_id.payment_state == 'partial':
                            record.payment_state = 'partial'
                        else:
                            record.payment_state = 'unpaid'
                    # Sinon vérifier l'état du bon d'achat
                    elif recap.bon_achat_id:
                        if recap.bon_achat_id.state == 'paye':
                            record.payment_state = 'paid'
                        elif recap.bon_achat_id.state in ['valide', 'facture']:
                            record.payment_state = 'unpaid'
                        else:
                            record.payment_state = 'not_invoiced'
                    else:
                        record.payment_state = 'unpaid'

    @api.depends('recap_ids.net_a_payer', 'recap_ids.invoice_id', 'recap_ids.bon_achat_id')
    def _compute_payment_info(self):
        """Calcule les montants de paiement"""
        for record in self:
            valid_recaps = record.recap_ids.filtered(lambda r: r.state in ['valide', 'facture'])

            if not valid_recaps:
                record.payment_amount_due = 0
                record.payment_amount_paid = 0
                record.payment_percentage = 0
                record.payment_amount_total = 0
            else:
                recap = valid_recaps[-1]
                total_amount = recap.net_a_payer

                # Calculer le montant payé
                amount_paid = 0
                if recap.invoice_id:
                    amount_paid = total_amount - recap.invoice_id.amount_residual
                elif recap.bon_achat_id and recap.bon_achat_id.state == 'paye':
                    amount_paid = total_amount

                record.payment_amount_due = total_amount - amount_paid
                record.payment_amount_paid = amount_paid
                record.payment_percentage = (amount_paid / total_amount * 100) if total_amount else 0
                record.payment_amount_total = record.payment_amount_due + record.payment_amount_paid

    def action_view_linked_sales(self):
        """Action du Smart Button pour afficher les ventes liées"""
        self.ensure_one()

        # Récupérer les IDs des ventes liées
        vente_ids = self.details_reception_ids.mapped('detail_vente_ids').filtered(
            lambda v: v.vente_id.state != 'annule'
        ).mapped('vente_id.id')

        # Retourner l'action pour afficher ces ventes
        action = {
            'name': _('Ventes liées'),
            'view_mode': 'list,form',
            'res_model': 'gecafle.vente',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', list(set(vente_ids)))],
            'context': {'create': False}
        }

        # Si une seule vente, ouvrir directement le formulaire
        if len(vente_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': vente_ids[0],
            })

        return action

    def unlink(self):
        """Empêche la suppression des réceptions liées à des ventes"""
        for record in self:
            if record.has_linked_sales:
                raise UserError(_(
                    "Impossible de supprimer la réception %s car elle est liée à une ou plusieurs ventes.\n"
                    "Veuillez d'abord annuler ou supprimer ces ventes."
                ) % (record.name))

        return super(GecafleReception, self).unlink()

    def action_cancel(self):
        """Annule la réception si aucune vente n'y est liée"""
        for record in self:
            """ Vérifie si la réception a des avances à payer avant de la supprimer"""
            payments = self.env['account.payment'].search([
                ('reception_id', '=', record.id),
                ('state', '!=', 'cancel')
            ])
            if payments:
                raise UserError(_(
                    "Impossible d'annuler la réception %s car elle a des paiements d'avance.\n"
                    "Paiements concernés: %s\n"
                    "Vous devez d'abord annuler ces paiements."
                ) % (record.name, ', '.join(payments.mapped('name'))))

            if record.has_linked_sales:
                raise UserError(_(
                    "Impossible d'annuler la réception %s car elle est liée à une ou plusieurs ventes.\n"
                    "Veuillez d'abord annuler ou supprimer ces ventes."
                ) % (record.name))

        return super(GecafleReception, self).action_cancel()

    def action_draft(self):
        """Remet la réception en brouillon si aucune vente n'y est liée"""
        for record in self:
            if record.has_linked_sales:
                raise UserError(_(
                    "Impossible de remettre en brouillon la réception %s car elle est liée à une ou plusieurs ventes.\n"
                    "Veuillez d'abord annuler ou supprimer ces ventes."
                ) % (record.name))

        return super(GecafleReception, self).action_draft()


    # NOUVEAU : Champ calculé pour indiquer si la réception a du stock disponible
    has_available_stock = fields.Boolean(
        string="A du stock disponible",
        compute="_compute_has_available_stock",
        store=True,
        help="Indique si cette réception a au moins une ligne avec du stock disponible"
    )

    @api.depends('details_reception_ids.qte_colis_disponibles')
    def _compute_has_available_stock(self):
        """Calcule si la réception a du stock disponible"""
        for record in self:
            record.has_available_stock = any(
                line.qte_colis_disponibles > 0
                for line in record.details_reception_ids
            )


    @api.depends('details_reception_ids.qte_colis_disponibles')
    def _compute_has_available_stock(self):
        """Calcule si la réception a du stock disponible"""
        for record in self:
            record.has_available_stock = any(
                line.qte_colis_disponibles > 0
                for line in record.details_reception_ids
            )

    recap_count = fields.Integer(
        string="Récapitulatifs",
        compute="_compute_recap_count",
    )

    def _compute_recap_count(self):
        for record in self:
            record.recap_count = self.env['gecafle.reception.recap'].search_count([
                ('reception_id', '=', record.id)
            ])

    search_field = fields.Char(
        string="Champ de recherche",
        compute='_compute_search_field',
        search='_search_search_field',
        store=False
    )

    @api.depends('name', 'producteur_id.name', 'reception_date')
    def _compute_search_field(self):
        for record in self:
            date_str = ""
            if hasattr(record, 'reception_date') and record.reception_date:
                date_str = record.reception_date.strftime('%d/%m/%Y')

            producteur = record.producteur_id.name if record.producteur_id else ''
            record.search_field = f"{record.name} {producteur} {date_str}"

    def _search_search_field(self, operator, value):
        """Permet la recherche sur plusieurs champs"""
        return ['|', '|',
                ('name', operator, value),
                ('producteur_id.name', operator, value),
                ('reception_date', operator, value)
                ]






class GecafleDetailsReceptionExtended(models.Model):
    _inherit = 'gecafle.details_reception'


    # Champ pour indiquer si cette ligne est utilisée dans des ventes
    has_linked_sales = fields.Boolean(
        string="Utilisée dans des ventes",
        compute="_compute_has_linked_sales",
        store=True,
        help="Indique si cette ligne est utilisée dans des ventes"
    )

    # Compteur de ventes liées à cette ligne
    linked_sale_count = fields.Integer(
        string="Nombre de ventes",
        compute="_compute_linked_sale_count",
        help="Nombre de ventes utilisant cette ligne"
    )

    # Liste des ventes liées pour affichage
    linked_sale_names = fields.Char(
        string="Ventes liées",
        compute="_compute_linked_sale_names",
        help="Liste des ventes utilisant cette ligne"
    )

    @api.depends('detail_vente_ids.vente_id.state')
    def _compute_has_linked_sales(self):
        for record in self:
            record.has_linked_sales = bool(
                record.detail_vente_ids.filtered(lambda v: v.vente_id.state != 'annule')
            )

    @api.depends('detail_vente_ids.vente_id.state')
    def _compute_linked_sale_count(self):
        for record in self:
            record.linked_sale_count = len(
                record.detail_vente_ids.filtered(lambda v: v.vente_id.state != 'annule').mapped('vente_id')
            )

    @api.depends('detail_vente_ids.vente_id')
    def _compute_linked_sale_names(self):
        for record in self:
            sales = record.detail_vente_ids.filtered(lambda v: v.vente_id.state != 'annule').mapped('vente_id.name')
            if sales:
                if len(sales) <= 3:
                    record.linked_sale_names = ', '.join(sales)
                else:
                    record.linked_sale_names = f"{', '.join(sales[:3])} et {len(sales) - 3} autres"
            else:
                record.linked_sale_names = False

    # Empêcher la suppression de lignes vendues
    def unlink(self):
        for record in self:
            # Vérifier les paiements
            if self.env['account.payment'].search_count([('reception_id', '=', record.id)]):
                raise UserError(_(
                    "Impossible de supprimer la réception %s car elle a des paiements associés."
                ) % record.name)

            if record.has_linked_sales:
                raise UserError(_(
                    "Impossible de supprimer la ligne de réception pour '%s' car elle est utilisée dans les ventes: %s.\n"
                    "Veuillez d'abord annuler ces ventes."
                ) % (record.designation_id.name, record.linked_sale_names))
        return super().unlink()

    # Protection contre les modifications critiques
    def write(self, vals):
        # Liste des champs critiques qui ne peuvent pas être modifiés
        critical_fields = ['designation_id', 'qualite_id', 'type_colis_id']

        if any(field in vals for field in critical_fields):
            for record in self:
                if record.has_linked_sales:
                    raise UserError(_(
                        "Impossible de modifier le produit/qualité/emballage pour '%s' car cette ligne est utilisée dans les ventes: %s.\n"
                        "Seule la quantité peut être ajustée."
                    ) % (record.designation_id.name, record.linked_sale_names))

        # On peut modifier la quantité reçue, mais pas la diminuer en dessous des ventes
        if 'qte_colis_recue' in vals:
            for record in self:
                if record.has_linked_sales and vals['qte_colis_recue'] < record.qte_colis_vendus:
                    raise UserError(_(
                        "Impossible de réduire la quantité reçue à %d pour '%s' car %d unités sont déjà vendues dans les ventes: %s"
                    ) % (vals['qte_colis_recue'], record.designation_id.name, record.qte_colis_vendus,
                         record.linked_sale_names))

        return super().write(vals)

