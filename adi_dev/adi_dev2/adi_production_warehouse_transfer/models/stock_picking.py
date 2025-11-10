# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_production_transfer = fields.Boolean(
        string='Transfert de production',
        compute='_compute_is_production_transfer',
        store=True
    )

    transfer_priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Très urgent'),
        ('3', 'Critique')
    ], string='Priorité du transfert', default='0')

    production_order_ids = fields.Many2many(
        'mrp.production',
        string='Ordres de fabrication liés',
        compute='_compute_production_orders'
    )

    shortage_alert = fields.Boolean(
        string='Alerte rupture',
        compute='_compute_shortage_alert'
    )

    @api.depends('origin', 'picking_type_id')
    def _compute_is_production_transfer(self):
        """Détermine si c'est un transfert de production"""
        for picking in self:
            picking.is_production_transfer = (
                    picking.picking_type_id.code == 'internal' and
                    picking.origin and
                    'BOM/' in picking.origin
            )

    def _compute_production_orders(self):
        """Trouve les ordres de fabrication liés"""
        for picking in self:
            # Rechercher par les produits
            products = picking.move_ids.mapped('product_id')
            productions = self.env['mrp.production'].search([
                ('state', 'not in', ['done', 'cancel']),
                ('move_raw_ids.product_id', 'in', products.ids)
            ])

            picking.production_order_ids = productions

    def _get_move_reserved_qty(self, move):
        """Méthode helper pour obtenir la quantité réservée d'un mouvement"""
        qty_reserved = 0

        # Option 1: Vérifier qty_done sur les move lines
        if move.move_line_ids:
            # Essayer différents noms de champs selon la version
            for field_name in ['qty_done', 'product_qty', 'reserved_uom_qty', 'product_uom_qty']:
                if hasattr(move.move_line_ids[0], field_name):
                    qty_reserved = sum(move.move_line_ids.mapped(field_name))
                    _logger.debug(f"Utilisation du champ {field_name} pour calculer la réservation")
                    break

        # Option 2: Utiliser l'état du mouvement
        if qty_reserved == 0 and move.state == 'assigned':
            qty_reserved = move.product_uom_qty

        # Option 3: Vérifier forecast_availability ou availability
        if qty_reserved == 0:
            for field_name in ['forecast_availability', 'availability', 'reserved_availability']:
                if hasattr(move, field_name):
                    qty_reserved = getattr(move, field_name, 0)
                    if qty_reserved:
                        break

        return qty_reserved

    def _compute_shortage_alert(self):
        """Vérifie s'il y a des ruptures de stock"""
        for picking in self:
            shortage = False

            if picking.state not in ('done', 'cancel'):
                for move in picking.move_ids:
                    qty_reserved = self._get_move_reserved_qty(move)

                    if qty_reserved < move.product_uom_qty:
                        shortage = True
                        break

            picking.shortage_alert = shortage

    def button_validate(self):
        """Override pour ajouter des contrôles sur les transferts de production"""
        for picking in self:
            if picking.is_production_transfer:
                # Vérifier si tous les produits sont disponibles
                unavailable_moves = []

                for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    qty_reserved = self._get_move_reserved_qty(move)

                    # Vérifier si la quantité réservée est suffisante
                    if qty_reserved < move.product_uom_qty:
                        unavailable_moves.append({
                            'move': move,
                            'qty_reserved': qty_reserved,
                            'qty_needed': move.product_uom_qty
                        })

                if unavailable_moves:
                    # Message d'avertissement mais pas de blocage
                    msg = _("⚠️ Attention ! Les produits suivants ne sont pas entièrement disponibles:\n")
                    for item in unavailable_moves:
                        move = item['move']
                        missing = item['qty_needed'] - item['qty_reserved']
                        msg += f"\n• {move.product_id.display_name}: "
                        msg += f"Manque {missing:.2f} {move.product_uom.name}"
                        msg += f" (Disponible: {item['qty_reserved']:.2f}, Requis: {item['qty_needed']:.2f})"

                    # Ajouter un message dans le chatter
                    picking.message_post(body=msg, message_type='notification')

                # Notifier les ordres de fabrication liés
                if picking.production_order_ids:
                    msg = _("✅ Le transfert %s a été validé.") % picking.name
                    for production in picking.production_order_ids:
                        production.message_post(body=msg)

        return super().button_validate()

    def action_set_priority(self):
        """Action pour définir la priorité rapidement"""
        return {
            'name': _('Définir la priorité'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.priority.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_ids': [(6, 0, self.ids)]
            }
        }

    @api.model
    def get_production_transfer_stats(self):
        """Retourne les statistiques pour le tableau de bord"""
        domain = [('is_production_transfer', '=', True)]

        stats = {
            'total': self.search_count(domain),
            'pending': self.search_count(domain + [('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])]),
            'done': self.search_count(domain + [('state', '=', 'done')]),
            'urgent': self.search_count(domain + [('transfer_priority', 'in', ['2', '3'])]),
            'with_shortage': self.search_count(domain + [('shortage_alert', '=', True)]),
        }

        return stats

    def action_generate_purchase_order(self):
        """Génère des commandes d'achat pour les produits manquants"""
        self.ensure_one()

        if not self.shortage_alert:
            raise UserError(_("Aucun produit manquant dans ce transfert."))

        # Collecter les produits manquants
        purchase_lines = []
        for move in self.move_ids:
            qty_reserved = self._get_move_reserved_qty(move)
            missing_qty = move.product_uom_qty - qty_reserved

            if missing_qty > 0 and move.product_id.seller_ids:
                supplier = move.product_id.seller_ids[0].partner_id
                purchase_lines.append({
                    'product_id': move.product_id.id,
                    'product_qty': missing_qty,
                    'product_uom': move.product_uom.id,
                    'partner_id': supplier.id,
                })

        if not purchase_lines:
            raise UserError(_("Aucun fournisseur trouvé pour les produits manquants."))

        # Grouper par fournisseur et créer les PO
        suppliers = {}
        for line in purchase_lines:
            if line['partner_id'] not in suppliers:
                suppliers[line['partner_id']] = []
            suppliers[line['partner_id']].append(line)

        purchase_orders = self.env['purchase.order']
        for partner_id, lines in suppliers.items():
            po = self.env['purchase.order'].create({
                'partner_id': partner_id,
                'origin': self.name,
            })

            for line in lines:
                self.env['purchase.order.line'].create({
                    'order_id': po.id,
                    'product_id': line['product_id'],
                    'product_qty': line['product_qty'],
                    'product_uom': line['product_uom'],
                })

            purchase_orders |= po

        # Retourner l'action pour afficher les PO
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        action['domain'] = [('id', 'in', purchase_orders.ids)]
        return action


class StockMove(models.Model):
    _inherit = 'stock.move'

    production_transfer_notes = fields.Text(
        string='Notes de transfert production'
    )

    def _get_reserved_quantity(self):
        """Obtient la quantité réservée pour ce mouvement - Compatible toutes versions"""
        self.ensure_one()

        # Utiliser la méthode du picking si disponible
        if self.picking_id and hasattr(self.picking_id, '_get_move_reserved_qty'):
            return self.picking_id._get_move_reserved_qty(self)

        # Sinon, calcul simple basé sur l'état
        if self.state == 'assigned':
            return self.product_uom_qty
        elif self.state in ('done', 'cancel'):
            return 0
        else:
            # Essayer de calculer via les move lines
            if self.move_line_ids:
                # Chercher le bon champ
                for field in ['qty_done', 'product_qty', 'product_uom_qty']:
                    if hasattr(self.move_line_ids[0], field):
                        return sum(self.move_line_ids.mapped(field))
            return 0

    def _action_assign(self):
        """Override pour gérer les priorités de transfert"""
        res = super()._action_assign()

        # Pour les transferts de production urgents
        for move in self.filtered(lambda m: m.picking_id.is_production_transfer and
                                            m.picking_id.transfer_priority in ['2', '3']):
            if move.state not in ('done', 'cancel', 'assigned'):
                # Essayer de forcer l'assignation si possible
                available_qty = self.env['stock.quant']._get_available_quantity(
                    move.product_id,
                    move.location_id,
                    strict=False
                )

                if available_qty > 0:
                    # Log pour debug
                    move.picking_id.message_post(
                        body=_("⚡ Tentative d'assignation prioritaire pour %s (Disponible: %.2f)") %
                             (move.product_id.display_name, available_qty)
                    )

        return res
