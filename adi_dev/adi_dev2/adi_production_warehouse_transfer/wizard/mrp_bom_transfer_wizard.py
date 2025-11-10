# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MrpBomTransferWizard(models.TransientModel):
    _name = 'mrp.bom.transfer.wizard'
    _description = 'Assistant de transfert pour nomenclature'

    # Champs principaux
    bom_id = fields.Many2one('mrp.bom', string='Nomenclature', required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Produit', readonly=True)
    qty_to_produce = fields.Float(string='Quantité à produire', default=1.0, required=True)

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt MP',
        required=True,
        default=lambda self: self.env.company.raw_material_warehouse_id
    )

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Entrepôt Production',
        required=True,
        default=lambda self: self.env.company.production_warehouse_id
    )

    transfer_mode = fields.Selection([
        ('missing_only', 'Transférer uniquement les quantités manquantes'),
        ('full_qty', 'Transférer la quantité totale requise'),
        ('available_only', 'Transférer uniquement ce qui est disponible')
    ], string='Mode', default='missing_only', required=True)

    # Lignes calculées automatiquement
    transfer_line_ids = fields.One2many(
        'mrp.bom.transfer.wizard.line',
        'wizard_id',
        string='Articles à transférer',
        compute='_compute_transfer_lines',
        store=True,
        readonly=False
    )

    # Statistiques calculées automatiquement
    total_lines = fields.Integer(
        string='Nombre d\'articles',
        compute='_compute_statistics',
        store=False
    )

    total_to_transfer = fields.Integer(
        string='Articles à transférer',
        compute='_compute_statistics',
        store=False
    )

    has_missing_items = fields.Boolean(
        string='Articles manquants',
        compute='_compute_statistics',
        store=False
    )

    # Champ HTML pour le résumé
    summary_html = fields.Html(
        string='Résumé',
        compute='_compute_summary',
        store=False,
        sanitize=False
    )

    @api.model
    def default_get(self, fields_list):
        """Initialisation automatique"""
        res = super().default_get(fields_list)

        # Récupérer la BOM du contexte
        bom_id = self.env.context.get('default_bom_id')
        if bom_id:
            bom = self.env['mrp.bom'].browse(bom_id)
            if bom.exists():
                res['bom_id'] = bom.id
                # Prendre le premier variant si plusieurs
                if bom.product_tmpl_id.product_variant_ids:
                    res['product_id'] = bom.product_tmpl_id.product_variant_ids[0].id

        return res

    @api.depends('bom_id', 'qty_to_produce', 'source_warehouse_id', 'dest_warehouse_id', 'transfer_mode')
    def _compute_transfer_lines(self):
        """Calcul automatique des lignes à chaque changement"""
        for wizard in self:
            # Nettoyer les anciennes lignes
            wizard.transfer_line_ids = [(5, 0, 0)]

            if not all([wizard.bom_id, wizard.source_warehouse_id, wizard.dest_warehouse_id]):
                continue

            # Obtenir les emplacements
            source_loc = wizard.source_warehouse_id.lot_stock_id
            dest_loc = wizard.dest_warehouse_id.lot_stock_id

            if not source_loc or not dest_loc:
                _logger.warning("Les entrepôts n'ont pas d'emplacement stock défini")
                continue

            # Créer une ligne pour chaque composant de la BOM
            new_lines = []
            for bom_line in wizard.bom_id.bom_line_ids:
                if not bom_line.product_id:
                    continue

                product = bom_line.product_id

                # Calculer les quantités
                qty_per_unit = bom_line.product_qty
                qty_total_needed = qty_per_unit * wizard.qty_to_produce

                # Stock disponible dans chaque entrepôt
                qty_in_source = product.with_context(
                    location=source_loc.id,
                    compute_child=False
                ).qty_available or 0.0

                qty_in_dest = product.with_context(
                    location=dest_loc.id,
                    compute_child=False
                ).qty_available or 0.0

                # Calculer la quantité à transférer selon le mode
                qty_to_transfer = wizard._calculate_transfer_qty(
                    qty_total_needed,
                    qty_in_source,
                    qty_in_dest,
                    wizard.transfer_mode
                )

                # Créer la ligne
                line_vals = {
                    'product_id': product.id,
                    'product_uom_id': bom_line.product_uom_id.id,
                    'qty_per_unit': qty_per_unit,
                    'qty_total_needed': qty_total_needed,
                    'qty_in_source': qty_in_source,
                    'qty_in_dest': qty_in_dest,
                    'qty_missing_in_dest': max(0, qty_total_needed - qty_in_dest),
                    'qty_to_transfer': qty_to_transfer,
                    'is_available': qty_in_source >= qty_to_transfer if qty_to_transfer > 0 else True,
                }

                new_lines.append((0, 0, line_vals))

            wizard.transfer_line_ids = new_lines

    def _calculate_transfer_qty(self, needed, in_source, in_dest, mode):
        """Logique de calcul selon le mode"""
        if mode == 'missing_only':
            # Transférer seulement ce qui manque dans la destination
            missing = max(0, needed - in_dest)
            return min(missing, in_source)

        elif mode == 'full_qty':
            # Transférer tout ce qui est nécessaire (si disponible)
            return min(needed, in_source)

        else:  # available_only
            # Transférer tout ce qui est disponible (jusqu'au besoin)
            return min(in_source, needed)

    @api.depends('transfer_line_ids')
    def _compute_statistics(self):
        """Calcul automatique des statistiques"""
        for wizard in self:
            lines = wizard.transfer_line_ids
            wizard.total_lines = len(lines)
            wizard.total_to_transfer = len(lines.filtered(lambda l: l.qty_to_transfer > 0))
            wizard.has_missing_items = bool(lines.filtered(
                lambda l: l.qty_total_needed > (l.qty_in_dest + l.qty_to_transfer)
            ))

    @api.depends('transfer_line_ids', 'qty_to_produce', 'product_id')
    def _compute_summary(self):
        """Génère un résumé HTML automatique"""
        for wizard in self:
            if not wizard.transfer_line_ids:
                wizard.summary_html = "<div class='alert alert-info'>Aucune donnée à afficher</div>"
                continue

            # Analyser la situation
            ready_items = wizard.transfer_line_ids.filtered(lambda l: l.is_available and l.qty_to_transfer > 0)
            missing_items = wizard.transfer_line_ids.filtered(lambda l: not l.is_available and l.qty_to_transfer > 0)
            no_transfer_items = wizard.transfer_line_ids.filtered(lambda l: l.qty_to_transfer == 0)

            html = "<div style='padding: 10px;'>"

            # Résumé global
            product_name = wizard.product_id.name if wizard.product_id else 'unité(s)'
            html += f"<h4>Production de {wizard.qty_to_produce} {product_name}</h4>"

            # Statut global avec icônes et couleurs
            if ready_items and not missing_items:
                html += """
                    <div class='alert alert-success' style='padding: 10px; margin: 10px 0;'>
                        <i class='fa fa-check-circle'></i> 
                        <strong>Tous les composants sont disponibles pour le transfert</strong>
                    </div>
                """
            elif missing_items:
                html += """
                    <div class='alert alert-warning' style='padding: 10px; margin: 10px 0;'>
                        <i class='fa fa-exclamation-triangle'></i> 
                        <strong>Certains composants ne sont pas entièrement disponibles</strong>
                    </div>
                """
            else:
                html += """
                    <div class='alert alert-danger' style='padding: 10px; margin: 10px 0;'>
                        <i class='fa fa-times-circle'></i> 
                        <strong>Aucun transfert nécessaire ou possible</strong>
                    </div>
                """

            # Tableau de synthèse
            html += """
                <table class='table table-sm table-bordered' style='margin-top: 10px;'>
                    <thead class='thead-light'>
                        <tr>
                            <th>Statut</th>
                            <th>Nombre d'articles</th>
                            <th>Pourcentage</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            total = len(wizard.transfer_line_ids)

            if ready_items:
                pct = len(ready_items) * 100 / total if total else 0
                html += f"""
                    <tr class='table-success'>
                        <td><i class='fa fa-check'></i> Prêts au transfert</td>
                        <td>{len(ready_items)}</td>
                        <td>{pct:.0f}%</td>
                    </tr>
                """

            if missing_items:
                pct = len(missing_items) * 100 / total if total else 0
                html += f"""
                    <tr class='table-warning'>
                        <td><i class='fa fa-exclamation'></i> Stock insuffisant</td>
                        <td>{len(missing_items)}</td>
                        <td>{pct:.0f}%</td>
                    </tr>
                """

            if no_transfer_items:
                pct = len(no_transfer_items) * 100 / total if total else 0
                html += f"""
                    <tr class='table-info'>
                        <td><i class='fa fa-info'></i> Pas de transfert nécessaire</td>
                        <td>{len(no_transfer_items)}</td>
                        <td>{pct:.0f}%</td>
                    </tr>
                """

            html += "</tbody></table>"

            # Articles critiques (aucun stock)
            critical_items = wizard.transfer_line_ids.filtered(
                lambda l: l.qty_missing_in_dest > 0 and l.qty_in_source == 0
            )

            if critical_items:
                html += """
                    <div class='alert alert-danger' style='margin-top: 15px;'>
                        <h5><i class='fa fa-exclamation-circle'></i> Articles critiques (aucun stock disponible) :</h5>
                        <ul style='margin-bottom: 0;'>
                """
                for item in critical_items[:5]:  # Limiter à 5
                    html += f"<li><strong>{item.product_id.name}</strong> - Besoin: {item.qty_total_needed:.0f} {item.product_uom_id.name}</li>"

                if len(critical_items) > 5:
                    html += f"<li><em>... et {len(critical_items) - 5} autres articles</em></li>"

                html += "</ul></div>"

            # Conseils selon la situation
            if missing_items:
                html += """
                    <div class='alert alert-info' style='margin-top: 10px;'>
                        <i class='fa fa-lightbulb-o'></i> 
                        <strong>Conseil :</strong> Vérifiez les approvisionnements nécessaires pour les articles manquants.
                    </div>
                """

            html += "</div>"
            wizard.summary_html = html

    def action_create_transfer(self):
        """Crée automatiquement le transfert optimisé"""
        self.ensure_one()

        # Filtrer uniquement les lignes avec quantité > 0
        lines_to_transfer = self.transfer_line_ids.filtered(lambda l: l.qty_to_transfer > 0)

        if not lines_to_transfer:
            raise UserError(_(
                "Aucune quantité à transférer.\n\n"
                "Vérifiez :\n"
                "- Le stock disponible dans l'entrepôt source\n"
                "- Le mode de transfert sélectionné"
            ))

        # Chercher le type d'opération pour les transferts internes
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            '|',
            ('warehouse_id', '=', self.source_warehouse_id.id),
            ('warehouse_id', '=', False)
        ], limit=1)

        if not picking_type:
            raise UserError(_("Configuration manquante : Aucun type de transfert interne trouvé."))

        # Construire l'origine du transfert
        bom_reference = self.bom_id.code or self.bom_id.product_tmpl_id.name
        origin = f"BOM/{bom_reference}/QTY:{self.qty_to_produce}"

        # Si on vient d'un ordre de fabrication, ajouter sa référence
        production = False
        if self.env.context.get('production_id'):
            production = self.env['mrp.production'].browse(self.env.context.get('production_id'))
            if production.exists():
                origin = f"MO/{production.name}/{origin}"

        # Créer le picking avec toutes les informations
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.source_warehouse_id.lot_stock_id.id,
            'location_dest_id': self.dest_warehouse_id.lot_stock_id.id,
            'origin': origin,
            'note': self._generate_transfer_note(lines_to_transfer),
            'priority': '1' if self.has_missing_items else '0',  # Urgent si manquants
            'company_id': self.env.company.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Créer les mouvements de stock
        for line in lines_to_transfer:
            move_vals = {
                'name': f"{line.product_id.display_name}",
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty_to_transfer,
                'product_uom': line.product_uom_id.id,
                'location_id': self.source_warehouse_id.lot_stock_id.id,
                'location_dest_id': self.dest_warehouse_id.lot_stock_id.id,
                'picking_id': picking.id,
                'origin': picking.origin,
                'company_id': self.env.company.id,
                'procure_method': 'make_to_stock',
                'group_id': False,
            }
            self.env['stock.move'].create(move_vals)

        # Confirmer et tenter d'assigner le stock
        picking.action_confirm()
        picking.action_assign()

        # Message de statut
        msg = ""

        # Si validation automatique activée et tout est disponible
        if self.env.company.auto_validate_internal_transfers:
            if picking.state == 'assigned':
                # Définir les quantités done = demandées pour chaque ligne
                for move in picking.move_ids:
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty

                # Valider le transfert
                try:
                    picking.button_validate()
                    msg = _("✅ Transfert %s créé et validé automatiquement") % picking.name
                except Exception as e:
                    msg = _("⚠️ Transfert %s créé mais validation échouée: %s") % (picking.name, str(e))
            else:
                msg = _("⚠️ Transfert %s créé mais en attente de disponibilité") % picking.name
        else:
            msg = _("✅ Transfert %s créé avec succès") % picking.name

        # Message dans le picking créé
        picking_msg_body = _(
            "📋 <b>Transfert créé depuis %s</b><br/>"
            "• Quantité à produire: %s<br/>"
            "• Mode: %s<br/>"
            "• Articles: %d<br/>"
        ) % (
                               self.bom_id.display_name,
                               self.qty_to_produce,
                               dict(self._fields['transfer_mode'].selection)[self.transfer_mode],
                               len(lines_to_transfer)
                           )

        # Ajouter le détail des articles
        if len(lines_to_transfer) <= 10:
            picking_msg_body += _("<br/><b>Détail des articles:</b><br/>")
            for line in lines_to_transfer:
                picking_msg_body += f"• {line.product_id.name}: {line.qty_to_transfer:.2f} {line.product_uom_id.name}<br/>"

        picking.message_post(body=picking_msg_body, subtype_xmlid='mail.mt_note')

        # Si on vient d'un OF, ajouter un message dans l'OF
        if production:
            production_msg = _(
                "📦 <b>Transfert %s créé pour alimenter cet ordre de fabrication</b><br/>"
                "• %d article(s) à transférer<br/>"
                "• De: %s<br/>"
                "• Vers: %s<br/>"
                "• État: %s"
            ) % (
                                 picking.name,
                                 len(lines_to_transfer),
                                 self.source_warehouse_id.name,
                                 self.dest_warehouse_id.name,
                                 dict(picking._fields['state'].selection)[picking.state]
                             )
            production.message_post(body=production_msg, subtype_xmlid='mail.mt_note')

        # Message sur la BOM aussi
        bom_msg = _(
            "🚚 <b>Nouveau transfert créé</b><br/>"
            "• Référence: %s<br/>"
            "• Quantité produite: %s %s<br/>"
            "• Articles transférés: %d"
        ) % (
                      picking.name,
                      self.qty_to_produce,
                      self.product_id.uom_id.name if self.product_id else '',
                      len(lines_to_transfer)
                  )
        self.bom_id.message_post(body=bom_msg, subtype_xmlid='mail.mt_note')

        # Notification utilisateur (si la méthode existe)
        if hasattr(self.env.user, 'notify_success'):
            self.env.user.notify_success(
                message=msg,
                title=_("Transfert créé"),
                sticky=False
            )

        # Créer les demandes d'achat si nécessaire
        self._create_purchase_requests()

        # Retourner l'action pour afficher le picking créé
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'no_breadcrumbs': True,
                'form_view_initial_mode': 'readonly',
            },
        }

    def _generate_transfer_note(self, lines):
        """Génère une note détaillée pour le transfert"""
        note = []

        # Informations générales
        note.append(f"📋 Transfert automatique pour production")
        note.append(f"=====================================")
        note.append(f"")
        note.append(f"• Produit: {self.product_id.name if self.product_id else 'N/A'}")
        note.append(f"• Quantité à produire: {self.qty_to_produce}")
        note.append(f"• Nomenclature: {self.bom_id.code or self.bom_id.product_tmpl_id.name}")
        note.append(f"• Mode: {dict(self._fields['transfer_mode'].selection)[self.transfer_mode]}")
        note.append(f"• Nombre d'articles: {len(lines)}")
        note.append(f"• Date de création: {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}")
        note.append(f"• Créé par: {self.env.user.name}")

        # Si on vient d'un OF
        if self.env.context.get('production_id'):
            production = self.env['mrp.production'].browse(self.env.context.get('production_id'))
            if production.exists():
                note.append(f"• Ordre de fabrication: {production.name}")
                note.append(f"• État OF: {production.state}")
                # On évite d'afficher la date pour éviter l'erreur

        # Détail des articles
        note.append(f"")
        note.append(f"📦 Détail des articles à transférer:")
        note.append(f"====================================")
        for i, line in enumerate(lines, 1):
            note.append(
                f"{i}. {line.product_id.default_code or ''} - {line.product_id.name}: "
                f"{line.qty_to_transfer:.2f} {line.product_uom_id.name}"
            )
            if line.qty_to_transfer < line.qty_total_needed:
                note.append(f"   ⚠️ Quantité partielle (Besoin total: {line.qty_total_needed:.2f})")

        return '\n'.join(note)

    def _create_purchase_requests(self):
        """Crée des demandes d'achat pour les produits manquants"""
        purchase_lines = []

        for line in self.transfer_line_ids:
            # Si on a besoin de plus que ce qui est disponible en stock MP
            # CORRECTION: Utiliser qty_total_needed au lieu de qty_needed
            shortage = line.qty_total_needed - (line.qty_in_dest + line.qty_to_transfer)

            if shortage > 0 and line.product_id.seller_ids:
                # Prendre le premier fournisseur
                supplier = line.product_id.seller_ids[0].partner_id

                purchase_lines.append({
                    'product_id': line.product_id,
                    'shortage': shortage,
                    'supplier_id': supplier.id,
                    'product_uom_id': line.product_uom_id,
                })

        # Grouper par fournisseur
        if purchase_lines:
            suppliers = {}
            for line in purchase_lines:
                if line['supplier_id'] not in suppliers:
                    suppliers[line['supplier_id']] = []
                suppliers[line['supplier_id']].append(line)

            # Message d'information
            msg_parts = [_("📌 <b>Articles à commander pour compléter le stock:</b>")]

            for supplier_id, lines in suppliers.items():
                supplier = self.env['res.partner'].browse(supplier_id)
                msg_parts.append(f"<br/><b>Fournisseur: {supplier.name}</b>")

                total_articles = len(lines)
                # Afficher max 5 articles par fournisseur
                for i, line in enumerate(lines[:5], 1):
                    msg_parts.append(
                        f"• {line['product_id'].default_code or ''} - {line['product_id'].name}: "
                        f"{line['shortage']:.2f} {line['product_uom_id'].name}"
                    )

                if total_articles > 5:
                    msg_parts.append(f"<em>... et {total_articles - 5} autres articles</em>")

            msg = '<br/>'.join(msg_parts)

            # Poster le message sur la BOM
            self.bom_id.message_post(body=msg, subtype_xmlid='mail.mt_note')

            # Si on vient d'un OF, poster aussi sur l'OF
            if self.env.context.get('production_id'):
                production = self.env['mrp.production'].browse(self.env.context.get('production_id'))
                if production.exists():
                    production.message_post(body=msg, subtype_xmlid='mail.mt_note')


