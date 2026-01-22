# reports/pallet_movement_report.py
from odoo import models, api
from datetime import datetime


class PalletMovementReport(models.AbstractModel):
    _name = 'report.dsi_stock_moves_report.report_pallet_movements'
    _description = 'Rapport Mouvements Palettes'

    def _get_product_movements(self, product, date_start=False, date_end=False):
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done')
        ]
        if date_start:
            domain.append(('date', '>=', date_start))
        if date_end:
            domain.append(('date', '<=', date_end))

        moves = self.env['stock.move'].search(domain, order='date')

        # Calculer la quantité initiale
        initial_qty = product.with_context(to_date=date_start).qty_available if date_start else 0.00

        movements = []
        balance = initial_qty
        for move in moves:
            in_qty = move.product_qty if (move.location_dest_id.usage == 'internal' and move.state == 'done') else 0
            out_qty = move.product_qty if (move.location_id.usage == 'internal' and move.state == 'done') else 0

            if in_qty == out_qty and move.picking_id.partner_id.is_supplier:
                in_qty = 0.00

            balance += in_qty - out_qty


            if move.picking_id.partner_id.is_supplier:
                partner_type = 'Fournisseur'
            else:
                if not move.picking_id.partner_id.name :
                    partner_type = 'Inv. / T.I'
                else:
                    partner_type = 'Client'

            movements.append({
                'date': move.date,
                'reference': move.picking_id.name or move.name,
                'partner_type': partner_type,
                'partner_name': move.picking_id.partner_id.name,
                'in_qty': in_qty,
                'out_qty': out_qty,
                'balance': balance
            })

        return {
            'initial_qty': initial_qty,
            'movements': movements,
            'total_in': sum(m['in_qty'] for m in movements),
            'total_out': sum(m['out_qty'] for m in movements),
            'final_qty': balance
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('product_variant_ids'):
            # Si aucune variante n'est spécifiée, prendre toutes les variantes des palettes
            pallet_products = self.env['product.product'].search([
                ('product_tmpl_id.is_palet', '=', True)
            ])
        else:
            pallet_products = self.env['product.product'].browse(data['product_variant_ids'])

        products_data = {}
        for product in pallet_products:
            products_data[product.id] = {
                'product': product,
                'variant_name': product.get_variant_name(),
                'movements': self._get_product_movements(
                    product,
                    data.get('date_start'),
                    data.get('date_end')
                )
            }

        return {
            'doc_ids': docids,
            'products_data': products_data,
            'date_start': data.get('date_start'),
            'date_end': data.get('date_end'),
        }

