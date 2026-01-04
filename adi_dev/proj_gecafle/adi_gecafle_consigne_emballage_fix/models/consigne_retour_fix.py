# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GecafleConsigneRetourFix(models.Model):
    """
    Correction de la préparation des lignes de retour de consigne
    pour utiliser le champ est_consigne au lieu de emballage_id.non_returnable.

    Avant ce fix:
    - _prepare_lines_from_vente() utilisait emballage_id.non_returnable
    - Les emballages forcés en NR sur la ligne de vente étaient quand même
      proposés pour retour

    Après ce fix:
    - Utilise le champ est_consigne des lignes d'emballage
    - Seuls les emballages réellement consignés (R) sont proposés pour retour
    """
    _inherit = 'gecafle.consigne.retour'

    def _prepare_lines_from_vente(self, vente):
        """
        Override pour utiliser est_consigne au lieu de non_returnable.

        Ne propose que les emballages où est_consigne = True.
        """
        lines = []

        if not vente or not vente.consigne_appliquee:
            return lines

        # Créer les lignes à partir des emballages de la vente
        # CORRECTION: Utiliser est_consigne au lieu de non_returnable
        for emb in vente.detail_emballage_vente_ids:
            # Vérifier que l'emballage est consigné (R) et qu'il y a des quantités
            if emb.qte_sortantes > 0 and emb.est_consigne:
                line_vals = {
                    'emballage_id': emb.emballage_id.id,
                    'qte_consignee': emb.qte_sortantes,
                    'qte_retournee': emb.qte_sortantes,
                    'prix_unitaire': emb.emballage_id.price_unit,
                }
                lines.append((0, 0, line_vals))

        return lines

    @api.onchange('vente_id')
    def _onchange_vente_id(self):
        """
        Override pour utiliser la nouvelle logique de préparation des lignes.
        """
        # Nettoyer les lignes existantes
        self.retour_line_ids = [(5, 0, 0)]

        if not self.vente_id:
            return

        # Mettre à jour le client
        self.client_id = self.vente_id.client_id

        # Vérifier si la vente a des consignes appliquées
        if not self.vente_id.consigne_appliquee:
            return {
                'warning': {
                    'title': _('Attention'),
                    'message': _('Cette vente n\'a pas de consigne appliquée.')
                }
            }

        # Vérifier s'il y a des emballages consignés
        emballages_consignes = self.vente_id.detail_emballage_vente_ids.filtered(
            lambda l: l.est_consigne and l.qte_sortantes > 0
        )

        if not emballages_consignes:
            return {
                'warning': {
                    'title': _('Information'),
                    'message': _('Aucun emballage consigné (R) trouvé pour cette vente.\n'
                                 'Tous les emballages sont marqués comme Non Rendu (NR).')
                }
            }

        # Créer les lignes temporaires pour l'affichage
        lines = self._prepare_lines_from_vente(self.vente_id)
        if lines:
            self.retour_line_ids = lines
