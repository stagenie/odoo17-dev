# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def action_generate_transfer_wizard(self):
        """Ouvre le wizard pour générer un transfert"""
        self.ensure_one()

        # Vérifier la configuration
        company = self.env.company
        if not company.raw_material_warehouse_id or not company.production_warehouse_id:
            raise UserError(_(
                "Veuillez configurer les entrepôts par défaut dans les paramètres de la société:\n"
                "- Entrepôt Matières Premières\n"
                "- Entrepôt Production"
            ))

        # Ouvrir le wizard
        return {
            'name': _('Générer Transfert vers Production'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.id,
                'default_product_id': self.product_tmpl_id.product_variant_ids[
                    0].id if self.product_tmpl_id.product_variant_ids else False,
                'default_source_warehouse_id': company.raw_material_warehouse_id.id,
                'default_dest_warehouse_id': company.production_warehouse_id.id,
            }
        }

    def _get_missing_quantities(self, qty_to_produce, warehouse_id):
        """Calcule les quantités manquantes pour produire"""
        missing_products = []
        location = warehouse_id.lot_stock_id

        for line in self.bom_line_ids:
            product = line.product_id
            qty_needed = line.product_qty * qty_to_produce

            # Quantité disponible dans l'entrepôt
            qty_available = product.with_context(location=location.id).qty_available

            # Quantité manquante
            if qty_available < qty_needed:
                missing_products.append({
                    'product_id': product.id,
                    'product_name': product.display_name,
                    'qty_needed': qty_needed,
                    'qty_available': qty_available,
                    'qty_missing': qty_needed - qty_available,
                    'uom_id': line.product_uom_id.id,
                    'uom_name': line.product_uom_id.name,
                })

        return missing_products
