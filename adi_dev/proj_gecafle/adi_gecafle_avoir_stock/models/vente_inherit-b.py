# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleVente(models.Model):
    _inherit = 'gecafle.vente'

    def action_create_avoir_with_details(self):
        """
        Action qui prépare toutes les lignes de détails et ouvre le wizard
        avec les données pré-calculées
        """
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("La vente doit être validée pour créer un avoir."))

        # Préparer les lignes de détails depuis les détails de vente
        lines_data = []
        for line in self.detail_vente_ids:
            lines_data.append({
                'detail_vente_id': line.id,
                'produit_id': line.produit_id.id,
                'producteur_id': line.producteur_id.id,
                'qualite_id': line.qualite_id.id if line.qualite_id else False,
                'type_colis_id': line.type_colis_id.id,
                'prix_unitaire': line.prix_unitaire,
                'nombre_colis_vendu': line.nombre_colis,
                'qte_vendue': line.poids_net,
                'nombre_colis_retour': 0,
                'qte_retour': 0,
                'inclure': False,
            })

        # Créer le wizard avec les lignes pré-remplies
        wizard = self.env['gecafle.avoir.client.wizard'].create({
            'vente_id': self.id,
            'montant_vente': self.montant_total_a_payer,
            'montant_avoir': self.montant_total_a_payer * 0.1,  # 10% par défaut
            'type_avoir': self.env.company.avoir_default_type or 'non_vendu',
            'description': _('Avoir stock avec sélection détaillée'),
            'mode_stock_detail': False,  # Par défaut désactivé
            'generer_avoirs_producteurs': True,
            'line_ids': [(0, 0, line_data) for line_data in lines_data],
        })

        # Retourner l'action d'ouverture du wizard
        return {
            'name': _('Création d\'Avoir avec Détails'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.avoir.client.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'context': {
                'dialog_size': 'extra-large',
            }
        }
