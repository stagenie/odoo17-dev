# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleConsigneRetourLine(models.Model):
    _name = 'gecafle.consigne.retour.line'
    _description = 'Ligne de retour de consigne'

    retour_id = fields.Many2one(
        'gecafle.consigne.retour',
        string="Retour",
        required=True,
        ondelete='cascade'
    )

    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Emballage",
        required=True,
        readonly=False  # Permettre la sélection manuelle
    )

    qte_consignee = fields.Integer(
        string="Qté consignée",
        help="Quantité initialement consignée"
    )

    qte_retournee = fields.Integer(
        string="Qté retournée",
        required=True,
        default=0,
        help="Quantité effectivement retournée"
    )

    prix_unitaire = fields.Monetary(
        string="Prix unitaire",
        currency_field='currency_id'
    )

    montant_total = fields.Monetary(
        string="Montant",
        compute='_compute_montant',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='retour_id.currency_id',
        readonly=True
    )

    # IMPORTANT : Méthode onchange pour récupérer le prix automatiquement
    @api.onchange('emballage_id')
    def _onchange_emballage_id(self):
        """Récupère automatiquement le prix unitaire de l'emballage"""
        if self.emballage_id:
            # Récupérer le prix de l'emballage
            self.prix_unitaire = self.emballage_id.price_unit

            # Si pas de quantité consignée définie et qu'on crée manuellement
            if not self.qte_consignee and not self.retour_id.vente_id:
                # En création manuelle, initialiser qte_consignee avec qte_retournee
                self.qte_consignee = self.qte_retournee if self.qte_retournee else 1

    @api.onchange('qte_retournee')
    def _onchange_qte_retournee(self):
        """Met à jour la quantité consignée si création manuelle"""
        # Seulement en création manuelle (pas de vente liée)
        if not self.retour_id.vente_id and not self.qte_consignee:
            self.qte_consignee = self.qte_retournee

    @api.depends('qte_retournee', 'prix_unitaire')
    def _compute_montant(self):
        """Calcule le montant total de la ligne"""
        for record in self:
            record.montant_total = record.qte_retournee * record.prix_unitaire

    @api.constrains('qte_retournee', 'qte_consignee')
    def _check_qte_retournee(self):
        """Vérifie la cohérence des quantités"""
        for record in self:
            # La quantité retournée ne peut pas être négative
            if record.qte_retournee < 0:
                raise ValidationError(_("La quantité retournée ne peut pas être négative."))

            # Si création depuis une vente, vérifier la cohérence
            if record.retour_id.vente_id and record.qte_consignee:
                if record.qte_retournee > record.qte_consignee:
                    raise ValidationError(_(
                        "La quantité retournée (%s) ne peut pas dépasser la quantité consignée (%s) pour %s"
                    ) % (record.qte_retournee, record.qte_consignee, record.emballage_id.name))

    @api.model
    def create(self, vals):
        """Override create pour s'assurer que le prix est défini"""
        # Si l'emballage est défini mais pas le prix, récupérer le prix
        if vals.get('emballage_id') and not vals.get('prix_unitaire'):
            emballage = self.env['gecafle.emballage'].browse(vals['emballage_id'])
            vals['prix_unitaire'] = emballage.price_unit

        # Si pas de qte_consignee et création manuelle, utiliser qte_retournee
        if not vals.get('qte_consignee') and vals.get('qte_retournee'):
            vals['qte_consignee'] = vals['qte_retournee']

        return super().create(vals)

    def write(self, vals):
        """Override write pour maintenir la cohérence"""
        # Si on change l'emballage et qu'on n'a pas spécifié de nouveau prix
        if 'emballage_id' in vals and 'prix_unitaire' not in vals:
            emballage = self.env['gecafle.emballage'].browse(vals['emballage_id'])
            vals['prix_unitaire'] = emballage.price_unit

        return super().write(vals)
