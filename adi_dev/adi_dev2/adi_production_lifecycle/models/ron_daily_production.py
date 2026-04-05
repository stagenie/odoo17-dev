# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RonDailyProductionLifecycle(models.Model):
    _inherit = 'ron.daily.production'

    # ================== CHAMPS ==================

    return_picking_ids = fields.Many2many(
        'stock.picking',
        'ron_production_return_picking_rel',
        'production_id', 'picking_id',
        string="Retours de stock",
        readonly=True,
        copy=False,
    )
    return_picking_count = fields.Integer(
        compute='_compute_return_picking_count',
        string="Nombre de retours",
    )

    @api.depends('return_picking_ids')
    def _compute_return_picking_count(self):
        for rec in self:
            rec.return_picking_count = len(rec.return_picking_ids)

    # ================== SMART BUTTON ==================

    def action_view_return_pickings(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'name': _("Retours de stock"),
        }
        if len(self.return_picking_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.return_picking_ids.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.return_picking_ids.ids)],
            })
        return action

    # ================== ANNULATION PICKING ==================

    def _create_return_picking(self, picking):
        """Crée un picking de retour pour un picking done et le valide.

        Returns:
            stock.picking: le retour créé, ou False si rien à faire
        """
        if not picking or picking.state != 'done':
            return self.env['stock.picking']

        done_moves = picking.move_ids.filtered(lambda m: m.state == 'done')
        if not done_moves:
            return self.env['stock.picking']

        return_type = picking.picking_type_id.return_picking_type_id or picking.picking_type_id
        return_picking = self.env['stock.picking'].create({
            'picking_type_id': return_type.id,
            'partner_id': picking.partner_id.id,
            'location_id': picking.location_dest_id.id,
            'location_dest_id': picking.location_id.id,
            'origin': _("Retour de %s") % picking.name,
        })

        for move in done_moves:
            self.env['stock.move'].create({
                'name': _("Retour de %s") % move.product_id.display_name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'picking_id': return_picking.id,
                'location_id': move.location_dest_id.id,
                'location_dest_id': move.location_id.id,
                'origin_returned_move_id': move.id,
                'picking_type_id': return_type.id,
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            })

        return_picking.action_confirm()
        return_picking.action_assign()

        if return_picking.state == 'assigned':
            for move in return_picking.move_ids:
                move.quantity = move.product_uom_qty
            try:
                with self.env.cr.savepoint():
                    return_picking.button_validate()
            except Exception as e:
                _logger.warning(
                    "Retour %s créé mais validation impossible: %s. "
                    "À valider manuellement.",
                    return_picking.name, str(e)
                )
                return_picking.invalidate_recordset()

        return return_picking

    def _cancel_or_return_picking(self, picking):
        """Annule un picking (draft/confirmed/assigned) ou crée un retour (done).

        Returns:
            stock.picking: le retour créé si done, sinon empty recordset
        """
        if not picking or picking.state == 'cancel':
            return self.env['stock.picking']

        if picking.state == 'done':
            return self._create_return_picking(picking)

        picking.action_cancel()
        _logger.info("Picking annulé: %s", picking.name)
        return self.env['stock.picking']

    # ================== ANNULATION FACTURE ==================

    def _cancel_invoice(self, invoice):
        """Annule une facture ou crée un avoir."""
        if not invoice or invoice.state == 'cancel':
            return

        if invoice.payment_state in ('in_payment', 'paid'):
            raise UserError(_(
                "La facture %s est payée. "
                "Annulez le paiement avant de remettre en brouillon."
            ) % invoice.name)

        if invoice.state == 'posted':
            try:
                reversal_wizard = self.env['account.move.reversal'].with_context(
                    active_model='account.move',
                    active_ids=invoice.ids,
                ).create({
                    'reason': _("Remise en brouillon %s") % self.name,
                    'journal_id': invoice.journal_id.id,
                })
                result = reversal_wizard.reverse_moves()
                if result and result.get('res_id'):
                    credit_note = self.env['account.move'].browse(result['res_id'])
                    credit_note.action_post()
                    _logger.info("Avoir créé: %s pour %s", credit_note.name, invoice.name)
                elif result and result.get('domain'):
                    for cn in self.env['account.move'].search(result['domain']):
                        if cn.state == 'draft':
                            cn.action_post()
                    _logger.info("Avoirs créés pour %s", invoice.name)
            except UserError:
                raise
            except Exception as e:
                raise UserError(_(
                    "Impossible de créer l'avoir pour %s.\n"
                    "Vérifiez la période comptable.\nErreur: %s"
                ) % (invoice.name, str(e)))

        elif invoice.state == 'draft':
            invoice.button_cancel()
            _logger.info("Facture annulée: %s", invoice.name)

    # ================== ANNULATION ACHAT ==================

    def _cancel_purchase(self, purchase):
        """Annule un achat et ses documents liés.

        Ordre: factures → réceptions → achat
        """
        if not purchase or purchase.state == 'cancel':
            return self.env['stock.picking']

        return_pickings = self.env['stock.picking']

        # 1. Factures
        for invoice in purchase.invoice_ids.filtered(lambda i: i.state != 'cancel'):
            self._cancel_invoice(invoice)

        # 2. Réceptions
        for picking in purchase.picking_ids.filtered(lambda p: p.state != 'cancel'):
            ret = self._cancel_or_return_picking(picking)
            return_pickings |= ret

        # 3. Achat
        has_done_pickings = any(p.state == 'done' for p in purchase.picking_ids)
        if has_done_pickings:
            _logger.info(
                "Achat %s non annulé (réceptions done). Retours créés.",
                purchase.name
            )
        else:
            if purchase.state == 'done':
                purchase.button_unlock()
            if purchase.state in ('draft', 'sent', 'purchase'):
                purchase.button_cancel()
                _logger.info("Achat annulé: %s", purchase.name)

        return return_pickings

    # ================== ACTION PRINCIPALE ==================

    def action_reset_draft(self):
        """Remet la production en brouillon en annulant tous les documents."""
        self.ensure_one()

        if self.state == 'draft':
            raise UserError(_("La production est déjà en brouillon."))

        # Vérifier les factures payées avant toute action
        self._check_paid_invoices()

        return_pickings = self.env['stock.picking']
        cancelled_docs = []

        if self.state in ('validated', 'done'):
            # Annuler les BL de consommation et emballage
            for picking_field in ('picking_consumption_id', 'picking_packaging_id'):
                picking = getattr(self, picking_field)
                if picking:
                    ret = self._cancel_or_return_picking(picking)
                    return_pickings |= ret
                    cancelled_docs.append(picking.name)

            # Annuler les achats et leurs documents
            for po_field in ('purchase_finished_id', 'purchase_scrap_id', 'purchase_paste_id'):
                purchase = getattr(self, po_field)
                if purchase:
                    ret = self._cancel_purchase(purchase)
                    return_pickings |= ret
                    cancelled_docs.append(purchase.name)

        # Enregistrer les retours
        if return_pickings:
            self.write({'return_picking_ids': [(4, p.id) for p in return_pickings]})

        # Effacer les liens vers les documents
        self.write({
            'state': 'draft',
            'picking_consumption_id': False,
            'picking_packaging_id': False,
            'purchase_finished_id': False,
            'purchase_scrap_id': False,
            'purchase_paste_id': False,
        })

        # Message dans le chatter
        body = _("Production remise en brouillon.")
        if cancelled_docs:
            body += _("<br/><b>Documents annulés :</b> %s") % ', '.join(cancelled_docs)
        if return_pickings:
            ret_names = ', '.join(return_pickings.mapped('name'))
            body += _("<br/><b>Retours créés :</b> %s") % ret_names
        self.message_post(body=body)

        return True

    # ================== VÉRIFICATIONS ==================

    def _check_paid_invoices(self):
        """Vérifie qu'aucune facture liée n'est payée."""
        self.ensure_one()
        purchases = self.env['purchase.order']
        for field in ('purchase_finished_id', 'purchase_scrap_id', 'purchase_paste_id'):
            po = getattr(self, field)
            if po:
                purchases |= po

        for invoice in purchases.mapped('invoice_ids'):
            if invoice.payment_state in ('in_payment', 'paid'):
                raise UserError(_(
                    "Impossible : la facture %s est payée.\n"
                    "Annulez d'abord le paiement."
                ) % invoice.name)

    # ================== PROTECTION SUPPRESSION ==================

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Impossible de supprimer '%s' (état: %s).\n"
                    "Remettez la production en brouillon d'abord."
                ) % (rec.name, dict(rec._fields['state'].selection).get(rec.state, rec.state)))
        return super().unlink()
