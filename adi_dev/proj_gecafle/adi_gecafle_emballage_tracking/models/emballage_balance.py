# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class GecafleEmballageBalanceClient(models.Model):
    _name = 'gecafle.emballage.balance.client'
    _description = 'Balance Emballages Client'
    _auto = False
    _order = 'client_id, emballage_id'

    client_id = fields.Many2one('gecafle.client', string='Client', readonly=True)
    emballage_id = fields.Many2one('gecafle.emballage', string='Emballage', readonly=True)

    # CORRECTION : Alignement des noms de champs avec la vue
    total_sortant = fields.Integer(string='Total Sortant', readonly=True)
    total_entrant = fields.Integer(string='Total Entrant', readonly=True)
    solde = fields.Integer(string='Solde', readonly=True)
    last_movement = fields.Datetime(string='Dernier mouvement', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    m.client_id,
                    t.emballage_id,
                    SUM(CASE WHEN m.type_mouvement = 'sortie_vente' THEN m.quantite ELSE 0 END) AS total_sortant,
                    SUM(CASE WHEN m.type_mouvement IN ('retour_client', 'consigne') THEN m.quantite ELSE 0 END) AS total_entrant,
                    SUM(CASE 
                        WHEN m.type_mouvement = 'sortie_vente' THEN m.quantite 
                        WHEN m.type_mouvement IN ('retour_client', 'consigne') THEN -m.quantite 
                        ELSE 0 
                    END) AS solde,
                    MAX(m.date) AS last_movement
                FROM gecafle_emballage_mouvement m
                INNER JOIN gecafle_emballage_tracking t ON m.tracking_id = t.id
                WHERE m.client_id IS NOT NULL
                  AND m.is_cancelled = False
                GROUP BY m.client_id, t.emballage_id
                HAVING SUM(CASE 
                    WHEN m.type_mouvement = 'sortie_vente' THEN m.quantite 
                    WHEN m.type_mouvement IN ('retour_client', 'consigne') THEN -m.quantite 
                    ELSE 0 
                END) != 0
            )
        """ % self._table)


class GecafleEmballageBalanceProducteur(models.Model):
    _name = 'gecafle.emballage.balance.producteur'
    _description = 'Balance Emballages Producteur'
    _auto = False
    _order = 'producteur_id, emballage_id'

    producteur_id = fields.Many2one('gecafle.producteur', string='Producteur', readonly=True)
    emballage_id = fields.Many2one('gecafle.emballage', string='Emballage', readonly=True)

    # CORRECTION : Alignement des noms de champs avec la vue
    total_entrant = fields.Integer(string='Total Entrant', readonly=True)
    total_sortant = fields.Integer(string='Total Sortant', readonly=True)
    solde = fields.Integer(string='Solde', readonly=True)
    last_movement = fields.Datetime(string='Dernier mouvement', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    m.producteur_id,
                    t.emballage_id,
                    SUM(CASE WHEN m.type_mouvement IN ('entree_reception', 'retour_producteur') THEN m.quantite ELSE 0 END) AS total_entrant,
                    SUM(CASE WHEN m.type_mouvement = 'sortie_producteur' THEN m.quantite ELSE 0 END) AS total_sortant,
                    SUM(CASE 
                        WHEN m.type_mouvement IN ('entree_reception', 'retour_producteur') THEN m.quantite 
                        WHEN m.type_mouvement = 'sortie_producteur' THEN -m.quantite 
                        ELSE 0 
                    END) AS solde,
                    MAX(m.date) AS last_movement
                FROM gecafle_emballage_mouvement m
                INNER JOIN gecafle_emballage_tracking t ON m.tracking_id = t.id
                WHERE m.producteur_id IS NOT NULL
                  AND m.is_cancelled = False
                GROUP BY m.producteur_id, t.emballage_id
                HAVING SUM(CASE 
                    WHEN m.type_mouvement IN ('entree_reception', 'retour_producteur') THEN m.quantite 
                    WHEN m.type_mouvement = 'sortie_producteur' THEN -m.quantite 
                    ELSE 0 
                END) != 0
            )
        """ % self._table)
