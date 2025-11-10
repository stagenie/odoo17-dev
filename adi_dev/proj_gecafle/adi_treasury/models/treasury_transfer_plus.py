# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from num2words import num2words


class TreasuryTransferInherited(models.Model):
    _inherit = 'treasury.transfer'

    # Lien avec les opérations de caisse créées
    cash_operation_ids = fields.One2many(
        'treasury.cash.operation',
        'transfer_id',
        string='Opérations de caisse liées',
        readonly=True
    )

    def _create_cash_operations(self):
        """Créer automatiquement les opérations de caisse pour les transferts"""
        self.ensure_one()

        operation_obj = self.env['treasury.cash.operation']

        # Catégories de transfert
        cat_transfer_in = self.env.ref('adi_treasury.category_transfer_in', raise_if_not_found=False)
        cat_transfer_out = self.env.ref('adi_treasury.category_transfer_out', raise_if_not_found=False)

        if not cat_transfer_in or not cat_transfer_out:
            # Créer les catégories si elles n'existent pas
            if not cat_transfer_out:
                cat_transfer_out = self.env['treasury.operation.category'].create({
                    'name': 'Transfert sortant',
                    'code': 'TRANSFER_OUT',
                    'operation_type': 'out',
                    'sequence': 31
                })
            if not cat_transfer_in:
                cat_transfer_in = self.env['treasury.operation.category'].create({
                    'name': 'Transfert entrant',
                    'code': 'TRANSFER_IN',
                    'operation_type': 'in',
                    'sequence': 30
                })

        operations_created = self.env['treasury.cash.operation']

        # Transfert CAISSE vers COFFRE
        if self.transfer_type == 'cash_to_safe' and self.cash_from_id:
            # Créer une opération de sortie pour la caisse source
            op_out = operation_obj.create({
                'cash_id': self.cash_from_id.id,
                'operation_type': 'out',
                'category_id': cat_transfer_out.id,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfert vers coffre %s") % self.safe_to_id.name,
                'reference': self.name,
                'state': 'posted',
                'is_manual': False,
            })
            operations_created |= op_out

        # Transfert COFFRE vers CAISSE
        elif self.transfer_type == 'safe_to_cash' and self.cash_to_id:
            # Créer une opération d'entrée pour la caisse destination
            op_in = operation_obj.create({
                'cash_id': self.cash_to_id.id,
                'operation_type': 'in',
                'category_id': cat_transfer_in.id,
                'amount': self.amount,
                'date': self.date,
                'description': _("Transfert depuis coffre %s") % self.safe_from_id.name,
                'reference': self.name,
                'state': 'posted',
                'is_manual': False,
            })
            operations_created |= op_in

        # Transfert CAISSE vers CAISSE
        elif self.transfer_type == 'cash_to_cash':
            # Opération de sortie pour la caisse source
            if self.cash_from_id:
                op_out = operation_obj.create({
                    'cash_id': self.cash_from_id.id,
                    'operation_type': 'out',
                    'category_id': cat_transfer_out.id,
                    'amount': self.amount,
                    'date': self.date,
                    'description': _("Transfert vers caisse %s") % self.cash_to_id.name,
                    'reference': self.name,
                    'state': 'posted',
                    'is_manual': False,
                })
                operations_created |= op_out

            # Opération d'entrée pour la caisse destination
            if self.cash_to_id:
                op_in = operation_obj.create({
                    'cash_id': self.cash_to_id.id,
                    'operation_type': 'in',
                    'category_id': cat_transfer_in.id,
                    'amount': self.amount,
                    'date': self.date,
                    'description': _("Transfert depuis caisse %s") % self.cash_from_id.name,
                    'reference': self.name,
                    'state': 'posted',
                    'is_manual': False,
                })
                operations_created |= op_in

        # Lier les opérations au transfert
        if operations_created:
            self.cash_operation_ids = [(6, 0, operations_created.ids)]

        return operations_created

    def action_done(self):
        """Valider et effectuer le transfert"""
        res = super().action_done()

        for transfer in self:
            # Créer les opérations de caisse après validation
            transfer._create_cash_operations()

        return res



