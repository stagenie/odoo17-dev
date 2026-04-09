# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class RonConsumptionAnalysis(models.Model):
    """
    Vue SQL d'analyse des consommations de matières premières.

    Agrège les lignes de consommation (ron.consumption.line) avec les
    informations de la production journalière parente, afin de permettre
    une analyse par période (jour, mois, année), par produit, par type
    de production (SOLO/CLASSICO ou Sandwich GF) via des vues
    graph / pivot / tree et un rapport PDF.

    Principales métriques exposées:
    - quantity              : quantité consommée (dans l'UdM du produit)
    - weight_kg             : poids total consommé en kilogrammes
    - total_cost            : coût total de la consommation
    - unit_cost             : coût unitaire (dernier AVCO utilisé)
    - total_cartons_produced: cartons de produit fini de la production parente
    - consumption_per_carton: ratio kg MP / carton de produit fini
    """
    _name = 'ron.consumption.analysis'
    _description = 'Analyse des Consommations par Période'
    _auto = False
    _rec_name = 'product_id'
    _order = 'production_date desc'

    # ========== DIMENSIONS ==========
    id = fields.Integer(string='ID', readonly=True)

    production_id = fields.Many2one(
        'ron.daily.production',
        string='Production Journalière',
        readonly=True,
    )

    production_date = fields.Date(
        string='Date de Production',
        readonly=True,
    )

    production_type = fields.Selection(
        [
            ('solo_classico', 'SOLO / CLASSICO'),
            ('sandwich_gf', 'Sandwich Grand Format'),
        ],
        string='Type de Production',
        readonly=True,
    )

    production_state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('confirmed', 'Confirmé'),
            ('validated', 'Validé'),
            ('done', 'Terminé'),
        ],
        string='État Production',
        readonly=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Matière Première',
        readonly=True,
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Article',
        readonly=True,
    )

    product_category_id = fields.Many2one(
        'product.category',
        string='Catégorie',
        readonly=True,
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unité de Mesure',
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        readonly=True,
    )

    # ========== MESURES ==========
    quantity = fields.Float(
        string='Quantité Consommée',
        readonly=True,
        group_operator='sum',
        digits='Product Unit of Measure',
    )

    weight_kg = fields.Float(
        string='Poids Consommé (kg)',
        readonly=True,
        group_operator='sum',
        digits='Product Unit of Measure',
    )

    unit_cost = fields.Float(
        string='Coût Unitaire',
        readonly=True,
        group_operator='avg',
        digits='Product Price',
    )

    total_cost = fields.Monetary(
        string='Coût Total',
        readonly=True,
        group_operator='sum',
        currency_field='currency_id',
    )

    # Production parente : cartons produits
    total_cartons_produced = fields.Float(
        string='Cartons Produits',
        readonly=True,
        group_operator='sum',
        help="Total des cartons produits ce jour-là (tous produits finis confondus)",
    )

    qty_solo_cartons = fields.Float(
        string='Cartons SOLO',
        readonly=True,
        group_operator='sum',
    )

    qty_classico_cartons = fields.Float(
        string='Cartons CLASSICO',
        readonly=True,
        group_operator='sum',
    )

    qty_sandwich_cartons = fields.Float(
        string='Cartons Sandwich GF',
        readonly=True,
        group_operator='sum',
    )

    consumption_per_carton = fields.Float(
        string='Kg MP / Carton',
        readonly=True,
        group_operator='avg',
        digits='Product Unit of Measure',
        help="Poids consommé / nombre de cartons produits",
    )

    def init(self):
        """Crée la vue SQL d'agrégation."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    cl.id                              AS id,
                    cl.daily_production_id             AS production_id,
                    dp.production_date                 AS production_date,
                    dp.production_type                 AS production_type,
                    dp.state                           AS production_state,
                    cl.product_id                      AS product_id,
                    pp.product_tmpl_id                 AS product_tmpl_id,
                    pt.categ_id                        AS product_category_id,
                    pt.uom_id                          AS product_uom_id,
                    dp.company_id                      AS company_id,
                    rc.currency_id                     AS currency_id,
                    COALESCE(cl.quantity, 0.0)         AS quantity,
                    COALESCE(cl.weight_kg, 0.0)        AS weight_kg,
                    COALESCE(cl.unit_cost, 0.0)        AS unit_cost,
                    COALESCE(cl.total_cost, 0.0)       AS total_cost,
                    COALESCE(dp.total_cartons_produced, 0.0) AS total_cartons_produced,
                    COALESCE(dp.qty_solo_cartons, 0.0) AS qty_solo_cartons,
                    COALESCE(dp.qty_classico_cartons, 0.0) AS qty_classico_cartons,
                    COALESCE(dp.qty_sandwich_cartons, 0.0) AS qty_sandwich_cartons,
                    CASE
                        WHEN COALESCE(dp.total_cartons_produced, 0.0) > 0
                        THEN COALESCE(cl.weight_kg, 0.0) / dp.total_cartons_produced
                        ELSE 0.0
                    END                                AS consumption_per_carton
                FROM ron_consumption_line cl
                JOIN ron_daily_production dp
                    ON dp.id = cl.daily_production_id
                JOIN product_product pp
                    ON pp.id = cl.product_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                JOIN res_company rc
                    ON rc.id = dp.company_id
            )
            """
            % self._table
        )
