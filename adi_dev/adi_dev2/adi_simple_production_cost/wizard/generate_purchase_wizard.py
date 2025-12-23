# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GeneratePurchaseWizard(models.TransientModel):
    """
    Wizard pour générer manuellement les achats de produits finis.
    """
    _name = 'ron.generate.purchase.wizard'
    _description = 'Générer Achat Produits Finis'

    daily_production_id = fields.Many2one(
        'ron.daily.production',
        string='Production Journalière',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )

    production_date = fields.Date(
        string='Date',
        related='daily_production_id.production_date'
    )

    # Informations sur les produits finis
    qty_solo = fields.Float(
        string='Quantité SOLO (Cartons)',
        related='daily_production_id.qty_solo_cartons'
    )

    cost_solo = fields.Monetary(
        string='Coût SOLO/Carton',
        related='daily_production_id.cost_solo_per_carton',
        currency_field='currency_id'
    )

    qty_classico = fields.Float(
        string='Quantité CLASSICO (Cartons)',
        related='daily_production_id.qty_classico_cartons'
    )

    cost_classico = fields.Monetary(
        string='Coût CLASSICO/Carton',
        related='daily_production_id.cost_classico_per_carton',
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='daily_production_id.currency_id'
    )

    # Options
    create_finished_purchase = fields.Boolean(
        string='Créer Achat Produits Finis',
        default=True
    )

    create_scrap_purchase = fields.Boolean(
        string='Créer Achat Rebuts Vendables',
        default=True
    )

    auto_confirm_purchase = fields.Boolean(
        string='Confirmer les Achats Automatiquement',
        default=False
    )

    auto_receive = fields.Boolean(
        string='Réceptionner Automatiquement',
        default=False,
        help="Valider les bons de réception automatiquement"
    )

    def action_generate(self):
        """Génère les achats selon les options."""
        self.ensure_one()
        production = self.daily_production_id

        if production.state not in ('calculated', 'validated'):
            raise UserError(_("La production doit être calculée avant de générer les achats."))

        purchases_created = []

        # Générer l'achat de produits finis
        if self.create_finished_purchase and not production.purchase_finished_id:
            production._create_finished_purchase()
            if production.purchase_finished_id:
                purchases_created.append(production.purchase_finished_id)

                if self.auto_confirm_purchase:
                    production.purchase_finished_id.button_confirm()

                    if self.auto_receive:
                        self._auto_receive_purchase(production.purchase_finished_id)

        # Générer l'achat de rebuts vendables
        if (self.create_scrap_purchase and
            production.scrap_sellable_weight > 0 and
            not production.purchase_scrap_id):

            production._create_scrap_purchase()
            if production.purchase_scrap_id:
                purchases_created.append(production.purchase_scrap_id)

                if self.auto_confirm_purchase:
                    production.purchase_scrap_id.button_confirm()

                    if self.auto_receive:
                        self._auto_receive_purchase(production.purchase_scrap_id)

        if not purchases_created:
            raise UserError(_("Aucun achat n'a été créé. Les achats existent peut-être déjà."))

        # Retourner l'action pour voir les achats créés
        if len(purchases_created) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Achat Créé',
                'res_model': 'purchase.order',
                'res_id': purchases_created[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Achats Créés',
                'res_model': 'purchase.order',
                'domain': [('id', 'in', [p.id for p in purchases_created])],
                'view_mode': 'tree,form',
                'target': 'current',
            }

    def _auto_receive_purchase(self, purchase):
        """Réceptionne automatiquement un achat."""
        for picking in purchase.picking_ids:
            if picking.state not in ('done', 'cancel'):
                # Préparer les quantités
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty

                # Valider
                picking.button_validate()
