# -*- coding: utf-8 -*-

from odoo import models, fields, tools


# Définition des 6 sources d'emballages/films sur ron_daily_production.
# Chaque tuple contient :
#   (offset_id, category, subtype_label, qty_field, unit_cost_field, cost_field)
#
# offset_id sert à générer un ID unique négatif pour chaque ligne synthétique :
#   id = -(dp.id * 100 + offset_id)
# → ne peut jamais entrer en collision avec ron_consumption_line.id (toujours > 0).
_PACKAGING_SOURCES = [
    (10, 'packaging', 'Emballage SOLO',
     'emballage_solo_qty', 'emballage_solo_unit_cost', 'emballage_solo_cost'),
    (11, 'packaging', 'Emballage CLASSICO',
     'emballage_classico_qty', 'emballage_classico_unit_cost', 'emballage_classico_cost'),
    (12, 'packaging', 'Emballage Sandwich GF',
     'emballage_sandwich_qty', 'emballage_sandwich_unit_cost', 'emballage_sandwich_cost'),
    (20, 'film', 'Film SOLO',
     'film_solo_qty', 'film_solo_unit_cost', 'film_solo_cost'),
    (21, 'film', 'Film CLASSICO',
     'film_classico_qty', 'film_classico_unit_cost', 'film_classico_cost'),
    (22, 'film', 'Film Sandwich GF',
     'film_sandwich_qty', 'film_sandwich_unit_cost', 'film_sandwich_cost'),
]


# Sources Rebuts/Pâte récupérables sur ron_scrap_line.
# Chaque tuple : (offset_id, scrap_type_value, category, subtype_label)
#   id = -(sl.id * 100 + offset_id)
# offsets {50, 51} disjoints des packaging {10..22} → pas de collision possible
# entre ron_consumption_line.id, dp.id*100+{10..22} et sl.id*100+{50,51}.
_RECOVERABLE_SOURCES = [
    (50, 'scrap_recoverable', 'scrap_recoverable', 'Rebut Récupérable'),
    (51, 'paste_recoverable', 'paste_recoverable', 'Pâte Récupérable'),
]


