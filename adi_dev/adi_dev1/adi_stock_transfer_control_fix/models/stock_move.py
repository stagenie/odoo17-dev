# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_available_source = fields.Float(
        string='Qté Disponible (Source)',
        compute='_compute_qty_available_source',
        store=False,
        help="Quantité disponible du produit dans l'emplacement source"
    )
    is_qty_insufficient = fields.Boolean(
        string='Stock Insuffisant',
        compute='_compute_qty_available_source',
        store=False,
        help="Indique si la quantité demandée dépasse la quantité disponible"
    )

    @api.depends('product_id', 'location_id', 'product_uom_qty')
    def _compute_qty_available_source(self):
        for move in self:
            qty_available = 0.0
            is_insufficient = False
            if move.product_id and move.location_id:
                # Calculer la quantité disponible dans l'emplacement source
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', move.product_id.id),
                    ('location_id', '=', move.location_id.id),
                ])
                qty_available = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
                # Vérifier si le stock est insuffisant
                if move.product_uom_qty > qty_available:
                    is_insufficient = True
            move.qty_available_source = qty_available
            move.is_qty_insufficient = is_insufficient


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    qty_available_source = fields.Float(
        string='Qté Disponible (Source)',
        compute='_compute_qty_available_source',
        store=False,
        help="Quantité disponible du produit dans l'emplacement source"
    )
    is_qty_insufficient = fields.Boolean(
        string='Stock Insuffisant',
        compute='_compute_qty_available_source',
        store=False,
        help="Indique si la quantité demandée dépasse la quantité disponible"
    )

    @api.depends('product_id', 'location_id', 'quantity')
    def _compute_qty_available_source(self):
        for line in self:
            qty_available = 0.0
            is_insufficient = False
            if line.product_id and line.location_id:
                # Calculer la quantité disponible dans l'emplacement source
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_id.id),
                ])
                qty_available = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
                # Vérifier si le stock est insuffisant (quantity remplace qty_done en Odoo 17)
                if line.quantity > qty_available:
                    is_insufficient = True
            line.qty_available_source = qty_available
            line.is_qty_insufficient = is_insufficient


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Surcharge pour vérifier la disponibilité avant validation"""
        for picking in self:
            # Vérifier seulement pour les transferts sortants (pas les réceptions)
            if picking.picking_type_code in ('outgoing', 'internal'):
                # Filtrer uniquement les mouvements actifs (pas annulés, pas faits, avec quantité > 0)
                # En Odoo 17, move_lines est remplacé par move_ids
                active_moves = picking.move_ids.filtered(
                    lambda m: m.state not in ('cancel', 'done') and m.product_uom_qty > 0
                )
                for move in active_moves:
                    if move.product_id and move.location_id:
                        # Calculer la quantité disponible
                        quants = self.env['stock.quant'].search([
                            ('product_id', '=', move.product_id.id),
                            ('location_id', '=', move.location_id.id),
                        ])
                        qty_available = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))

                        # Ajouter la quantité réservée pour ce mouvement (elle sera libérée)
                        # En Odoo 17, reserved_availability peut être remplacé par quantity
                        qty_available += move.quantity

                        if move.product_uom_qty > qty_available:
                            raise UserError(_(
                                "Transfert impossible !\n\n"
                                "Le produit '%s' n'a pas assez de stock dans l'emplacement source '%s'.\n\n"
                                "- Quantité demandée: %s %s\n"
                                "- Quantité disponible: %s %s\n\n"
                                "Veuillez ajuster la quantité ou attendre un réapprovisionnement."
                            ) % (
                                move.product_id.display_name,
                                move.location_id.complete_name,
                                move.product_uom_qty,
                                move.product_uom.name,
                                qty_available,
                                move.product_uom.name,
                            ))
        return super().button_validate()
