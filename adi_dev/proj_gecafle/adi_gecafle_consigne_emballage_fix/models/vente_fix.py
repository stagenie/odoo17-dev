# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GecafleVenteFix(models.Model):
    """
    Correction de la génération des lignes d'emballage pour propager
    le comportement R/NR depuis les lignes de vente.

    Avant ce fix:
    - Les emballages étaient regroupés uniquement par emballage_id
    - Le comportement R/NR forcé sur les lignes était ignoré

    Après ce fix:
    - Les emballages sont regroupés par (emballage_id + est_consigne)
    - Un même emballage peut avoir 2 lignes si certaines sont R et d'autres NR
    """
    _inherit = 'gecafle.vente'

    # Nouveau champ pour vérifier s'il y a des emballages consignés
    has_emballages_consignes = fields.Boolean(
        string="A des emballages consignés",
        compute='_compute_has_emballages_consignes',
        store=True,
        help="Indique si la vente contient au moins un emballage consigné (R)"
    )

    @api.depends('detail_emballage_vente_ids.est_consigne')
    def _compute_has_emballages_consignes(self):
        """Vérifie s'il y a au moins un emballage consigné dans la vente"""
        for vente in self:
            vente.has_emballages_consignes = any(
                emb.est_consigne for emb in vente.detail_emballage_vente_ids
            )

    def generate_emballage_lines(self):
        """
        Override pour regrouper les emballages par (emballage_id + est_consigne).

        Logique:
        1. Parcourir toutes les lignes de vente avec emballage
        2. Récupérer le champ est_consigne de chaque ligne
        3. Regrouper par (emballage_id, est_consigne)
        4. Créer les lignes d'emballage avec le bon statut
        """
        self.ensure_one()

        # Suppression des lignes existantes
        self.detail_emballage_vente_ids.unlink()

        # Dictionnaire pour regrouper les emballages
        # Clé: (emballage_id, est_consigne)
        emballage_dict = {}

        for line in self.detail_vente_ids:
            if line.type_colis_id and line.nombre_colis > 0:
                emballage_id = line.type_colis_id.id

                # Récupérer le statut consigné depuis la ligne de vente
                # Le champ est_consigne est calculé dans adi_gecafle_vente_emballage_custom
                est_consigne = line.est_consigne if hasattr(line, 'est_consigne') else False

                # Clé de regroupement
                key = (emballage_id, est_consigne)

                if key not in emballage_dict:
                    emballage_dict[key] = {
                        'sortantes': 0,
                        'entrantes': 0,
                        'est_consigne': est_consigne,
                    }

                # Accumuler les quantités
                emballage_dict[key]['sortantes'] += line.nombre_colis

        # Créer les lignes d'emballage
        for (emballage_id, est_consigne), data in emballage_dict.items():
            self.env['gecafle.details_emballage_vente'].create({
                'vente_id': self.id,
                'emballage_id': emballage_id,
                'qte_sortantes': data['sortantes'],
                'qte_entrantes': data.get('entrantes', 0),
                'est_consigne': data['est_consigne'],
            })

        return True

    @api.depends('detail_vente_ids.est_consigne',
                 'detail_vente_ids.nombre_colis',
                 'detail_vente_ids.type_colis_id')
    def _compute_etat_consigne(self):
        """
        Override du calcul de l'état de consigne pour utiliser
        le champ est_consigne des lignes d'emballage au lieu de
        emballage_id.non_returnable.
        """
        for vente in self:
            if not vente.consigne_appliquee:
                vente.etat_consigne = False
                continue

            # Vérifier les retours validés
            retours_valides = vente.consigne_retour_ids.filtered(
                lambda r: r.state in ['valide', 'avoir_cree']
            )

            if not retours_valides:
                # Vérifier s'il y a des emballages consignés
                has_consigne = any(
                    emb.est_consigne for emb in vente.detail_emballage_vente_ids
                )
                if has_consigne:
                    vente.etat_consigne = 'non_rendu'
                else:
                    # Pas d'emballages consignés, pas de suivi nécessaire
                    vente.etat_consigne = False
            else:
                # Calculer les quantités en utilisant est_consigne
                qte_totale_consignee = sum(
                    vente.detail_emballage_vente_ids.filtered(
                        lambda l: l.est_consigne
                    ).mapped('qte_sortantes')
                )

                qte_totale_retournee = sum(
                    retours_valides.mapped('retour_line_ids.qte_retournee')
                )

                if qte_totale_consignee == 0:
                    vente.etat_consigne = False
                elif qte_totale_retournee >= qte_totale_consignee:
                    vente.etat_consigne = 'rendu'
                elif qte_totale_retournee > 0:
                    vente.etat_consigne = 'partiel'
                else:
                    vente.etat_consigne = 'non_rendu'