class MrpBomTransferWizardLine(models.TransientModel):
    _name = 'mrp.bom.transfer.wizard.line'
    _description = 'Ligne de transfert automatique'
    _order = 'is_available desc, qty_to_transfer desc'

    wizard_id = fields.Many2one('mrp.bom.transfer.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Article', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unité', required=True)

    # Informations de base
    qty_per_unit = fields.Float(string='Qté/unité', readonly=True, help="Quantité nécessaire par unité produite")
    qty_total_needed = fields.Float(string='Besoin total', readonly=True,
                                    help="Quantité totale nécessaire pour la production")

    # Stocks actuels
    qty_in_source = fields.Float(string='Stock MP', readonly=True,
                                 help="Stock disponible dans l'entrepôt matières premières")
    qty_in_dest = fields.Float(string='Stock Prod', readonly=True, help="Stock disponible dans l'entrepôt production")
    qty_missing_in_dest = fields.Float(string='Manquant', readonly=True,
                                       help="Quantité manquante dans l'entrepôt production")

    # Transfert
    qty_to_transfer = fields.Float(string='À transférer', help="Quantité qui sera transférée")
    is_available = fields.Boolean(string='Disponible', readonly=True,
                                  help="Indique si la quantité est disponible pour le transfert")

    # Statut visuel
    status = fields.Selection([
        ('ok', 'Disponible'),
        ('partial', 'Partiel'),
        ('missing', 'Manquant')
    ], string='Statut', compute='_compute_status')

    @api.depends('qty_to_transfer', 'qty_in_source', 'qty_total_needed', 'qty_in_dest')
    def _compute_status(self):
        """Calcul automatique du statut visuel"""
        for line in self:
            if line.qty_in_dest >= line.qty_total_needed:
                line.status = 'ok'
            elif line.qty_in_source >= line.qty_missing_in_dest:
                line.status = 'ok'
            elif line.qty_in_source > 0:
                line.status = 'partial'
            else:
                line.status = 'missing'

    @api.onchange('qty_to_transfer')
    def _onchange_check_qty(self):
        """Vérification automatique lors de la modification manuelle"""
        if self.qty_to_transfer > self.qty_in_source:
            self.qty_to_transfer = self.qty_in_source
            return {
                'warning': {
                    'title': _('Quantité ajustée'),
                    'message': _('Maximum disponible : %s %s') % (self.qty_in_source, self.product_uom_id.name)
                }
            }
