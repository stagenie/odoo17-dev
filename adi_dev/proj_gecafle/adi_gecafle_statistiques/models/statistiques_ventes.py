# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class GecafleStatistiquesVentes(models.Model):
    _name = 'gecafle.statistiques.ventes'
    _description = 'Statistiques des Ventes'
    _auto = False  # Vue SQL
    _order = 'date_vente desc'

    # Dimensions
    date_vente = fields.Date(string="Date de vente")
    producteur_id = fields.Many2one('gecafle.producteur', string="Producteur")
    produit_id = fields.Many2one('gecafle.produit', string="Produit")
    qualite_id = fields.Many2one('gecafle.qualite', string="Qualité")
    client_id = fields.Many2one('gecafle.client', string="Client")
    region_id = fields.Many2one('gecafle.region', string="Région")
    type_produit = fields.Selection([
        ('fruit', 'Fruit'),
        ('legume', 'Légume')
    ], string="Type")

    # Mesures
    nombre_ventes = fields.Integer(string="Nombre de ventes")
    nombre_colis = fields.Integer(string="Nombre de colis")
    poids_total = fields.Float(string="Poids total (kg)", digits=(16, 2))
    montant_total = fields.Monetary(string="Montant total", currency_field='currency_id')
    montant_commission = fields.Monetary(string="Commission totale", currency_field='currency_id')
    montant_net = fields.Monetary(string="Montant net", currency_field='currency_id')
    prix_moyen = fields.Float(string="Prix moyen/kg", digits=(16, 2))
    taux_commission_moyen = fields.Float(string="Taux commission moyen (%)", digits=(5, 2))

    currency_id = fields.Many2one('res.currency', string="Devise")
    company_id = fields.Many2one('res.company', string="Société")

    def init(self):
        """Création de la vue SQL pour les statistiques"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    DATE(v.date_vente) as date_vente,
                    dv.producteur_id,
                    dv.produit_id,
                    dv.qualite_id,
                    v.client_id,
                    c.region_id,
                    p.type as type_produit,
                    COUNT(DISTINCT v.id) as nombre_ventes,
                    SUM(dv.nombre_colis) as nombre_colis,
                    SUM(dv.poids_net) as poids_total,
                    SUM(dv.montant_net) as montant_total,
                    SUM(dv.montant_commission) as montant_commission,
                    SUM(dv.montant_net - dv.montant_commission) as montant_net,
                    AVG(dv.prix_unitaire) as prix_moyen,
                    AVG(dv.taux_commission) as taux_commission_moyen,
                    v.currency_id,
                    v.company_id
                FROM gecafle_details_ventes dv
                JOIN gecafle_vente v ON dv.vente_id = v.id
                JOIN gecafle_client c ON v.client_id = c.id
                JOIN gecafle_produit p ON dv.produit_id = p.id
                WHERE v.state = 'valide'
                GROUP BY
                    DATE(v.date_vente),
                    dv.producteur_id,
                    dv.produit_id,
                    dv.qualite_id,
                    v.client_id,
                    c.region_id,
                    p.type,
                    v.currency_id,
                    v.company_id
            )
        """ % self._table)

    @api.model
    def get_statistics_by_product(self, date_from=None, date_to=None):
        """Statistiques par produit pour graphiques"""
        domain = []
        if date_from:
            domain.append(('date_vente', '>=', date_from))
        if date_to:
            domain.append(('date_vente', '<=', date_to))

        return self.read_group(
            domain,
            ['produit_id', 'montant_total:sum', 'poids_total:sum', 'nombre_colis:sum'],
            ['produit_id'],
            orderby='montant_total desc'
        )

    @api.model
    def get_statistics_by_producer(self, date_from=None, date_to=None):
        """Statistiques par producteur pour graphiques"""
        domain = []
        if date_from:
            domain.append(('date_vente', '>=', date_from))
        if date_to:
            domain.append(('date_vente', '<=', date_to))

        return self.read_group(
            domain,
            ['producteur_id', 'montant_total:sum', 'montant_commission:sum', 'poids_total:sum'],
            ['producteur_id'],
            orderby='montant_total desc'
        )
