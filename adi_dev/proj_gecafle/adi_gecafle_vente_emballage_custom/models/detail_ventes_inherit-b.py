# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleDetailsVentesInherit(models.Model):
    _inherit = 'gecafle.details_ventes'

    # Sélecteur Rendu/Non Rendu
    force_comportement_emballage = fields.Selection([
        ('rendu', 'Rendu (Consigné)'),
        ('non_rendu', 'Non Rendu (Payé)')
    ], string="Type emballage",
        help="Rendu = Consigné (remboursable), Non Rendu = Payé par le client")

    # Prix unitaire d'un colis (modifiable)
    prix_unitaire_colis = fields.Float(
        string="Prix unitaire colis",
        compute='_compute_prix_unitaire_colis',
        inverse='_set_prix_unitaire_colis',
        store=True,
        digits=(16, 2),
        help="Prix d'un seul colis/emballage"
    )

    # Montant total des colis
    montant_colis = fields.Float(
        string="Montant colis",
        compute='_compute_montant_colis',
        store=True,
        digits=(16, 2),
        help="Montant total des emballages"
    )

    # CORRECTION : Override du poids brut unitaire
    poids_brut_un_colis = fields.Float(
        string="Poids Brut /U",
        compute='_compute_poids_brut_unitaire_correct',
        store=True,
        digits=(16, 3),
        help="Poids brut par colis"
    )

    # Poids unitaire moyen (poids net / nombre de colis)
    poids_unitaire_moyen = fields.Float(
        string="Poids unitaire moyen",
        compute='_compute_poids_unitaire_moyen',
        store=True,
        digits=(16, 3),
        help="Poids net moyen par colis (kg)"
    )

    # Prix brut par unité
    prix_brut_unitaire = fields.Float(
        string="Prix Brut /U",
        compute='_compute_prix_brut_unitaire',
        store=True,
        digits=(16, 2),
        help="Prix brut par colis"
    )

    # Poids brut unitaire
    poids_brut_unitaire = fields.Float(
        string="Poids Brut Unit.",
        compute='_compute_poids_brut_unitaire_correct',
        store=True,
        digits=(16, 3),
        help="Poids brut moyen par colis"
    )

    # Indicateur si l'emballage entre dans la consigne
    est_consigne = fields.Boolean(
        string="Est consigné",
        compute='_compute_est_consigne',
        store=True,
        help="Indique si cet emballage entre dans la consigne"
    )

    # MÉTHODE CORRIGÉE pour poids_brut_un_colis
    @api.depends('poids_brut', 'nombre_colis')
    def _compute_poids_brut_unitaire_correct(self):
        """CORRECTION : Calcule simplement poids_brut / nombre_colis"""
        for record in self:
            if record.nombre_colis > 0:
                record.poids_brut_un_colis = record.poids_brut / record.nombre_colis
                record.poids_brut_unitaire = record.poids_brut / record.nombre_colis
            else:
                record.poids_brut_un_colis = 0
                record.poids_brut_unitaire = 0

    @api.depends('type_colis_id')
    def _compute_prix_unitaire_colis(self):
        """Initialise le prix unitaire du colis depuis l'emballage"""
        for record in self:
            if record.type_colis_id and not record.prix_unitaire_colis:
                record.prix_unitaire_colis = record.type_colis_id.price_unit

    def _set_prix_unitaire_colis(self):
        """Permet la modification manuelle du prix unitaire"""
        pass

    @api.onchange('type_colis_id')
    def _onchange_type_colis_id(self):
        """Met à jour le prix et le comportement lors du changement d'emballage"""
        if self.type_colis_id:
            self.prix_unitaire_colis = self.type_colis_id.price_unit
            if not self.force_comportement_emballage:
                if self.type_colis_id.non_returnable:
                    self.force_comportement_emballage = 'non_rendu'
                else:
                    self.force_comportement_emballage = 'rendu'

    @api.depends('prix_unitaire_colis', 'nombre_colis')
    def _compute_montant_colis(self):
        """Calcule le montant total des colis"""
        for record in self:
            record.montant_colis = record.prix_unitaire_colis * record.nombre_colis

    @api.depends('poids_net', 'nombre_colis')
    def _compute_poids_unitaire_moyen(self):
        """Calcule le poids net moyen par colis"""
        for record in self:
            if record.nombre_colis > 0:
                record.poids_unitaire_moyen = record.poids_net / record.nombre_colis
            else:
                record.poids_unitaire_moyen = 0

    @api.depends('poids_brut_un_colis', 'prix_unitaire')
    def _compute_prix_brut_unitaire(self):
        """Calcule le prix brut par unité"""
        for record in self:
            record.prix_brut_unitaire = record.poids_brut_un_colis * record.prix_unitaire

    @api.depends('type_colis_id', 'force_comportement_emballage', 'vente_id.client_id.est_fidel')
    def _compute_est_consigne(self):
        """Détermine si l'emballage est consigné selon le comportement choisi"""
        for record in self:
            if not record.type_colis_id:
                record.est_consigne = False
                continue

            # Client fidèle : pas de consigne
            if record.vente_id and record.vente_id.client_id and record.vente_id.client_id.est_fidel:
                record.est_consigne = False
                continue

            # Déterminer selon le comportement forcé
            if record.force_comportement_emballage:
                record.est_consigne = (record.force_comportement_emballage == 'rendu')
            else:
                record.est_consigne = not record.type_colis_id.non_returnable

    @api.constrains('prix_unitaire_colis')
    def _check_prix_unitaire_colis(self):
        """Vérifie que le prix unitaire n'est pas négatif"""
        for record in self:
            if record.prix_unitaire_colis < 0:
                raise ValidationError(_("Le prix unitaire du colis ne peut pas être négatif"))

    # Override de la méthode _compute_prix_colis existante
    @api.depends('prix_unitaire_colis', 'nombre_colis', 'montant_colis')
    def _compute_prix_colis(self):
        """Override pour utiliser notre montant_colis"""
        for record in self:
            record.prix_colis = record.montant_colis
