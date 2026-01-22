# -*- coding: utf-8 -*-

from odoo import models, api


class ProductMovementEnhancedReport(models.AbstractModel):
    _name = 'report.adi_stock_moves_report_enhanced.report_movements'
    _description = 'Rapport Mouvements Produits Amélioré'

    def _get_product_movements(self, product, location_ids, date_start=False, date_end=False):
        """
        Récupérer les mouvements d'un produit filtrés par emplacements.

        Args:
            product: product.product record
            location_ids: liste des IDs d'emplacements à inclure
            date_start: date de début (optionnel)
            date_end: date de fin (optionnel)

        Returns:
            dict avec initial_qty, movements, total_in, total_out, final_qty
        """
        # Domaine de base
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
        ]

        # Filtre par date
        if date_start:
            domain.append(('date', '>=', date_start))
        if date_end:
            domain.append(('date', '<=', date_end))

        # Filtre par emplacements (source OU destination doit être dans les emplacements)
        if location_ids:
            domain.append('|')
            domain.append(('location_id', 'in', location_ids))
            domain.append(('location_dest_id', 'in', location_ids))

        moves = self.env['stock.move'].search(domain, order='date')

        # Calculer la quantité initiale pour les emplacements sélectionnés
        if date_start and location_ids:
            # Quantité initiale = somme des quantités dans les emplacements sélectionnés à date_start
            initial_qty = 0.0
            for location_id in location_ids:
                location = self.env['stock.location'].browse(location_id)
                qty = product.with_context(
                    to_date=date_start,
                    location=location_id
                ).qty_available
                initial_qty += qty
        elif location_ids:
            initial_qty = 0.0
        else:
            initial_qty = product.with_context(to_date=date_start).qty_available if date_start else 0.0

        movements = []
        balance = initial_qty

        for move in moves:
            # Déterminer si c'est une entrée ou une sortie pour les emplacements sélectionnés
            in_qty = 0.0
            out_qty = 0.0

            if location_ids:
                # Entrée = destination dans les emplacements sélectionnés
                if move.location_dest_id.id in location_ids and move.location_dest_id.usage == 'internal':
                    in_qty = move.product_qty
                # Sortie = source dans les emplacements sélectionnés
                if move.location_id.id in location_ids and move.location_id.usage == 'internal':
                    out_qty = move.product_qty
            else:
                # Sans filtre emplacement, utiliser la logique standard
                if move.location_dest_id.usage == 'internal':
                    in_qty = move.product_qty
                if move.location_id.usage == 'internal':
                    out_qty = move.product_qty

            balance += in_qty - out_qty

            # Déterminer le type de partenaire
            if not move.picking_id.partner_id.name:
                partner_type = 'Inv. / T.I'
            else:
                if move.picking_id.partner_id.customer_rank > 0:
                    partner_type = 'Client'
                elif move.picking_id.partner_id.supplier_rank > 0:
                    partner_type = 'Fournisseur'
                else:
                    partner_type = 'Partenaire'

            # Informations sur l'emplacement
            location_info = ""
            if move.location_id.usage == 'internal' and move.location_dest_id.usage == 'internal':
                location_info = f"{move.location_id.name} → {move.location_dest_id.name}"
            elif move.location_dest_id.usage == 'internal':
                location_info = f"→ {move.location_dest_id.name}"
            elif move.location_id.usage == 'internal':
                location_info = f"{move.location_id.name} →"

            movements.append({
                'date': move.date,
                'reference': move.picking_id.name or move.name,
                'partner_type': partner_type,
                'partner_name': move.picking_id.partner_id.name or '',
                'location_info': location_info,
                'location_src': move.location_id.display_name,
                'location_dest': move.location_dest_id.display_name,
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
        """Préparer les valeurs pour le rapport."""
        products = self.env['product.product'].browse(data.get('product_ids', []))
        location_ids = data.get('location_ids', [])
        warehouse_ids = data.get('warehouse_ids', [])

        # Récupérer les noms des entrepôts et emplacements pour l'affichage
        warehouses = self.env['stock.warehouse'].browse(warehouse_ids) if warehouse_ids else False
        locations = self.env['stock.location'].browse(location_ids) if location_ids else False

        products_data = {}
        for product in products:
            movements_data = self._get_product_movements(
                product,
                location_ids,
                data.get('date_start'),
                data.get('date_end')
            )
            # Ne pas inclure les produits sans mouvements
            if movements_data['movements'] or movements_data['initial_qty'] != 0:
                products_data[product.id] = {
                    'product': product,
                    'movements': movements_data
                }

        return {
            'doc_ids': docids,
            'products_data': products_data,
            'date_start': data.get('date_start'),
            'date_end': data.get('date_end'),
            'warehouses': warehouses,
            'locations': locations,
            'show_all_warehouses': data.get('show_all_warehouses', True),
            'show_all_locations': data.get('show_all_locations', True),
        }
