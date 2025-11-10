# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GecafleDetailsReceptionValorisee(models.Model):
    _inherit = 'gecafle.details_reception'

    # Nouveaux champs pour la valorisation
    poids_brut = fields.Float(
        string="Poids Brut",
        digits=(16, 2),
        default=0.0
    )

    poids_colis = fields.Float(
        string="Poids Colis",
        compute='_compute_poids_colis',
        store=True,
        digits=(16, 2)
    )

    poids_net = fields.Float(
        string="Poids Net",
        compute='_compute_poids_net',
        store=True,
        digits=(16, 2)
    )

    prix_unitaire_achat = fields.Float(
        string="Prix Unitaire d'Achat",
        digits='Product Price',
        default=0.0
    )

    montant_ligne = fields.Monetary(
        string="Montant",
        compute='_compute_montant_ligne',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='reception_id.currency_id',
        store=True
    )

    @api.depends('qte_colis_recue', 'type_colis_id', 'reception_id.is_achat_valorise')
    def _compute_poids_colis(self):
        """Calcule le poids total des colis"""
        for line in self:
            if line.reception_id.is_achat_valorise and line.type_colis_id:
                line.poids_colis = line.qte_colis_recue * line.type_colis_id.weight
            else:
                line.poids_colis = 0

    @api.depends('poids_brut', 'poids_colis', 'reception_id.is_achat_valorise')
    def _compute_poids_net(self):
        """Calcule le poids net"""
        for line in self:
            if line.reception_id.is_achat_valorise:
                line.poids_net = line.poids_brut - line.poids_colis
            else:
                line.poids_net = 0

    @api.depends('poids_net', 'prix_unitaire_achat', 'reception_id.is_achat_valorise')
    def _compute_montant_ligne(self):
        """Calcule le montant de la ligne"""
        for line in self:
            if line.reception_id.is_achat_valorise:
                line.montant_ligne = line.poids_net * line.prix_unitaire_achat
            else:
                line.montant_ligne = 0

    @api.constrains('poids_brut', 'poids_colis')
    def _check_poids(self):
        """Vérifie la cohérence des poids"""
        for line in self:
            if line.reception_id.is_achat_valorise:
                if line.poids_brut < 0:
                    raise ValidationError(_("Le poids brut ne peut pas être négatif."))
                if line.poids_brut < line.poids_colis:
                    raise ValidationError(_(
                        "Le poids brut (%s) ne peut pas être inférieur au poids des colis (%s)."
                    ) % (line.poids_brut, line.poids_colis))

