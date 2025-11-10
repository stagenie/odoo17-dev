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
                errors.append(
                    f"• {product.display_name}: "
                    f"Requis {qty_required:.2f} {move.product_uom.name}, "
                    f"Disponible {qty_available:.2f} {move.product_uom.name} "
                    f"(Manque {qty_required - qty_available:.2f})"
                )

        return errors

    def action_confirm(self):
        """Vérifier le stock avant de confirmer"""
        for production in self:
            # Ne vérifier que si la production n'est pas déjà confirmée
            if production.state == 'draft':
                errors = production._check_components_availability()
                if errors:
                    raise UserError(
                        _("Stock insuffisant pour confirmer la production %s:\n\n%s") %
                        (production.name, '\n'.join(errors))
                    )

        return super().action_confirm()

    def _pre_button_mark_done(self):
        """Hook avant de marquer la production comme terminée"""
        res = super()._pre_button_mark_done()

        for production in self:
            # Vérifier la surconsommation
            if not production.allow_overconsumption:
                for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    # Calculer la quantité totale consommée
                    qty_done = 0
                    for line in move.move_line_ids:
                        if hasattr(line, 'qty_done'):
                            qty_done += line.qty_done or 0

                    # Convertir si nécessaire
                    if qty_done and move.product_uom != move.product_id.uom_id:
                        qty_done = move.product_id.uom_id._compute_quantity(
                            qty_done,
                            move.product_uom,
                            rounding_method='HALF-UP'
                        )

                    # Vérifier surconsommation
                    if qty_done > move.product_uom_qty:
                        raise UserError(
                            _("Surconsommation non autorisée détectée:\n\n"
                              "Produit: %s\n"
                              "Quantité prévue: %.2f %s\n"
                              "Quantité consommée: %.2f %s\n"
                              "Excès: %.2f %s\n\n"
                              "Pour autoriser, cochez 'Autoriser surconsommation' dans l'ordre de fabrication.") % (
                                move.product_id.display_name,
                                move.product_uom_qty,
                                move.product_uom.name,
                                qty_done,
                                move.product_uom.name,
                                qty_done - move.product_uom_qty,
                                move.product_uom.name
                            )
                        )

        return res

    def action_assign(self):
        """Vérifier la disponibilité lors de l'assignation"""
        res = super().action_assign()

        for production in self:
            # Afficher un avertissement si pas tout disponible
            moves_not_ready = production.move_raw_ids.filtered(
                lambda m: m.state not in ('assigned', 'done', 'cancel')
            )
            if moves_not_ready:
                products = ', '.join(moves_not_ready.mapped('product_id.display_name'))
                # Log warning sans bloquer
                production.message_post(
                    body=_("Attention: Les composants suivants ne sont pas entièrement disponibles: %s") % products
                )

        return res


class StockMove(models.Model):
    """Extension pour les mouvements de stock"""
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """Vérifier avant de valider le mouvement"""
        # Pour les mouvements de production uniquement
        production_moves = self.filtered(lambda m: m.raw_material_production_id)

        for move in production_moves:
            production = move.raw_material_production_id

            # Si production avec contrôle de stock
            if move.location_id.usage == 'internal':
                # Calculer quantité à consommer
                qty_todo = 0
                for ml in move.move_line_ids:
                    if hasattr(ml, 'qty_done'):
                        qty_todo += ml.qty_done or 0

                if qty_todo > 0:
                    # Vérifier disponibilité
                    available = self.env['stock.quant']._get_available_quantity(
                        move.product_id,
                        move.location_id,
                        strict=False
                    )

                    # Convertir si nécessaire
                    if move.product_uom != move.product_id.uom_id:
                        available = move.product_id.uom_id._compute_quantity(
                            available,
                            move.product_uom,
                            rounding_method='HALF-UP'
                        )

                    # Bloquer si insuffisant
                    if available < qty_todo:
                        raise UserError(
                            _("Stock insuffisant!\n\n"
                              "Produit: %s\n"
                              "Emplacement: %s\n"
                              "Disponible: %.2f %s\n"
                              "Demandé: %.2f %s\n"
                              "Manque: %.2f %s") % (
                                move.product_id.display_name,
                                move.location_id.display_name,
                                available,
                                move.product_uom.name,
                                qty_todo,
                                move.product_uom.name,
                                qty_todo - available,
                                move.product_uom.name
                            )
                        )

                    # Vérifier surconsommation
                    if not production.allow_overconsumption and qty_todo > move.product_uom_qty:
                        raise UserError(
                            _("Surconsommation non autorisée!\n\n"
                              "Produit: %s\n"
                              "Quantité prévue: %.2f %s\n"
                              "Quantité à consommer: %.2f %s") % (
                                move.product_id.display_name,
                                move.product_uom_qty,
                                move.product_uom.name,
                                qty_todo,
                                move.product_uom.name
                            )
                        )

        return super()._action_done(cancel_backorder=cancel_backorder)


class StockQuant(models.Model):
    """Contrainte sur les quantités négatives"""
    _inherit = 'stock.quant'

    @api.constrains('quantity')
    def _check_negative_qty_production(self):
        """Empêche stock négatif pour la production"""
        for quant in self:
            if (quant.location_id.usage == 'internal' and
                    quant.quantity < 0 and
                    quant.product_id.type == 'product'):

                # Chercher si lié à une production
                domain = [
                    ('product_id', '=', quant.product_id.id),
                    ('location_id', '=', quant.location_id.id),
                    ('state', 'not in', ['cancel', 'done']),
                    ('raw_material_production_id', '!=', False)
                ]

                if self.env['stock.move'].search_count(domain, limit=1):
                    raise UserError(
                        _("Stock négatif non autorisé!\n\n"
                          "Produit: %s\n"
                          "Emplacement: %s\n"
                          "Quantité: %.2f\n\n"
                          "Le stock ne peut pas être négatif pour les mouvements de production.") % (
                            quant.product_id.display_name,
                            quant.location_id.complete_name,
                            quant.quantity
                        )
                    )
