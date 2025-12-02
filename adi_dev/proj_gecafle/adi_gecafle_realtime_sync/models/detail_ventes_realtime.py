# -*- coding: utf-8 -*-
from odoo import models, fields, api


class GecafleDetailsVentesRealtime(models.Model):
    """
    Extension du modèle gecafle.details_ventes pour la synchronisation temps réel.

    Cette extension simplifie le domaine du champ reception_id pour éviter
    le problème du domaine lambda qui n'est évalué qu'une seule fois.

    Le filtrage des réceptions avec stock disponible est maintenant géré
    directement dans la méthode name_search de gecafle.reception.
    """
    _inherit = 'gecafle.details_ventes'

    # Redéfinir le champ avec un domaine statique simple
    # Le filtrage dynamique est géré par name_search dans reception_realtime.py
    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True,
        domain="[('state', 'in', ['brouillon', 'confirmee'])]"
    )
