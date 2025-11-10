# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Liens vers GECAFLE
    gecafle_client_id = fields.Many2one(
        'gecafle.client',
        string="Client GECAFLE",
        readonly=True,
        ondelete='restrict'
    )

    gecafle_producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur GECAFLE",
        readonly=True,
        ondelete='restrict'
    )

    is_gecafle_synced = fields.Boolean(
        string="Synchronisé GECAFLE",
        default=False,
        help="Indique si ce contact est synchronisé avec GECAFLE"
    )

    sync_source = fields.Selection([
        ('odoo', 'Créé dans Odoo'),
        ('gecafle', 'Créé dans GECAFLE'),
    ], string="Source", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Création avec synchronisation automatique"""
        partners = super().create(vals_list)

        for partner in partners:
            # Ne pas synchroniser si déjà en cours de sync
            if self.env.context.get('sync_in_progress'):
                continue

            # Synchroniser selon le type
            if partner.customer_rank > 0:
                partner._create_gecafle_client()

            if partner.supplier_rank > 0:
                partner._create_gecafle_producteur()

        return partners

    def _create_gecafle_client(self):
        """Crée le client GECAFLE correspondant"""
        self.ensure_one()

        if self.gecafle_client_id:
            return self.gecafle_client_id

        # Vérifier les doublons
        existing = self.env['gecafle.client'].search([
            ('name', '=', self.name),
            '|', ('active', '=', True), ('active', '=', False)
        ], limit=1)

        if existing:
            if not existing.active:
                existing.active = True
            self.gecafle_client_id = existing
            self.is_gecafle_synced = True
            return existing

        # Créer le client GECAFLE
        client_vals = {
            'name': self.name,
            'tel_mob': self.phone or self.mobile or '',
            'adresse': self._get_full_address(),
            'langue_client': self._get_gecafle_language(),
            'est_fidel': self.trust == 'good',  # Basé sur la confiance
            'res_partner_id': self.id,
        }

        client = self.env['gecafle.client'].with_context(
            sync_in_progress=True
        ).create(client_vals)

        self.gecafle_client_id = client
        self.is_gecafle_synced = True
        self.sync_source = 'odoo'

        _logger.info(f"Client GECAFLE créé : {client.name}")
        return client

    def _create_gecafle_producteur(self):
        """Crée le producteur GECAFLE correspondant"""
        self.ensure_one()

        if self.gecafle_producteur_id:
            return self.gecafle_producteur_id

        # Vérifier les doublons
        existing = self.env['gecafle.producteur'].search([
            ('name', '=', self.name),
            '|', ('active', '=', True), ('active', '=', False)
        ], limit=1)

        if existing:
            if not existing.active:
                existing.active = True
            self.gecafle_producteur_id = existing
            self.is_gecafle_synced = True
            return existing

        # Créer le producteur GECAFLE
        producteur_vals = {
            'name': self.name,
            'phone': self.phone or self.mobile or '',
            'address': self._get_full_address(),
            'language': self._get_gecafle_producteur_language(),
            'res_partner_id': self.id,
            'initial_balance': 0.0,
        }

        producteur = self.env['gecafle.producteur'].with_context(
            sync_in_progress=True
        ).create(producteur_vals)

        self.gecafle_producteur_id = producteur
        self.is_gecafle_synced = True
        self.sync_source = 'odoo'

        _logger.info(f"Producteur GECAFLE créé : {producteur.name}")
        return producteur

    def _get_full_address(self):
        """Construit l'adresse complète"""
        address_parts = []
        if self.street:
            address_parts.append(self.street)
        if self.street2:
            address_parts.append(self.street2)
        if self.zip:
            address_parts.append(self.zip)
        if self.city:
            address_parts.append(self.city)
        if self.state_id:
            address_parts.append(self.state_id.name)
        if self.country_id:
            address_parts.append(self.country_id.name)

        return ', '.join(address_parts)

    def _get_gecafle_language(self):
        """Convertit la langue Odoo en langue GECAFLE client"""
        lang_mapping = {
            'fr_FR': 'fr',
            'ar_DZ': 'ar',
            'ar_SA': 'ar',
        }
        return lang_mapping.get(self.lang, 'fr')

    def _get_gecafle_producteur_language(self):
        """Convertit la langue Odoo en langue GECAFLE producteur"""
        lang_mapping = {
            'fr_FR': 'fr_FR',
            'ar_DZ': 'ar_DZ',
            'ar_SA': 'ar_DZ',
        }
        return lang_mapping.get(self.lang, 'fr_FR')

    def write(self, vals):
        """Synchronise les modifications"""
        res = super().write(vals)

        # Synchroniser si nécessaire
        if not self.env.context.get('sync_in_progress'):
            for partner in self:
                # Synchroniser le client GECAFLE
                if partner.gecafle_client_id and any(f in vals for f in ['name', 'phone', 'mobile', 'street', 'city']):
                    partner._sync_gecafle_client(vals)

                # Synchroniser le producteur GECAFLE
                if partner.gecafle_producteur_id and any(
                        f in vals for f in ['name', 'phone', 'mobile', 'street', 'city']):
                    partner._sync_gecafle_producteur(vals)

                # Créer si nouveau type
                if 'customer_rank' in vals and vals['customer_rank'] > 0 and not partner.gecafle_client_id:
                    partner._create_gecafle_client()

                if 'supplier_rank' in vals and vals['supplier_rank'] > 0 and not partner.gecafle_producteur_id:
                    partner._create_gecafle_producteur()

        return res

    def _sync_gecafle_client(self, vals):
        """Synchronise les modifications vers le client GECAFLE"""
        self.ensure_one()
        if not self.gecafle_client_id:
            return

        client_vals = {}

        if 'name' in vals:
            client_vals['name'] = vals['name']

        if 'phone' in vals or 'mobile' in vals:
            client_vals['tel_mob'] = vals.get('phone') or vals.get('mobile') or self.phone or self.mobile

        if any(f in vals for f in ['street', 'street2', 'zip', 'city']):
            client_vals['adresse'] = self._get_full_address()

        if client_vals:
            self.gecafle_client_id.with_context(sync_in_progress=True).write(client_vals)
            _logger.info(f"Client GECAFLE synchronisé : {self.gecafle_client_id.name}")

    def _sync_gecafle_producteur(self, vals):
        """Synchronise les modifications vers le producteur GECAFLE"""
        self.ensure_one()
        if not self.gecafle_producteur_id:
            return

        producteur_vals = {}

        if 'name' in vals:
            producteur_vals['name'] = vals['name']

        if 'phone' in vals or 'mobile' in vals:
            producteur_vals['phone'] = vals.get('phone') or vals.get('mobile') or self.phone or self.mobile

        if any(f in vals for f in ['street', 'street2', 'zip', 'city']):
            producteur_vals['address'] = self._get_full_address()

        if producteur_vals:
            self.gecafle_producteur_id.with_context(sync_in_progress=True).write(producteur_vals)
            _logger.info(f"Producteur GECAFLE synchronisé : {self.gecafle_producteur_id.name}")

    def unlink(self):
        """Empêche la suppression, archive à la place"""
        for partner in self:
            if partner.gecafle_client_id or partner.gecafle_producteur_id:
                raise UserError(_(
                    "Impossible de supprimer %s car il est lié à GECAFLE.\n"
                    "Utilisez l'archivage à la place."
                ) % partner.name)
        return super().unlink()

    def toggle_active(self):
        """Archive/Désarchive avec synchronisation"""
        res = super().toggle_active()

        if not self.env.context.get('sync_in_progress'):
            for partner in self:
                # Synchroniser l'archivage
                if partner.gecafle_client_id:
                    partner.gecafle_client_id.with_context(
                        sync_in_progress=True
                    ).active = partner.active

                if partner.gecafle_producteur_id:
                    partner.gecafle_producteur_id.with_context(
                        sync_in_progress=True
                    ).active = partner.active

        return res

    def action_open_gecafle_client(self):
        """Ouvre le formulaire du client GECAFLE lié"""
        self.ensure_one()
        if not self.gecafle_client_id:
            raise UserError(_("Aucun client GECAFLE n'est lié à ce contact."))

        return {
            'name': _('Client GECAFLE'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.client',
            'res_id': self.gecafle_client_id.id,
            'target': 'current',
        }

    def action_open_gecafle_producteur(self):
        """Ouvre le formulaire du producteur GECAFLE lié"""
        self.ensure_one()
        if not self.gecafle_producteur_id:
            raise UserError(_("Aucun producteur GECAFLE n'est lié à ce contact."))

        return {
            'name': _('Producteur GECAFLE'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.producteur',
            'res_id': self.gecafle_producteur_id.id,
            'target': 'current',
        }
