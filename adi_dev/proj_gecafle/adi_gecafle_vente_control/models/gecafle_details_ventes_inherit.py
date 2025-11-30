# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleDetailsVentesControl(models.Model):
    _inherit = 'gecafle.details_ventes'

    def _can_edit_price_directly(self):
        """
        Vérifie si le prix peut être modifié directement sur une vente validée.

        Conditions :
        1. La vente doit être validée avec une facture
        2. La facture ne doit avoir AUCUN paiement (payment_state == 'not_paid')
        3. Aucune facture fournisseur ne doit exister sur les récaps liées

        Returns:
            tuple: (bool, str) - (autorisé, message d'erreur si non autorisé)
        """
        self.ensure_one()
        vente = self.vente_id

        # Vente doit être validée
        if vente.state != 'valide':
            return True, "OK"  # Pas de restriction si pas validée

        # Vérifier si facture existe
        if not vente.invoice_id:
            return True, "OK"  # Pas de restriction si pas de facture

        # Vérifier si facture a des paiements
        if vente.invoice_id.payment_state != 'not_paid':
            return False, _(
                "Impossible de modifier le prix : la facture %s a des paiements.\n"
                "État de paiement : %s"
            ) % (vente.invoice_id.name, vente.invoice_id.payment_state)

        # Vérifier les récaps liées (via la réception)
        recaps = self.env['gecafle.reception.recap'].search([
            ('reception_id', '=', self.reception_id.id),
            ('state', 'in', ['valide', 'facture'])
        ])

        for recap in recaps:
            if recap.invoice_id:
                return False, _(
                    "Impossible de modifier le prix : le bordereau %s a une facture fournisseur (%s).\n"
                    "Vous devez d'abord supprimer la facture fournisseur et ses paiements."
                ) % (recap.name, recap.invoice_id.name)

        return True, "OK"

    def write(self, vals):
        """
        Surcharge pour gérer la modification du prix sur les ventes validées facturées.

        Si le prix est modifié :
        1. Vérifier les conditions (pas de paiement, pas de facture fournisseur)
        2. Mettre à jour la ligne de vente
        3. Mettre à jour la facture client
        4. Mettre à jour la récap producteur si elle existe
        """
        # Stocker les anciens prix AVANT le write
        old_prices = {}
        records_to_update = self.env['gecafle.details_ventes']

        if 'prix_unitaire' in vals:
            for record in self:
                vente = record.vente_id

                # Vérifier si modification autorisée
                if vente.state == 'valide' and vente.invoice_id:
                    can_edit, message = record._can_edit_price_directly()
                    if not can_edit:
                        raise UserError(message)

                    old_price = record.prix_unitaire
                    new_price = vals['prix_unitaire']

                    if old_price != new_price:
                        old_prices[record.id] = old_price
                        records_to_update |= record
                        _logger.info(
                            f"Modification prix ligne vente {record.id}: "
                            f"{old_price} → {new_price}"
                        )

        # Exécuter le write standard avec contexte pour bypasser la contrainte sur la vente
        result = super(GecafleDetailsVentesControl, self.with_context(allow_price_edit=True)).write(vals)

        # Si le prix a été modifié, mettre à jour les cascades
        if 'prix_unitaire' in vals and records_to_update:
            for record in records_to_update:
                vente = record.vente_id

                if vente.state == 'valide' and vente.invoice_id:
                    # 1. Mettre à jour la facture client
                    record._update_invoice_line()

                    # 2. Mettre à jour la récap si elle existe
                    record._update_recap_lines()

                    # 3. Logger la modification dans le chatter
                    old_price = old_prices.get(record.id, 0)
                    record._log_price_change(old_price, vals['prix_unitaire'])

        return result

    def _update_invoice_line(self):
        """
        Met à jour la ligne de facture correspondante.

        La facture doit être en brouillon pour être modifiée,
        puis repostée si elle était postée.
        """
        self.ensure_one()
        vente = self.vente_id

        if not vente.invoice_id:
            return

        invoice = vente.invoice_id
        was_posted = invoice.state == 'posted'

        # Trouver la ligne de facture correspondante
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda l: l.gecafle_detail_vente_id.id == self.id
        )

        if not invoice_line:
            _logger.warning(
                f"Ligne de facture non trouvée pour detail_vente {self.id}"
            )
            return

        try:
            # Passer la facture en brouillon si postée
            # Utiliser force_gecafle_update pour bypasser la protection
            if was_posted:
                invoice.with_context(force_gecafle_update=True).button_draft()

            # Mettre à jour la ligne de facture
            # Recalculer le montant basé sur le nouveau prix
            invoice_line.with_context(check_move_validity=False).write({
                'price_unit': self.prix_unitaire,
                'prix_unitaire': self.prix_unitaire,
                'montant_net': self.montant_net,
                'montant_commission': self.montant_commission,
            })

            # Revalider la facture si elle était postée
            if was_posted:
                invoice.with_context(force_gecafle_update=True).action_post()

            _logger.info(
                f"Facture {invoice.name} mise à jour - "
                f"Ligne {invoice_line.id}: prix={self.prix_unitaire}"
            )

        except Exception as e:
            _logger.error(f"Erreur mise à jour facture: {str(e)}")
            raise UserError(_(
                "Erreur lors de la mise à jour de la facture:\n%s"
            ) % str(e))

    def _update_recap_lines(self):
        """
        Met à jour les lignes de récap producteur si elles existent.

        - Mise à jour des sale_line_ids (détails des ventes)
        - Regénération des recap_line_ids (lignes agrégées)
        - Recalcul des totaux
        """
        self.ensure_one()

        # Chercher les récaps liées à cette réception
        recaps = self.env['gecafle.reception.recap'].search([
            ('reception_id', '=', self.reception_id.id),
            ('state', 'in', ['brouillon', 'valide'])  # Pas 'facture'
        ])

        for recap in recaps:
            # Mettre à jour la ligne de vente dans la récap
            sale_lines = recap.sale_line_ids.filtered(
                lambda l: l.vente_id.id == self.vente_id.id and
                          l.produit_id.id == self.produit_id.id and
                          l.qualite_id.id == (self.qualite_id.id if self.qualite_id else False)
            )

            for sale_line in sale_lines:
                sale_line.write({
                    'prix_unitaire': self.prix_unitaire,
                    'montant_net': self.montant_net,
                    'montant_commission': self.montant_commission,
                })

            # Regénérer les lignes récapitulatives (agrégées)
            recap.generate_recap_lines()

            _logger.info(
                f"Récap {recap.name} mise à jour - "
                f"Nouveaux totaux: ventes={recap.total_ventes}, "
                f"commission={recap.total_commission}, net={recap.net_a_payer}"
            )

            # Message dans le chatter de la récap
            recap.message_post(
                body=_(
                    "📝 Mise à jour automatique suite à modification de prix\n"
                    "Vente: %s\n"
                    "Produit: %s\n"
                    "Nouveau prix: %s"
                ) % (self.vente_id.name, self.produit_id.name, self.prix_unitaire),
                message_type='notification'
            )

    def _log_price_change(self, old_price, new_price):
        """
        Enregistre la modification de prix dans le chatter de la vente.
        """
        self.ensure_one()

        self.vente_id.message_post(
            body=_(
                "💰 <b>Modification de prix</b>\n"
                "<ul>"
                "<li>Produit: %s</li>"
                "<li>Qualité: %s</li>"
                "<li>Ancien prix: %.2f</li>"
                "<li>Nouveau prix: %.2f</li>"
                "<li>Nouveau montant net: %.2f</li>"
                "</ul>"
                "Facture et récap mises à jour automatiquement."
            ) % (
                self.produit_id.name,
                self.qualite_id.name if self.qualite_id else '-',
                old_price,
                new_price,
                self.montant_net
            ),
            message_type='comment'
        )
