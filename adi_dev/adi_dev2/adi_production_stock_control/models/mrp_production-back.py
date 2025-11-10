# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    allow_overconsumption = fields.Boolean(
        string='Autoriser surconsommation',
        help='Si coché, permet de consommer plus que la quantité programmée',
        default=False
    )

    require_full_availability = fields.Boolean(
        string='Exiger disponibilité complète',
        help='Si coché, tous les composants doivent être disponibles en quantité suffisante avant de pouvoir produire',
        default=True
    )

    def _get_available_quantity(self, product_id, location_id, lot_id=None):
        """Calcule la quantité disponible d'un produit dans une location"""
        return self.env['stock.quant']._get_available_quantity(
            product_id,
            location_id,
            lot_id=lot_id,
            strict=False
        )

    def _check_components_availability(self):
        """Vérifie si tous les composants sont disponibles"""
        self.ensure_one()
        errors = []

        for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            product = move.product_id
            location = self.location_src_id

            # Quantité disponible dans l'emplacement source
            qty_available = self._get_available_quantity(product, location)

            # Convertir en unité du mouvement
            if move.product_uom != product.uom_id:
                qty_available = product.uom_id._compute_quantity(
                    qty_available,
                    move.product_uom,
                    rounding_method='HALF-UP'
                )

            # Quantité requise
            qty_required = move.product_uom_qty

            # Vérifier disponibilité
            precision = move.product_uom.rounding
            if float_compare(qty_available, qty_required, precision_rounding=precision) < 0:
                errors.append({
                    'product': product.display_name,
                    'available': qty_available,
                    'required': qty_required,
                    'missing': qty_required - qty_available,
                    'uom': move.product_uom.name
                })

        return errors

    def action_confirm(self):
        """Vérifier le stock avant de confirmer"""
        for production in self:
            if production.state == 'draft' and production.require_full_availability:
                errors = production._check_components_availability()
                if errors:
                    msg_lines = ["❌ Stock insuffisant pour confirmer la production:"]
                    for err in errors:
                        msg_lines.append(
                            f"• {err['product']}: "
                            f"Requis {err['required']:.2f} {err['uom']}, "
                            f"Disponible {err['available']:.2f} {err['uom']} "
                            f"(Manque {err['missing']:.2f})"
                        )
                    raise UserError('\n'.join(msg_lines))

        return super().action_confirm()

    def _pre_button_mark_done(self):
        """Hook avant de marquer la production comme terminée"""
        # Vérifier la disponibilité complète avant de produire
        for production in self:
            if production.require_full_availability:
                # Bloquer si tous les composants ne sont pas disponibles
                errors = []

                for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    # Calculer ce qui doit être consommé
                    qty_to_consume = 0
                    for line in move.move_line_ids:
                        if hasattr(line, 'qty_done'):
                            qty_to_consume += line.qty_done or 0

                    if qty_to_consume <= 0:
                        qty_to_consume = move.product_uom_qty

                    # Vérifier disponibilité
                    available = production._get_available_quantity(
                        move.product_id,
                        move.location_id or production.location_src_id
                    )

                    if move.product_uom != move.product_id.uom_id:
                        available = move.product_id.uom_id._compute_quantity(
                            available,
                            move.product_uom,
                            rounding_method='HALF-UP'
                        )

                    if available < qty_to_consume:
                        errors.append({
                            'product': move.product_id.display_name,
                            'available': available,
                            'to_consume': qty_to_consume,
                            'missing': qty_to_consume - available,
                            'uom': move.product_uom.name
                        })

                if errors:
                    msg_lines = ["❌ Impossible de produire - Stock insuffisant:"]
                    for err in errors:
                        msg_lines.append(
                            f"• {err['product']}: "
                            f"Disponible {err['available']:.2f} {err['uom']}, "
                            f"À consommer {err['to_consume']:.2f} {err['uom']} "
                            f"(Manque {err['missing']:.2f})"
                        )
                    raise UserError('\n'.join(msg_lines))

        res = super()._pre_button_mark_done()

        # Vérifier la surconsommation après
        for production in self:
            if not production.allow_overconsumption:
                for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    qty_done = 0
                    for line in move.move_line_ids:
                        if hasattr(line, 'qty_done'):
                            qty_done += line.qty_done or 0

                    if qty_done and move.product_uom != move.product_id.uom_id:
                        qty_done = move.product_id.uom_id._compute_quantity(
                            qty_done,
                            move.product_uom,
                            rounding_method='HALF-UP'
                        )

                    if qty_done > move.product_uom_qty:
                        raise UserError(
                            _("Surconsommation non autorisée:\n\n"
                              "Produit: %s\n"
                              "Quantité prévue: %.2f %s\n"
                              "Quantité consommée: %.2f %s\n"
                              "Pour autoriser, cochez 'Autoriser surconsommation'.") % (
                                move.product_id.display_name,
                                move.product_uom_qty,
                                move.product_uom.name,
                                qty_done,
                                move.product_uom.name
                            )
                        )

        return res


class StockMove(models.Model):
    """Extension pour les mouvements de stock"""
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """Override pour empêcher la création de lignes si stock insuffisant"""
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)

        # Si c'est un mouvement de production
        if self.raw_material_production_id and self.raw_material_production_id.require_full_availability:
            # Vérifier la disponibilité
            available = self.env['stock.quant']._get_available_quantity(
                self.product_id,
                self.location_id,
                strict=False
            )

            if self.product_uom != self.product_id.uom_id:
                available = self.product_id.uom_id._compute_quantity(
                    available,
                    self.product_uom,
                    rounding_method='HALF-UP'
                )

            qty_todo = quantity or self.product_uom_qty

            if available < qty_todo:
                raise UserError(
                    _("Stock insuffisant pour %s.\n"
                      "Disponible: %.2f %s\n"
                      "Requis: %.2f %s\n\n"
                      "La production nécessite la disponibilité complète de tous les composants.") % (
                        self.product_id.display_name,
                        available,
                        self.product_uom.name,
                        qty_todo,
                        self.product_uom.name
                    )
                )

        return vals

    def _action_done(self, cancel_backorder=False):
        """Vérifier avant de valider le mouvement"""
        production_moves = self.filtered(lambda m: m.raw_material_production_id)

        for move in production_moves:
            production = move.raw_material_production_id

            if production.require_full_availability and move.location_id.usage == 'internal':
                qty_todo = 0
                for ml in move.move_line_ids:
                    if hasattr(ml, 'qty_done'):
                        qty_todo += ml.qty_done or 0

                if qty_todo > 0:
                    available = self.env['stock.quant']._get_available_quantity(
                        move.product_id,
                        move.location_id,
                        strict=False
                    )

                    if move.product_uom != move.product_id.uom_id:
                        available = move.product_id.uom_id._compute_quantity(
                            available,
                            move.product_uom,
                            rounding_method='HALF-UP'
                        )

                    if available < qty_todo:
                        raise UserError(
                            _("Stock insuffisant!\n\n"
                              "Produit: %s\n"
                              "Disponible: %.2f %s\n"
                              "Demandé: %.2f %s\n\n"
                              "Tous les composants doivent être disponibles.") % (
                                move.product_id.display_name,
                                available,
                                move.product_uom.name,
                                qty_todo,
                                move.product_uom.name
                            )
                        )

        return super()._action_done(cancel_backorder=cancel_backorder)
