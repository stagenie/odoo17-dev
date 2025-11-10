# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleVenteInherit(models.Model):
    _inherit = 'gecafle.vente'

    def action_refresh_receptions(self):
        """
        Action pour rafraîchir les réceptions disponibles
        Cette méthode peut être vide si elle n'est pas utilisée
        """
        # Simplement retourner True ou faire une action si nécessaire
        return True

    # Poids unitaire moyen global de la vente
    """ 
    
    """
    poids_unitaire_moyen_global = fields.Float(
        string="Poids unitaire moyen global",
        compute='_compute_poids_unitaire_moyen_global',
        store=True,
        digits=(16, 3),
        help="Poids net moyen par colis pour toute la vente (kg)"
    )

    @api.depends('detail_vente_ids.poids_unitaire_moyen', 'detail_vente_ids.nombre_colis')
    def _compute_poids_unitaire_moyen_global(self):
        """Calcule le poids unitaire moyen pondéré global"""
        for vente in self:
            total_colis = sum(vente.detail_vente_ids.mapped('nombre_colis'))
            total_poids_net = sum(vente.detail_vente_ids.mapped('poids_net'))

            if total_colis > 0:
                vente.poids_unitaire_moyen_global = total_poids_net / total_colis
            else:
                vente.poids_unitaire_moyen_global = 0

    # Override du calcul des totaux pour tenir compte du comportement personnalisé
    @api.depends('detail_vente_ids.montant_commission',
                 'detail_vente_ids.montant_net',
                 'detail_vente_ids.nombre_colis',
                 'detail_vente_ids.type_colis_id',
                 'detail_vente_ids.montant_colis',
                 'detail_vente_ids.est_consigne',
                 'detail_vente_ids.force_comportement_emballage',
                 'client_id.est_fidel',
                 'montant_remise_globale',
                 'company_id.fideles_paient_emballages_non_rendus')
    def _compute_totaux_vente(self):
        """Override du calcul des totaux avec le comportement personnalisé des emballages"""
        # D'abord appeler la méthode parent pour calculer les totaux de base
        super()._compute_totaux_vente()

        for vente in self:
            # Recalculer les montants d'emballages selon le comportement personnalisé
            montant_total_emballages = 0
            montant_total_consigne = 0
            montant_emballages_non_rendus = 0
            montant_emballages_rendus = 0

            for line in vente.detail_vente_ids:
                if line.type_colis_id:
                    # Utiliser le montant_colis calculé avec le prix personnalisé
                    montant_ligne_emballage = line.montant_colis
                    montant_total_emballages += montant_ligne_emballage

                    # Déterminer si c'est consigné selon est_consigne
                    if line.est_consigne:
                        # Emballage rendu/consigné
                        montant_total_consigne += montant_ligne_emballage
                        montant_emballages_rendus += montant_ligne_emballage
                    else:
                        # Emballage non rendu/payé
                        montant_emballages_non_rendus += montant_ligne_emballage

            # Mettre à jour les montants
            vente.montant_total_emballages = montant_total_emballages
            vente.montant_total_consigne = montant_total_consigne
            vente.montant_emballages_non_rendus = montant_emballages_non_rendus
            vente.montant_emballages_rendus = montant_emballages_rendus

            # Recalculer le montant à payer selon le type de client
            if vente.client_id and vente.client_id.est_fidel:
                # Client fidèle : paie seulement les emballages non rendus si configuré
                montant_emballages_a_payer = 0
                if vente.company_id.fideles_paient_emballages_non_rendus:
                    montant_emballages_a_payer = montant_emballages_non_rendus
                vente.montant_total_a_payer_calc = vente.montant_total_net + montant_emballages_a_payer
            else:
                # Client non fidèle : paie tous les emballages
                vente.montant_total_a_payer_calc = vente.montant_total_net + vente.montant_total_emballages

            # Appliquer la remise
            vente.montant_total_a_payer = vente.montant_total_a_payer_calc - vente.montant_remise_globale

    def generate_emballage_lines(self):
        """Override pour tenir compte du comportement personnalisé"""
        self.ensure_one()

        # Suppression des lignes existantes
        self.detail_emballage_vente_ids.unlink()

        # Dictionnaire pour regrouper les emballages
        emballage_dict = {}

        for line in self.detail_vente_ids:
            if line.type_colis_id and line.nombre_colis > 0:
                emballage_id = line.type_colis_id.id

                if emballage_id not in emballage_dict:
                    emballage_dict[emballage_id] = {
                        'sortantes': 0,
                        'entrantes': 0
                    }

                # Les emballages sortent toujours
                emballage_dict[emballage_id]['sortantes'] += line.nombre_colis

                # Si c'est consigné (rendu), on attend le retour
                # Si non consigné (non rendu), pas de retour attendu
                if line.est_consigne:
                    # On pourrait gérer les entrantes différemment si besoin
                    pass

        # Créer les lignes d'emballage
        for emballage_id, qtés in emballage_dict.items():
            self.env['gecafle.details_emballage_vente'].create({
                'vente_id': self.id,
                'emballage_id': emballage_id,
                'qte_sortantes': qtés['sortantes'],
                'qte_entrantes': qtés.get('entrantes', 0),
            })

        return True

    def action_create_avoir_express(self):
        # 🔁 Appelle simplement la méthode originale
        return super(GecafleVenteInherit, self).action_create_avoir_express()


