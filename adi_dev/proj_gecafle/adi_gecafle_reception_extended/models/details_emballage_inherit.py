# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DetailsEmballageReceptionExtended(models.Model):
    _inherit = 'gecafle.details_emballage_reception'

    # Nouveaux champs pour l'achat d'emballages
    is_achete = fields.Boolean(
        string="Acheté",
        default=False,
        help="Cochez si cet emballage est acheté auprès du producteur"
    )

    qte_achetee = fields.Integer(
        string="Quantité Achetée",
        default=0
    )

    prix_unitaire_achat = fields.Float(
        string="Prix Unitaire",
        digits='Product Price',
        compute='_compute_prix_unitaire',
        inverse='_set_prix_unitaire',
        store=True
    )

    montant_achat = fields.Monetary(
        string="Montant",
        compute='_compute_montant_achat',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='reception_id.currency_id',
        store=True
    )

    @api.depends('emballage_id', 'is_achete')
    def _compute_prix_unitaire(self):
        """Initialise le prix unitaire avec le prix par défaut de l'emballage"""
        for line in self:
            if line.is_achete and line.emballage_id and not line.prix_unitaire_achat:
                line.prix_unitaire_achat = line.emballage_id.price_unit
            elif not line.is_achete:
                line.prix_unitaire_achat = 0

    def _set_prix_unitaire(self):
        """Permet la modification manuelle du prix"""
        pass

    @api.depends('is_achete', 'qte_achetee', 'prix_unitaire_achat')
    def _compute_montant_achat(self):
        """Calcule le montant total de l'achat"""
        for line in self:
            if line.is_achete:
                line.montant_achat = line.qte_achetee * line.prix_unitaire_achat
            else:
                line.montant_achat = 0

    @api.model_create_multi
    def create(self, vals_list):
        """Applique la logique par défaut lors de la création"""
        records = super().create(vals_list)

        for record in records:
            # Appliquer la logique uniquement si c'est une réception valorisée
            if record.reception_id and record.reception_id.is_achat_valorise:
                if record.emballage_id and record.emballage_id.non_returnable:
                    # Si non rendu, marquer comme acheté par défaut
                    if not record.is_achete:  # Seulement si pas déjà défini manuellement
                        record.is_achete = True
                        # Initialiser la quantité si pas déjà définie
                        if not record.qte_achetee and record.qte_entrantes:
                            record.qte_achetee = record.qte_entrantes
                        # Initialiser le prix si pas déjà défini
                        if not record.prix_unitaire_achat and record.emballage_id.price_unit:
                            record.prix_unitaire_achat = record.emballage_id.price_unit

        return records

    @api.onchange('emballage_id')
    def _onchange_emballage_id(self):
        """Active automatiquement 'is_achete' si l'emballage est non-rendu"""
        # Appliquer la logique uniquement si c'est une réception valorisée
        if self.reception_id and self.reception_id.is_achat_valorise:
            if self.emballage_id and self.emballage_id.non_returnable:
                self.is_achete = True
                # Initialiser automatiquement la quantité et le prix
                if self.qte_entrantes:
                    self.qte_achetee = self.qte_entrantes
                if self.emballage_id.price_unit:
                    self.prix_unitaire_achat = self.emballage_id.price_unit

    @api.onchange('is_achete')
    def _onchange_is_achete(self):
        """Réinitialise les valeurs si décoché"""
        if not self.is_achete:
            self.qte_achetee = 0
            self.prix_unitaire_achat = 0
        else:
            # Initialiser avec la quantité entrante par défaut
            if not self.qte_achetee and self.qte_entrantes:
                self.qte_achetee = self.qte_entrantes
            # Initialiser avec le prix par défaut
            if self.emballage_id and not self.prix_unitaire_achat:
                self.prix_unitaire_achat = self.emballage_id.price_unit
