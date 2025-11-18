# -*- coding: utf-8 -*-
from odoo import models, api, fields
import time


class GecafleReceptionRealtime(models.Model):
    _inherit = 'gecafle.reception'

    @api.model
    def create(self, vals):
        """Override create pour marquer qu'une réception a changé"""
        reception = super(GecafleReceptionRealtime, self).create(vals)
        self._mark_reception_changed()
        return reception

    def write(self, vals):
        """Override write pour marquer qu'une réception a changé"""
        result = super(GecafleReceptionRealtime, self).write(vals)
        self._mark_reception_changed()
        return result

    def unlink(self):
        """Override unlink pour marquer qu'une réception a changé"""
        result = super(GecafleReceptionRealtime, self).unlink()
        self._mark_reception_changed()
        return result

    def _mark_reception_changed(self):
        """
        Marque qu'une réception a changé en mettant à jour un paramètre système
        Cette approche simple évite les complications du bus
        """
        # Mettre à jour un paramètre système avec le timestamp actuel
        timestamp = str(time.time())
        self.env['ir.config_parameter'].sudo().set_param('gecafle.reception.last_change', timestamp)

        # Invalider le cache pour forcer le recalcul
        self.invalidate_model()
        if 'gecafle.details_ventes' in self.env:
            self.env['gecafle.details_ventes'].invalidate_model()
        if 'gecafle.vente' in self.env:
            self.env['gecafle.vente'].invalidate_model()

    @api.model
    def get_last_change_timestamp(self):
        """
        Retourne le timestamp de la dernière modification de réception
        Utilisé par le JavaScript pour vérifier s'il faut rafraîchir
        """
        return self.env['ir.config_parameter'].sudo().get_param('gecafle.reception.last_change', '0')


class GecafleDetailsReceptionRealtime(models.Model):
    _inherit = 'gecafle.details_reception'

    def create(self, vals):
        """Marquer le changement lors de l'ajout d'une ligne de réception"""
        ligne = super(GecafleDetailsReceptionRealtime, self).create(vals)
        if ligne.reception_id:
            ligne.reception_id._mark_reception_changed()
        return ligne

    def write(self, vals):
        """Marquer le changement lors de la modification d'une ligne de réception"""
        result = super(GecafleDetailsReceptionRealtime, self).write(vals)
        for ligne in self:
            if ligne.reception_id:
                ligne.reception_id._mark_reception_changed()
        return result

    def unlink(self):
        """Marquer le changement lors de la suppression d'une ligne de réception"""
        reception_ids = self.mapped('reception_id')
        result = super(GecafleDetailsReceptionRealtime, self).unlink()
        for reception in reception_ids:
            if reception.exists():
                reception._mark_reception_changed()
        return result
