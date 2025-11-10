# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Champs calculés pour le bouton intelligent
    production_transfer_count = fields.Integer(
        string='Nombre de transferts',
        compute='_compute_production_transfers'
    )

    production_transfer_ids = fields.One2many(
        'stock.picking',
        compute='_compute_production_transfers',
        string='Transferts de production'
    )

    @api.depends('origin', 'name', 'bom_id')
    def _compute_production_transfers(self):
        """Calcule les transferts liés à cet ordre de fabrication"""
        for production in self:
            # Initialiser
            production.production_transfer_ids = False
            production.production_transfer_count = 0

            if not production.name:
                continue

            # Rechercher les pickings qui ont comme origine cet OF ou sa BOM
            domain = [
                ('picking_type_id.code', '=', 'internal'),
                '|',
                ('origin', 'ilike', f'MO/{production.name}'),
                ('origin', 'ilike', production.name)
            ]

            # Si une BOM est définie, chercher aussi par BOM
            if production.bom_id:
                domain = ['|'] + domain + [
                    ('origin', 'ilike', f'BOM/{production.bom_id.code or production.bom_id.product_tmpl_id.name}')
                ]

            transfers = self.env['stock.picking'].search(domain)
            production.production_transfer_ids = transfers
            production.production_transfer_count = len(transfers)

    def action_generate_transfer_wizard(self):
        """Ouvre le wizard de transfert avec les bonnes valeurs par défaut"""
        self.ensure_one()

        # Vérifier qu'une BOM est définie
        if not self.bom_id:
            raise UserError(_("Aucune nomenclature définie pour cet ordre de fabrication."))

        # Vérifier la configuration des entrepôts
        company = self.env.company
        if not company.raw_material_warehouse_id or not company.production_warehouse_id:
            raise UserError(_(
                "Veuillez configurer les entrepôts par défaut dans les paramètres de la société:\n"
                "- Entrepôt Matières Premières\n"
                "- Entrepôt Production"
            ))

        # Ouvrir le wizard avec les valeurs pré-remplies
        action = {
            'name': _('Générer Transfert MP → Production'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.bom_id.id,
                'default_product_id': self.product_id.id,
                'default_qty_to_produce': self.product_qty,
                'default_source_warehouse_id': company.raw_material_warehouse_id.id,
                'default_dest_warehouse_id': company.production_warehouse_id.id,
                'default_transfer_mode': 'missing_only',
                'production_id': self.id,  # Pour référence dans le wizard
                'dialog_size': 'extra-large',
            }
        }

        return action

    def action_view_production_transfers(self):
        """Affiche tous les transferts liés à cet OF"""
        self.ensure_one()

        if not self.production_transfer_ids:
            raise UserError(_("Aucun transfert trouvé pour cet ordre de fabrication."))

        # Récupérer l'action de base
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')

        # Adapter pour nos transferts
        action.update({
            'domain': [('id', 'in', self.production_transfer_ids.ids)],
            'context': {
                'search_default_not_done': 1,
                'default_origin': f'MO/{self.name}',
                'create': False,
            }
        })

        # Si un seul transfert, ouvrir directement en vue form
        if len(self.production_transfer_ids) == 1:
            action.update({
                'res_id': self.production_transfer_ids.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        else:
            action['view_mode'] = 'tree,form'

        return action
