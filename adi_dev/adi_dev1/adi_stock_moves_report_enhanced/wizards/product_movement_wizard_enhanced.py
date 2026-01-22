# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductMovementWizardEnhanced(models.TransientModel):
    """Extension du wizard de mouvements produits avec filtres entrepôts/emplacements."""
    _inherit = 'product.movement.wizard'

    # ========== Filtres Entrepôts ==========
    show_all_warehouses = fields.Boolean(
        string='Tous les entrepôts',
        default=True,
        help='Cocher pour inclure tous les entrepôts dans le rapport',
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'wizard_movement_warehouse_rel',
        'wizard_id',
        'warehouse_id',
        string='Entrepôts',
    )

    # ========== Filtres Emplacements ==========
    show_all_locations = fields.Boolean(
        string='Tous les emplacements',
        default=True,
        help='Cocher pour inclure tous les emplacements des entrepôts sélectionnés',
    )
    location_ids = fields.Many2many(
        'stock.location',
        'wizard_movement_location_rel',
        'wizard_id',
        'location_id',
        string='Emplacements',
        domain="[('id', 'in', available_location_ids)]",
    )
    available_location_ids = fields.Many2many(
        'stock.location',
        'wizard_movement_available_location_rel',
        'wizard_id',
        'location_id',
        string='Emplacements Disponibles',
        compute='_compute_available_locations',
        store=False,
    )

    # ========== Computed ==========
    @api.depends('show_all_warehouses', 'warehouse_ids')
    def _compute_available_locations(self):
        """Calculer les emplacements disponibles selon les entrepôts sélectionnés."""
        for wizard in self:
            if wizard.show_all_warehouses:
                # Tous les emplacements internes
                locations = self.env['stock.location'].search([
                    ('usage', '=', 'internal'),
                ])
            else:
                if wizard.warehouse_ids:
                    # Emplacements liés aux entrepôts sélectionnés
                    location_ids = []
                    for warehouse in wizard.warehouse_ids:
                        if warehouse.view_location_id:
                            child_locations = self.env['stock.location'].search([
                                ('id', 'child_of', warehouse.view_location_id.id),
                                ('usage', '=', 'internal'),
                            ])
                            location_ids.extend(child_locations.ids)
                        elif warehouse.lot_stock_id:
                            child_locations = self.env['stock.location'].search([
                                ('id', 'child_of', warehouse.lot_stock_id.id),
                                ('usage', '=', 'internal'),
                            ])
                            location_ids.extend(child_locations.ids)
                    locations = self.env['stock.location'].browse(list(set(location_ids)))
                else:
                    locations = self.env['stock.location']
            wizard.available_location_ids = locations

    # ========== Onchange ==========
    @api.onchange('show_all_warehouses')
    def _onchange_show_all_warehouses(self):
        if self.show_all_warehouses:
            self.warehouse_ids = False
        # Réinitialiser les emplacements
        self.location_ids = False
        self.show_all_locations = True

    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        """Réinitialiser les emplacements quand les entrepôts changent."""
        self.location_ids = False
        self._compute_available_locations()

    @api.onchange('show_all_locations')
    def _onchange_show_all_locations(self):
        if self.show_all_locations:
            self.location_ids = False

    # ========== Override Action ==========
    def action_generate_report(self):
        """Générer le rapport avec les filtres entrepôts/emplacements."""
        self.ensure_one()

        # Déterminer les produits (logique originale)
        domain = []
        if not self.show_all:
            if self.category_ids:
                domain.append(('categ_id', 'in', self.category_ids.ids))
            if self.product_ids:
                domain.append(('id', 'in', self.product_ids.ids))

        products = self.env['product.product'].search(domain)

        # Déterminer les emplacements
        if self.show_all_warehouses and self.show_all_locations:
            # Tous les emplacements internes
            locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        elif self.show_all_locations:
            # Tous les emplacements des entrepôts sélectionnés
            locations = self.available_location_ids
        else:
            # Emplacements spécifiquement sélectionnés
            locations = self.location_ids

        # Préparer les données pour le rapport
        data = {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'product_ids': products.ids,
            'location_ids': locations.ids,
            'warehouse_ids': self.warehouse_ids.ids if not self.show_all_warehouses else [],
            'show_all_warehouses': self.show_all_warehouses,
            'show_all_locations': self.show_all_locations,
        }

        return self.env.ref(
            'adi_stock_moves_report_enhanced.action_report_product_movements_enhanced'
        ).report_action(self, data=data)
