# -*- coding: utf-8 -*-
from odoo import models, api, fields
import time
import logging

_logger = logging.getLogger(__name__)


class GecafleReceptionRealtime(models.Model):
    """
    Extension du modèle gecafle.reception pour la synchronisation temps réel.

    Fonctionnalités:
    - Marque automatiquement les changements via timestamp
    - Override name_search pour retourner uniquement les réceptions avec stock disponible
    - Invalide les caches pour forcer le rechargement des données
    """
    _inherit = 'gecafle.reception'

    @api.model
    def create(self, vals):
        """Override create pour marquer qu'une réception a changé"""
        reception = super(GecafleReceptionRealtime, self).create(vals)
        self._mark_reception_changed()
        _logger.info(f"[GeCaFle Realtime] Réception créée: {reception.name}")
        return reception

    def write(self, vals):
        """Override write pour marquer qu'une réception a changé"""
        result = super(GecafleReceptionRealtime, self).write(vals)
        self._mark_reception_changed()
        return result

    def unlink(self):
        """Override unlink pour marquer qu'une réception a changé"""
        names = self.mapped('name')
        result = super(GecafleReceptionRealtime, self).unlink()
        self._mark_reception_changed()
        _logger.info(f"[GeCaFle Realtime] Réceptions supprimées: {names}")
        return result

    def _mark_reception_changed(self):
        """
        Marque qu'une réception a changé en mettant à jour un paramètre système.
        Cette méthode est appelée après chaque create/write/unlink.
        """
        # Mettre à jour un paramètre système avec le timestamp actuel
        timestamp = str(time.time())
        self.env['ir.config_parameter'].sudo().set_param(
            'gecafle.reception.last_change',
            timestamp
        )

        # Invalider tous les caches des modèles concernés
        self.invalidate_model()

        # Invalider aussi les modèles liés
        models_to_invalidate = [
            'gecafle.details_reception',
            'gecafle.details_ventes',
            'gecafle.vente',
        ]

        for model_name in models_to_invalidate:
            if model_name in self.env:
                try:
                    self.env[model_name].invalidate_model()
                except Exception as e:
                    _logger.warning(f"[GeCaFle Realtime] Impossible d'invalider {model_name}: {e}")

    @api.model
    def get_last_change_timestamp(self):
        """
        Retourne le timestamp de la dernière modification de réception.
        Utilisé par le JavaScript pour vérifier s'il faut rafraîchir.
        """
        return self.env['ir.config_parameter'].sudo().get_param(
            'gecafle.reception.last_change',
            '0'
        )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search pour filtrer automatiquement les réceptions
        qui ont du stock disponible.

        Cette approche remplace le domaine lambda qui n'était évalué qu'une fois.
        Chaque appel à name_search recalcule les réceptions disponibles.
        """
        args = args or []

        # Rechercher les réceptions qui ont des lignes avec stock disponible
        # Utilisation de SQL pour performance et données fraîches
        self.env.cr.execute("""
            SELECT DISTINCT dr.reception_id
            FROM gecafle_details_reception dr
            WHERE dr.qte_colis_disponibles > 0
              AND dr.reception_id IS NOT NULL
        """)
        reception_ids_with_stock = [row[0] for row in self.env.cr.fetchall()]

        # Construire le domaine de base
        base_domain = [
            ('state', 'in', ['brouillon', 'confirmee']),
            ('id', 'in', reception_ids_with_stock) if reception_ids_with_stock else ('id', '=', False),
        ]

        # Ajouter le filtre de recherche par nom
        if name:
            search_domain = ['|', '|',
                ('name', operator, name),
                ('producteur_id.name', operator, name),
                ('display_name', operator, name)
            ]
            domain = search_domain + base_domain
        else:
            domain = base_domain

        # Combiner avec les args existants
        domain = domain + args

        # Rechercher et retourner
        recs = self.search(domain, limit=limit)
        return recs.name_get()

    @api.model
    def search_read_realtime(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Méthode de recherche en temps réel qui invalide le cache avant la recherche.
        Utilisée par le widget JavaScript pour garantir des données fraîches.
        """
        # Invalider le cache avant la recherche
        self.invalidate_model()

        # Effectuer la recherche
        return self.search_read(domain or [], fields, offset, limit, order)


class GecafleDetailsReceptionRealtime(models.Model):
    """
    Extension du modèle gecafle.details_reception pour la synchronisation temps réel.
    Marque les changements quand une ligne de réception est modifiée.
    """
    _inherit = 'gecafle.details_reception'

    @api.model_create_multi
    def create(self, vals_list):
        """Marquer le changement lors de l'ajout d'une ligne de réception"""
        lignes = super(GecafleDetailsReceptionRealtime, self).create(vals_list)
        for ligne in lignes:
            if ligne.reception_id:
                ligne.reception_id._mark_reception_changed()
        return lignes

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

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search pour retourner des données fraîches.
        Invalide le cache avant chaque recherche.
        """
        # Invalider le cache pour avoir des données fraîches
        self.invalidate_model()

        args = args or []
        domain = []

        if name:
            # Recherche dans plusieurs champs liés
            domain = ['|', '|', '|',
                ('designation_id.name', operator, name),
                ('qualite_id.name', operator, name),
                ('type_colis_id.name', operator, name),
                ('display_name', operator, name)
            ]

        # Combiner avec les arguments existants
        records = self.search(domain + args, limit=limit)
        return records.name_get()
