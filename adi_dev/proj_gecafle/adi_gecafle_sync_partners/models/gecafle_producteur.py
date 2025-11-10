# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleProducteur(models.Model):
    _inherit = 'gecafle.producteur'

    # Lien vers res.partner
    res_partner_id = fields.Many2one(
        'res.partner',
        string="Fournisseur Odoo",
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
        producteurs = super().create(vals_list)

        for producteur in producteurs:
            # Ne pas synchroniser si déjà en cours
            if self.env.context.get('sync_in_progress'):
                continue

            producteur._create_res_partner()

        return producteurs

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
            existing.gecafle_producteur_id = self
            existing.is_gecafle_synced = True
            return existing

        # Créer le partner
        partner_vals = {
            'name': self.name,
            'phone': self.phone,
            'street': self.address,
            'supplier_rank': 1,
            'is_company': False,
            'lang': self.language,
            'gecafle_producteur_id': self.id,
            'is_gecafle_synced': True,
            'sync_source': 'gecafle',
        }

        partner = self.env['res.partner'].with_context(
            sync_in_progress=True
        ).create(partner_vals)

        self.res_partner_id = partner

        _logger.info(f"Partner créé depuis producteur GECAFLE : {partner.name}")
        return partner

    def write(self, vals):
        """Synchronise les modifications vers res.partner"""
        res = super().write(vals)

        if not self.env.context.get('sync_in_progress'):
            for producteur in self:
                if producteur.res_partner_id:
                    producteur._sync_res_partner(vals)

        return res

    def _sync_res_partner(self, vals):
        """Synchronise les modifications vers res.partner"""
        self.ensure_one()
        if not self.res_partner_id:
            return

        partner_vals = {}

        if 'name' in vals:
            partner_vals['name'] = vals['name']

        if 'phone' in vals:
            partner_vals['phone'] = vals['phone']

        if 'address' in vals:
            partner_vals['street'] = vals['address']

        if 'language' in vals:
            partner_vals['lang'] = vals['language']

        if partner_vals:
            self.res_partner_id.with_context(sync_in_progress=True).write(partner_vals)
            _logger.info(f"Partner synchronisé depuis producteur GECAFLE : {self.res_partner_id.name}")

    def unlink(self):
        """Empêche la suppression, archive à la place"""
        for producteur in self:
            if producteur.res_partner_id:
                raise UserError(_(
                    "Impossible de supprimer %s car il est lié à un fournisseur Odoo.\n"
                    "Utilisez l'archivage à la place."
                ) % producteur.name)
        return super().unlink()

    def toggle_active(self):
        """Archive/Désarchive avec synchronisation"""
        for producteur in self:
            producteur.active = not producteur.active
            if producteur.res_partner_id and not self.env.context.get('sync_in_progress'):
                producteur.res_partner_id.with_context(
                    sync_in_progress=True
                ).active = producteur.active

    def action_open_res_partner(self):
        """Ouvre le formulaire du partner Odoo lié"""
        self.ensure_one()
        if not self.res_partner_id:
            raise UserError(_("Aucun fournisseur Odoo n'est lié à ce producteur."))

        return {
            'name': _('Fournisseur Odoo'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'res_id': self.res_partner_id.id,
            'target': 'current',
        }
