# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TreasuryOperationCategory(models.Model):
    _name = 'treasury.operation.category'
    _description = 'Catégorie d\'opération de caisse'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Code court pour identifier la catégorie"
    )
    operation_type = fields.Selection([
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('both', 'Entrée et Sortie')
    ], string='Type d\'opération', required=True, default='both')

    sequence = fields.Integer(
        string='Séquence',
        default=10
    )
    active = fields.Boolean(
        string='Actif',
        default=True
    )

    # Pour l'intégration automatique
    is_customer_payment = fields.Boolean(
        string='Paiement client',
        help="Cocher si cette catégorie est utilisée pour les paiements clients"
    )
    is_vendor_payment = fields.Boolean(
        string='Paiement fournisseur',
        help="Cocher si cette catégorie est utilisée pour les paiements fournisseurs"
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Le code doit être unique !'),
    ]

    @api.model
    def _create_default_categories(self):
        """Créer les catégories par défaut"""
        categories = [
            {'name': 'Vente', 'code': 'VENTE', 'operation_type': 'in', 'is_customer_payment': True},
            {'name': 'Service', 'code': 'SERVICE', 'operation_type': 'in'},
            {'name': 'Paiement client', 'code': 'PAY_CLIENT', 'operation_type': 'in', 'is_customer_payment': True},
            {'name': 'Achat', 'code': 'ACHAT', 'operation_type': 'out'},
            {'name': 'Paiement fournisseur', 'code': 'PAY_FOURN', 'operation_type': 'out', 'is_vendor_payment': True},
            {'name': 'Fournitures', 'code': 'FOURNITURE', 'operation_type': 'out'},
            {'name': 'Transport', 'code': 'TRANSPORT', 'operation_type': 'out'},
            {'name': 'Autres frais', 'code': 'FRAIS', 'operation_type': 'out'},
            {'name': 'Ajustement', 'code': 'AJUST', 'operation_type': 'both'},
        ]

        for vals in categories:
            if not self.search([('code', '=', vals['code'])]):
                self.create(vals)
