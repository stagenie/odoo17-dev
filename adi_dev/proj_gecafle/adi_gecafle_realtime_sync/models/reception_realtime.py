# -*- coding: utf-8 -*-
from odoo import models, api, fields
import json


class GecafleReceptionRealtime(models.Model):
    _inherit = 'gecafle.reception'

    @api.model
    def create(self, vals):
        """Override create pour envoyer une notification lors de la création d'une réception"""
        reception = super(GecafleReceptionRealtime, self).create(vals)
        self._notify_reception_change('create', reception)
        return reception

    def write(self, vals):
        """Override write pour envoyer une notification lors de la modification d'une réception"""
        result = super(GecafleReceptionRealtime, self).write(vals)
        for reception in self:
            self._notify_reception_change('update', reception)
        return result

    def unlink(self):
        """Override unlink pour envoyer une notification lors de la suppression d'une réception"""
        reception_ids = self.ids
        result = super(GecafleReceptionRealtime, self).unlink()
        self._notify_reception_change('delete', reception_ids=reception_ids)
        return result

    def _notify_reception_change(self, operation, reception=None, reception_ids=None):
        """
        Envoie une notification via le bus Odoo pour informer les ventes
        
        :param operation: Type d'opération ('create', 'update', 'delete')
        :param reception: Enregistrement de réception (pour create/update)
        :param reception_ids: Liste d'IDs (pour delete)
        """
        channel_name = 'gecafle_reception_sync'
        
        # Préparer le message
        if operation in ['create', 'update']:
            message = {
                'operation': operation,
                'reception_id': reception.id,
                'reception_name': reception.name if hasattr(reception, 'name') else None,
                'producteur_id': reception.producteur_id.id if reception.producteur_id else None,
                'producteur_name': reception.producteur_id.name if reception.producteur_id else None,
                'reception_date': fields.Datetime.to_string(reception.reception_date) if hasattr(reception, 'reception_date') else None,
                'state': reception.state if hasattr(reception, 'state') else None,
                'timestamp': fields.Datetime.now().isoformat(),
            }
        else:  # delete
            message = {
                'operation': 'delete',
                'reception_ids': reception_ids,
                'timestamp': fields.Datetime.now().isoformat(),
            }
        
        # Envoyer la notification à tous les utilisateurs via le bus
        self.env['bus.bus']._sendone(
            channel_name,
            'gecafle.reception.change',
            message
        )
        
        # IMPORTANT: Invalider le cache pour forcer le recalcul des domaines
        # Cela permet aux vues ouvertes de voir les nouvelles réceptions
        self.env['gecafle.details_ventes'].invalidate_model()
        self.env['gecafle.reception'].invalidate_model()


class GecafleDetailsReceptionRealtime(models.Model):
    _inherit = 'gecafle.details_reception'

    def create(self, vals):
        """Notification lors de l'ajout d'une ligne de réception (gecafle.details_reception)"""
        ligne = super(GecafleDetailsReceptionRealtime, self).create(vals)
        if ligne.reception_id:
            ligne.reception_id._notify_reception_change('update', ligne.reception_id)
        return ligne

    def write(self, vals):
        """Notification lors de la modification d'une ligne de réception (gecafle.details_reception)"""
        result = super(GecafleDetailsReceptionRealtime, self).write(vals)
        for ligne in self:
            if ligne.reception_id:
                ligne.reception_id._notify_reception_change('update', ligne.reception_id)
        return result

    def unlink(self):
        """Notification lors de la suppression d'une ligne de réception (gecafle.details_reception)"""
        reception_ids = self.mapped('reception_id')
        result = super(GecafleDetailsReceptionRealtime, self).unlink()
        for reception in reception_ids:
            if reception.exists():
                reception._notify_reception_change('update', reception)
        return result
