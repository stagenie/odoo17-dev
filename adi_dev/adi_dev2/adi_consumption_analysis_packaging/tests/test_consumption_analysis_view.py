# -*- coding: utf-8 -*-
"""
Tests de la vue SQL ron.consumption.analysis étendue par emballages/films.

Vérifie que le UNION ALL produit les bonnes lignes :
  - Les lignes MP (raw_material) restent inchangées
  - Les lignes synthétiques emballage/film n'apparaissent que si qty > 0
  - Les IDs négatifs synthétiques sont stables et sans collision

Lancement :
  ./odoo-bin -c odoo17.conf -d <db> -i adi_consumption_analysis_packaging \\
      --test-enable --test-tags adi_consumption_analysis_packaging --stop-after-init
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('adi_consumption_analysis_packaging', 'post_install', '-at_install')
class TestConsumptionAnalysisView(TransactionCase):
    """Tests d'intégration de la vue SQL avec emballages et films."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Désactiver le tracking mail pour accélérer les fixtures
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Produit de type 'product' requis pour ron.consumption.line
        cls.product = cls.env['product.product'].create({
            'name': 'Farine Test 25KG',
            'type': 'product',
            'standard_price': 2.5,
        })

        # Production de référence — tous les tests créent des productions
        # additionnelles dans leur propre corps pour l'isolation.
        cls.company = cls.env.company

    def _make_production(self, date='2026-01-15', production_type='solo_classico', **kwargs):
        """Crée une ron.daily.production minimale.

        :param date: Date de production (str YYYY-MM-DD)
        :param production_type: 'solo_classico' ou 'sandwich_gf'
        :param kwargs: Champs supplémentaires transmis directement au create
        :returns: ron.daily.production record
        """
        vals = {
            'production_date': date,
            'production_type': production_type,
            'company_id': self.company.id,
        }
        vals.update(kwargs)
        return self.env['ron.daily.production'].create(vals)

    def _make_consumption_line(self, production, qty=10.0, weight_per_unit=25.0, unit_cost=2.5):
        """Crée une ligne de consommation MP rattachée à une production.

        :param production: ron.daily.production record
        :param qty: Quantité consommée
        :param weight_per_unit: Poids par unité (kg)
        :param unit_cost: Coût unitaire
        :returns: ron.consumption.line record
        """
        return self.env['ron.consumption.line'].create({
            'daily_production_id': production.id,
            'product_id': self.product.id,
            'quantity': qty,
            'weight_per_unit': weight_per_unit,
            'unit_cost': unit_cost,
        })

    def _make_scrap_line(self, production, scrap_type='scrap_recoverable',
                         weight_kg=15.0, cost_per_kg=120.0, product=None):
        """Crée une ligne ron.scrap.line rattachée à une production.

        :param production: ron.daily.production record
        :param scrap_type: 'scrap_recoverable' ou 'paste_recoverable'
        :param weight_kg: Poids du rebut/pâte (>0)
        :param cost_per_kg: Coût par kg
        :param product: product.product (optionnel — pour paste_recoverable
            le default_get peut le forcer via la config)
        :returns: ron.scrap.line record
        """
        vals = {
            'daily_production_id': production.id,
            'scrap_type': scrap_type,
            'weight_kg': weight_kg,
            'cost_per_kg': cost_per_kg,
        }
        if product is not None:
            vals['product_id'] = product.id
        return self.env['ron.scrap.line'].create(vals)

    # ------------------------------------------------------------------
    # Test 1 : régression MP — la ligne raw_material reste bien présente
    # ------------------------------------------------------------------
    def test_mp_row_appears_with_raw_material_category(self):
        """Une ligne MP doit apparaître avec consumption_category='raw_material'.

        Vérifie également que product_id est renseigné et que
        consumption_subtype est vide (NULL rendu False par Odoo).
        """
        prod = self._make_production(date='2026-01-10')
        line = self._make_consumption_line(prod, qty=5.0, weight_per_unit=25.0, unit_cost=3.0)

        Analysis = self.env['ron.consumption.analysis']
        rows = Analysis.search([('production_id', '=', prod.id)])

        # Filtrer uniquement les lignes MP (pas d'éventuelles lignes emballage)
        mp_rows = rows.filtered(lambda r: r.consumption_category == 'raw_material')
        self.assertTrue(mp_rows, "Aucune ligne 'raw_material' trouvée dans la vue")

        row = mp_rows[0]
        self.assertEqual(row.consumption_category, 'raw_material',
                         "La catégorie doit être 'raw_material' pour une ligne MP")
        self.assertFalse(row.consumption_subtype,
                         "consumption_subtype doit être vide (NULL) pour une ligne MP")
        self.assertTrue(row.product_id,
                        "product_id doit être renseigné pour une ligne MP")
        self.assertEqual(row.product_id.id, self.product.id,
                         "product_id doit correspondre au produit de la ligne de consommation")
        # L'ID doit être positif (issu de ron_consumption_line.id)
        self.assertGreater(row.id, 0, "L'ID d'une ligne MP doit être positif")

    # ------------------------------------------------------------------
    # Test 2 : ligne emballage apparaît si qty > 0
    # ------------------------------------------------------------------
    def test_packaging_row_appears_when_qty_positive(self):
        """Une ligne synthétique Emballage SOLO doit être visible si qty > 0.

        Vérifie : category='packaging', subtype='Emballage SOLO',
        quantity et total_cost corrects, product_id absent, id négatif.
        """
        prod = self._make_production(
            date='2026-01-11',
            emballage_solo_qty=100.0,
            emballage_solo_unit_cost=35.0,
        )
        # Forcer le recalcul du champ stocké emballage_solo_cost
        prod._compute_packaging_costs()

        Analysis = self.env['ron.consumption.analysis']
        rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', '=', 'packaging'),
            ('consumption_subtype', '=', 'Emballage SOLO'),
        ])

        self.assertEqual(len(rows), 1,
                         "Exactement 1 ligne synthétique 'Emballage SOLO' attendue")
        row = rows[0]
        self.assertEqual(row.consumption_category, 'packaging')
        self.assertEqual(row.consumption_subtype, 'Emballage SOLO')
        self.assertAlmostEqual(row.quantity, 100.0, places=2,
                               msg="quantity doit valoir 100")
        self.assertAlmostEqual(row.total_cost, 100.0 * 35.0, places=2,
                               msg="total_cost doit valoir qty × unit_cost = 3500")
        self.assertFalse(row.product_id,
                         "product_id doit être NULL pour une ligne synthétique")
        self.assertLess(row.id, 0, "L'ID d'une ligne synthétique doit être négatif")

    # ------------------------------------------------------------------
    # Test 3 : zéro-qty → pas de ligne emballage dans la vue
    # ------------------------------------------------------------------
    def test_zero_qty_packaging_excluded_from_view(self):
        """Une production sans aucun emballage ne doit produire aucune ligne packaging/film."""
        prod = self._make_production(date='2026-01-12')
        # Pas de ligne MP non plus (on teste uniquement l'absence d'emballages)

        Analysis = self.env['ron.consumption.analysis']
        pkg_rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', 'in', ('packaging', 'film')),
        ])

        self.assertFalse(pkg_rows,
                         "Aucune ligne emballage/film ne doit apparaître quand toutes "
                         "les qtés sont nulles")

    # ------------------------------------------------------------------
    # Test 4 : plusieurs types d'emballage sur une même production
    # ------------------------------------------------------------------
    def test_multiple_packaging_types_produce_distinct_rows(self):
        """Deux types d'emballage > 0 sur une même production → 2 lignes distinctes."""
        prod = self._make_production(
            date='2026-01-13',
            emballage_solo_qty=50.0,
            emballage_solo_unit_cost=30.0,
            film_classico_qty=10.0,
            film_classico_unit_cost=8.0,
        )
        prod._compute_packaging_costs()

        Analysis = self.env['ron.consumption.analysis']
        pkg_rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', 'in', ('packaging', 'film')),
        ])

        self.assertEqual(len(pkg_rows), 2,
                         "Exactement 2 lignes synthétiques attendues "
                         "(Emballage SOLO + Film CLASSICO)")

        subtypes = pkg_rows.mapped('consumption_subtype')
        self.assertIn('Emballage SOLO', subtypes,
                      "La ligne 'Emballage SOLO' doit être présente")
        self.assertIn('Film CLASSICO', subtypes,
                      "La ligne 'Film CLASSICO' doit être présente")

        # Vérification des catégories distinctes
        solo_row = pkg_rows.filtered(lambda r: r.consumption_subtype == 'Emballage SOLO')
        film_row = pkg_rows.filtered(lambda r: r.consumption_subtype == 'Film CLASSICO')
        self.assertEqual(solo_row.consumption_category, 'packaging')
        self.assertEqual(film_row.consumption_category, 'film')

    # ------------------------------------------------------------------
    # Test 5 : unicité des IDs négatifs entre productions et offsets
    # ------------------------------------------------------------------
    def test_synthetic_ids_are_unique_across_productions(self):
        """Les IDs négatifs de deux productions différentes ne doivent pas collisionner.

        Formule : id = -(dp.id * 100 + offset)
        Ce test vérifie empiriquement l'absence de doublon sur 2 productions.
        """
        prod_a = self._make_production(
            date='2026-01-14',
            emballage_solo_qty=1.0,
            emballage_solo_unit_cost=10.0,
            emballage_classico_qty=1.0,
            emballage_classico_unit_cost=10.0,
        )
        prod_b = self._make_production(
            date='2026-01-15',
            emballage_solo_qty=1.0,
            emballage_solo_unit_cost=10.0,
            film_solo_qty=1.0,
            film_solo_unit_cost=10.0,
        )
        prod_a._compute_packaging_costs()
        prod_b._compute_packaging_costs()

        Analysis = self.env['ron.consumption.analysis']
        rows_a = Analysis.search([
            ('production_id', '=', prod_a.id),
            ('consumption_category', 'in', ('packaging', 'film')),
        ])
        rows_b = Analysis.search([
            ('production_id', '=', prod_b.id),
            ('consumption_category', 'in', ('packaging', 'film')),
        ])

        ids_a = set(rows_a.mapped('id'))
        ids_b = set(rows_b.mapped('id'))

        # Toutes les IDs doivent être négatives
        self.assertTrue(all(i < 0 for i in ids_a),
                        "Tous les IDs synthétiques de prod_a doivent être négatifs")
        self.assertTrue(all(i < 0 for i in ids_b),
                        "Tous les IDs synthétiques de prod_b doivent être négatifs")

        # Pas de collision entre les deux productions
        collision = ids_a & ids_b
        self.assertFalse(collision,
                         f"Collision d'IDs synthétiques détectée entre prod_a et prod_b : "
                         f"{collision}")

    # ------------------------------------------------------------------
    # Test 6 : ligne Rebut Récupérable apparaît dans la vue
    # ------------------------------------------------------------------
    def test_scrap_recoverable_row_appears(self):
        """Une ligne ron.scrap.line de type scrap_recoverable doit apparaître
        avec consumption_category='scrap_recoverable' et subtype='Rebut Récupérable'.

        product_id doit être NULL dans la vue (même logique que packaging).
        """
        prod = self._make_production(date='2026-01-16')
        self._make_scrap_line(
            prod,
            scrap_type='scrap_recoverable',
            weight_kg=20.0,
            cost_per_kg=150.0,
            product=self.product,
        )

        Analysis = self.env['ron.consumption.analysis']
        rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', '=', 'scrap_recoverable'),
        ])

        self.assertEqual(len(rows), 1, "1 ligne 'scrap_recoverable' attendue")
        row = rows[0]
        self.assertEqual(row.consumption_subtype, 'Rebut Récupérable')
        self.assertAlmostEqual(row.weight_kg, 20.0, places=2)
        self.assertAlmostEqual(row.unit_cost, 150.0, places=2)
        self.assertAlmostEqual(row.total_cost, 20.0 * 150.0, places=2)
        self.assertFalse(row.product_id,
                         "product_id doit être NULL dans la vue (info conservée "
                         "côté ron.scrap.line)")
        self.assertLess(row.id, 0, "L'ID synthétique scrap doit être négatif")

    # ------------------------------------------------------------------
    # Test 7 : ligne Pâte Récupérable apparaît dans la vue
    # ------------------------------------------------------------------
    def test_paste_recoverable_row_appears(self):
        """Une ligne ron.scrap.line de type paste_recoverable doit apparaître
        avec consumption_category='paste_recoverable' et subtype='Pâte Récupérable'.
        """
        prod = self._make_production(date='2026-01-17')
        self._make_scrap_line(
            prod,
            scrap_type='paste_recoverable',
            weight_kg=12.5,
            cost_per_kg=80.0,
            product=self.product,  # produit explicite pour éviter la dépendance config
        )

        Analysis = self.env['ron.consumption.analysis']
        rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', '=', 'paste_recoverable'),
        ])

        self.assertEqual(len(rows), 1, "1 ligne 'paste_recoverable' attendue")
        row = rows[0]
        self.assertEqual(row.consumption_subtype, 'Pâte Récupérable')
        self.assertAlmostEqual(row.weight_kg, 12.5, places=2)
        self.assertAlmostEqual(row.total_cost, 12.5 * 80.0, places=2)

    # ------------------------------------------------------------------
    # Test 8 : zéro-poids → pas de ligne récupérable dans la vue
    # ------------------------------------------------------------------
    def test_zero_weight_scrap_excluded_from_view(self):
        """Le filtre WHERE weight_kg > 0 doit exclure les lignes vides.

        Note : ron.scrap.line a un constraint weight_kg > 0, donc ce test
        valide le filtre SQL via une production sans aucune ligne scrap
        (pas de ligne récupérable créée → pas de ligne dans la vue).
        """
        prod = self._make_production(date='2026-01-18')

        Analysis = self.env['ron.consumption.analysis']
        rec_rows = Analysis.search([
            ('production_id', '=', prod.id),
            ('consumption_category', 'in', ('scrap_recoverable', 'paste_recoverable')),
        ])

        self.assertFalse(rec_rows,
                         "Aucune ligne récupérable ne doit apparaître sans scrap line")

    # ------------------------------------------------------------------
    # Test 9 : non-collision IDs scrap vs IDs packaging vs IDs MP
    # ------------------------------------------------------------------
    def test_scrap_ids_disjoint_from_packaging_and_mp_ids(self):
        """Les offsets scrap {50, 51} sont disjoints de packaging {10..22} ;
        sl.id et dp.id étant indépendants, aucune collision possible côté SQL.

        On valide en pratique en mélangeant les 3 sources sur la même prod.
        """
        prod = self._make_production(
            date='2026-01-19',
            emballage_solo_qty=10.0,
            emballage_solo_unit_cost=20.0,
            film_solo_qty=5.0,
            film_solo_unit_cost=15.0,
        )
        prod._compute_packaging_costs()
        self._make_consumption_line(prod, qty=3.0, weight_per_unit=10.0, unit_cost=4.0)
        self._make_scrap_line(prod, scrap_type='scrap_recoverable',
                              weight_kg=8.0, cost_per_kg=100.0, product=self.product)
        self._make_scrap_line(prod, scrap_type='paste_recoverable',
                              weight_kg=4.0, cost_per_kg=60.0, product=self.product)

        Analysis = self.env['ron.consumption.analysis']
        rows = Analysis.search([('production_id', '=', prod.id)])
        all_ids = rows.mapped('id')

        # Unicité sur l'ensemble (MP positif, packaging négatif {10..22},
        # scrap négatif {50, 51})
        self.assertEqual(len(all_ids), len(set(all_ids)),
                         f"Collision d'IDs détectée parmi les sources mélangées : "
                         f"{all_ids}")

        # Vérifier qu'on a bien les 5 catégories : MP + packaging + film
        # + scrap + paste
        categories = set(rows.mapped('consumption_category'))
        self.assertEqual(
            categories,
            {'raw_material', 'packaging', 'film', 'scrap_recoverable', 'paste_recoverable'},
            f"Catégories attendues incomplètes — obtenu {categories}",
        )
