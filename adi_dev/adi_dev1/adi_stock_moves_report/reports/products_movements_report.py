from odoo import models, api

class ProductMovementReport(models.AbstractModel):
    _name = 'report.adi_stock_moves_report.report_product_movements'
    _description = 'Rapport Mouvements Produits'

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


        initial_qty = product.with_context(to_date=date_start).qty_available if date_start else 0.00

        movements = []
        balance = initial_qty


        for move in moves:
            in_qty = move.product_qty if (move.location_dest_id.usage == 'internal' and move.state == 'done') else 0
            out_qty = move.product_qty if (move.location_id.usage == 'internal' and move.state == 'done') else 0
            balance += in_qty - out_qty
            
            if not move.picking_id.partner_id.name:
                    partner_type = 'Inv. / T.I'
            else:
                if  move.picking_id.partner_id.customer_rank > 0:
                    partner_type = 'Client'
                elif move.picking_id.partner_id.supplier_rank > 0:
                    partner_type = 'Fournisseur'
                else :
                    partner_type = 'partenaire' 


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
        products = self.env['product.product'].browse(data['product_ids'])

        products_data = {}
        for product in products:
            products_data[product.id] = {
                'product': product,
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