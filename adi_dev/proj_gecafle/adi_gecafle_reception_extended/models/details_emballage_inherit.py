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
