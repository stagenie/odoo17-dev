# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GecafleDetailsEmballageVenteFix(models.Model):
    """
    Extension du modèle gecafle.details_emballage_vente pour ajouter
    le suivi du comportement R/NR (Rendu / Non Rendu).

    Avant ce fix, le modèle ne stockait que:
    - emballage_id, qte_sortantes, qte_entrantes

    Problème: Impossible de distinguer les emballages consignés des non consignés
    quand l'utilisateur force le comportement sur la ligne de vente.

    Solution: Ajouter le champ est_consigne pour refléter le choix utilisateur.
    """
    _inherit = 'gecafle.details_emballage_vente'

    # Nouveau champ pour stocker le comportement R/NR
    est_consigne = fields.Boolean(
        string="Consigné",
        default=False,
        help="Indique si cet emballage est consigné (Rendu) ou non (Non Rendu).\n"
             "- Consigné (R): Le client peut retourner l'emballage et être remboursé.\n"
             "- Non consigné (NR): L'emballage est vendu définitivement."
    )

    # Champ calculé pour affichage
    type_emballage_display = fields.Char(
        string="Type",
        compute='_compute_type_emballage_display',
        store=False,
        help="Affiche R (Rendu) ou NR (Non Rendu)"
    )

    @api.depends('est_consigne')
    def _compute_type_emballage_display(self):
        """Affiche R ou NR selon le statut de consigne"""
        for record in self:
            record.type_emballage_display = 'R' if record.est_consigne else 'NR'

    def name_get(self):
        """Override pour afficher le type R/NR dans le nom"""
        result = []
        for record in self:
            emballage_name = record.emballage_id.name or ''
            type_display = 'R' if record.est_consigne else 'NR'
            name = f"{emballage_name} ({type_display})"
            result.append((record.id, name))
        return result