class RonConsumptionAnalysis(models.Model):
    """Extension de la vue d'analyse pour inclure emballages et films.

    Ajoute deux dimensions :
      - consumption_category : 'raw_material' / 'packaging' / 'film'
      - consumption_subtype  : libellé textuel pour les lignes synthétiques

    Les lignes emballage/film sont générées par UNION ALL à partir des
    champs scalaires de ron.daily.production. Pour ces lignes :
      - product_id, product_tmpl_id, product_category_id, product_uom_id sont NULL
      - weight_kg = 0 (emballages comptés en unités, films déjà en kg via quantity)
      - id est négatif (ID synthétique stable, dérivé de daily_production_id)
    """
    _inherit = 'ron.consumption.analysis'

    consumption_category = fields.Selection(
        [
            ('raw_material', 'Matière Première'),
            ('packaging', 'Emballage'),
            ('film', 'Film'),
            ('scrap_recoverable', 'Rebut Récupérable'),
            ('paste_recoverable', 'Pâte Récupérable'),
        ],
        string='Catégorie de Consommation',
        readonly=True,
    )

    consumption_subtype = fields.Char(
        string='Sous-type',
        readonly=True,
        help="Libellé pour les emballages/films (ex: 'Emballage SOLO'). "
             "Vide pour les matières premières.",
    )

    def _select_raw_material(self):
        """Bloc SELECT pour les matières premières (lignes ron_consumption_line)."""
        return """
            SELECT
                cl.id                                    AS id,
                cl.daily_production_id                   AS production_id,
                dp.production_date                       AS production_date,
                dp.production_type                       AS production_type,
                dp.state                                 AS production_state,
                cl.product_id                            AS product_id,
                pp.product_tmpl_id                       AS product_tmpl_id,
                pt.categ_id                              AS product_category_id,
                pt.uom_id                                AS product_uom_id,
                dp.company_id                            AS company_id,
                rc.currency_id                           AS currency_id,
                COALESCE(cl.quantity, 0.0)               AS quantity,
                COALESCE(cl.weight_kg, 0.0)              AS weight_kg,
                COALESCE(cl.unit_cost, 0.0)              AS unit_cost,
                COALESCE(cl.total_cost, 0.0)             AS total_cost,
                COALESCE(dp.total_cartons_produced, 0.0) AS total_cartons_produced,
                COALESCE(dp.qty_solo_cartons, 0.0)       AS qty_solo_cartons,
                COALESCE(dp.qty_classico_cartons, 0.0)   AS qty_classico_cartons,
                COALESCE(dp.qty_sandwich_cartons, 0.0)   AS qty_sandwich_cartons,
                CASE
                    WHEN COALESCE(dp.total_cartons_produced, 0.0) > 0
                    THEN COALESCE(cl.weight_kg, 0.0) / dp.total_cartons_produced
                    ELSE 0.0
                END                                      AS consumption_per_carton,
                'raw_material'                           AS consumption_category,
                NULL::varchar                            AS consumption_subtype
            FROM ron_consumption_line cl
            JOIN ron_daily_production dp ON dp.id = cl.daily_production_id
            JOIN product_product pp      ON pp.id = cl.product_id
            JOIN product_template pt     ON pt.id = pp.product_tmpl_id
            JOIN res_company rc          ON rc.id = dp.company_id
        """

    def _select_packaging_source(self, offset_id, category, label,
                                 qty_field, unit_cost_field, cost_field):
        """Bloc SELECT synthétique pour un type d'emballage/film.

        Ne retourne une ligne que si la quantité saisie est > 0
        (évite de polluer la vue avec des productions sans emballage).
        """
        return f"""
            SELECT
                -(dp.id * 100 + {offset_id})             AS id,
                dp.id                                    AS production_id,
                dp.production_date                       AS production_date,
                dp.production_type                       AS production_type,
                dp.state                                 AS production_state,
                NULL::int4                               AS product_id,
                NULL::int4                               AS product_tmpl_id,
                NULL::int4                               AS product_category_id,
                NULL::int4                               AS product_uom_id,
                dp.company_id                            AS company_id,
                rc.currency_id                           AS currency_id,
                COALESCE(dp.{qty_field}, 0.0)            AS quantity,
                0.0                                      AS weight_kg,
                COALESCE(dp.{unit_cost_field}, 0.0)      AS unit_cost,
                COALESCE(dp.{cost_field}, 0.0)           AS total_cost,
                COALESCE(dp.total_cartons_produced, 0.0) AS total_cartons_produced,
                COALESCE(dp.qty_solo_cartons, 0.0)       AS qty_solo_cartons,
                COALESCE(dp.qty_classico_cartons, 0.0)   AS qty_classico_cartons,
                COALESCE(dp.qty_sandwich_cartons, 0.0)   AS qty_sandwich_cartons,
                0.0                                      AS consumption_per_carton,
                '{category}'                             AS consumption_category,
                '{label}'                                AS consumption_subtype
            FROM ron_daily_production dp
            JOIN res_company rc ON rc.id = dp.company_id
            WHERE COALESCE(dp.{qty_field}, 0.0) > 0
        """

    def _select_recoverable_source(self, offset_id, scrap_type, category, label):
        """Bloc SELECT pour les rebuts/pâte récupérables (lignes ron_scrap_line).

        product_id est volontairement NULL : la boucle parente du wizard
        (`_prepare_report_data`) ignore les lignes sans product_id, ce qui
        empêche la pollution des totaux MP par les valeurs récupérables.
        L'agrégation détaillée se fait via _prepare_recoverable_lines() qui
        interroge directement ron.scrap.line pour conserver l'info produit.
        """
        return f"""
            SELECT
                -(sl.id * 100 + {offset_id})             AS id,
                sl.daily_production_id                   AS production_id,
                dp.production_date                       AS production_date,
                dp.production_type                       AS production_type,
                dp.state                                 AS production_state,
                NULL::int4                               AS product_id,
                NULL::int4                               AS product_tmpl_id,
                NULL::int4                               AS product_category_id,
                NULL::int4                               AS product_uom_id,
                dp.company_id                            AS company_id,
                rc.currency_id                           AS currency_id,
                COALESCE(sl.weight_kg, 0.0)              AS quantity,
                COALESCE(sl.weight_kg, 0.0)              AS weight_kg,
                COALESCE(sl.cost_per_kg, 0.0)            AS unit_cost,
                COALESCE(sl.total_cost, 0.0)             AS total_cost,
                COALESCE(dp.total_cartons_produced, 0.0) AS total_cartons_produced,
                COALESCE(dp.qty_solo_cartons, 0.0)       AS qty_solo_cartons,
                COALESCE(dp.qty_classico_cartons, 0.0)   AS qty_classico_cartons,
                COALESCE(dp.qty_sandwich_cartons, 0.0)   AS qty_sandwich_cartons,
                0.0                                      AS consumption_per_carton,
                '{category}'                             AS consumption_category,
                '{label}'                                AS consumption_subtype
            FROM ron_scrap_line sl
            JOIN ron_daily_production dp ON dp.id = sl.daily_production_id
            JOIN res_company rc          ON rc.id = dp.company_id
            WHERE sl.scrap_type = '{scrap_type}'
              AND COALESCE(sl.weight_kg, 0.0) > 0
        """

    def init(self):
        """Recrée la vue SQL avec UNION ALL : 1 bloc MP + 6 emballage/film + 2 récupérables."""
        tools.drop_view_if_exists(self.env.cr, self._table)

        unions = [self._select_raw_material()]
        for source in _PACKAGING_SOURCES:
            unions.append(self._select_packaging_source(*source))
        for source in _RECOVERABLE_SOURCES:
            unions.append(self._select_recoverable_source(*source))

        sql = "CREATE OR REPLACE VIEW %s AS (\n%s\n)" % (
            self._table,
            "\nUNION ALL\n".join(unions),
        )
        self.env.cr.execute(sql)
