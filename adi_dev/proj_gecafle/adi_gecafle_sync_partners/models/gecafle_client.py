# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleClient(models.Model):
    _inherit = 'gecafle.client'

    # Lien vers res.partner
    res_partner_id = fields.Many2one(
        'res.partner',
        string="Contact Odoo",
        readonly=True,
        ondelete='restrict'
    )

    active = fields.Boolean(
        string="Actif",
        default=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Création avec synchronisation automatique vers res.partner"""
        clients = super().create(vals_list)

        for client in clients:
            # Ne pas synchroniser si déjà en cours
            if self.env.context.get('sync_in_progress'):
                continue

            client._create_res_partner()

        return clients

    def _create_res_partner(self):
        """Crée le res.partner correspondant"""
        self.ensure_one()

        if self.res_partner_id:
            return self.res_partner_id

        # Vérifier les doublons
        existing = self.env['res.partner'].search([
            ('name', '=', self.name),
            '|', ('active', '=', True), ('active', '=', False)
        ], limit=1)

        if existing:
            if not existing.active:
                existing.active = True
            self.res_partner_id = existing
            existing.gecafle_client_id = self
            existing.is_gecafle_synced = True
            return existing

        # Créer le partner
        partner_vals = {
            'name': self.name,
            'phone': self.tel_mob,
            'street': self.adresse,
            'customer_rank': 1,
            'is_company': False,
            'lang': self._get_odoo_language(),
            'gecafle_client_id': self.id,
            'is_gecafle_synced': True,
            'sync_source': 'gecafle',
            'trust': 'good' if self.est_fidel else 'normal',
        }

        partner = self.env['res.partner'].with_context(
            sync_in_progress=True
        ).create(partner_vals)

        self.res_partner_id = partner

        _logger.info(f"Partner créé depuis client GECAFLE : {partner.name}")
        return partner

    def _get_odoo_language(self):
        """Convertit la langue GECAFLE en langue Odoo"""
        lang_mapping = {
            'fr': 'fr_FR',
            'ar': 'ar_DZ',
        }
        return lang_mapping.get(self.langue_client, 'fr_FR')

    def write(self, vals):
        """Synchronise les modifications vers res.partner"""
        res = super().write(vals)

        if not self.env.context.get('sync_in_progress'):
            for client in self:
                if client.res_partner_id:
                    client._sync_res_partner(vals)

        return res

    def _sync_res_partner(self, vals):
        """Synchronise les modifications vers res.partner"""
        self.ensure_one()
        if not self.res_partner_id:
            return

        partner_vals = {}

        if 'name' in vals:
            partner_vals['name'] = vals['name']

        if 'tel_mob' in vals:
            partner_vals['phone'] = vals['tel_mob']

        if 'adresse' in vals:
            partner_vals['street'] = vals['adresse']

        if 'langue_client' in vals:
            partner_vals['lang'] = self._get_odoo_language()

        if 'est_fidel' in vals:
            partner_vals['trust'] = 'good' if vals['est_fidel'] else 'normal'

        if partner_vals:
            self.res_partner_id.with_context(sync_in_progress=True).write(partner_vals)
            _logger.info(f"Partner synchronisé depuis GECAFLE : {self.res_partner_id.name}")

    def unlink(self):
        """Empêche la suppression, archive à la place"""
        for client in self:
            if client.res_partner_id:
                raise UserError(_(
                    "Impossible de supprimer %s car il est lié à un contact Odoo.\n"
                    "Utilisez l'archivage à la place."
                ) % client.name)
        return super().unlink()

    def toggle_active(self):
        """Archive/Désarchive avec synchronisation"""
        for client in self:
            client.active = not client.active
            if client.res_partner_id and not self.env.context.get('sync_in_progress'):
                client.res_partner_id.with_context(
                    sync_in_progress=True
                ).active = client.active

    def action_open_res_partner(self):
        """Ouvre le formulaire du partner Odoo lié"""
        self.ensure_one()
        if not self.res_partner_id:
            raise UserError(_("Aucun contact Odoo n'est lié à ce client."))

        return {
            'name': _('Contact Odoo'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'res_id': self.res_partner_id.id,
            'target': 'current',
        }

    def action_view_partner_ledger(self):
        """Ouvre le wizard du Partner Ledger pour le partenaire lié"""
        self.ensure_one()
        if not self.res_partner_id:
            raise UserError(_("Aucun contact Odoo n'est lié à ce client."))

        return {
            'name': _('Partner Ledger'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.report.partner.ledger',
            'view_id': self.env.ref('accounting_pdf_reports.account_report_partner_ledger_view').id,
            'target': 'new',
            'context': {
                'default_partner_ids': [(6, 0, [self.res_partner_id.id])],
                'default_target_move': 'posted',
                'default_result_selection': 'customer',
                'default_reconciled': True,
                'hide_partner': True,
            }
        }
