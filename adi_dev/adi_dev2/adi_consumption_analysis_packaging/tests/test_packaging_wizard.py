# -*- coding: utf-8 -*-
"""
Tests du wizard ron.print.consumption.report.wizard étendu.

Couverture :
  - _build_domain() selon content_scope (all / raw_material / packaging_only)
  - _prepare_packaging_lines() : agrégation, coût moyen pondéré, tri
  - _prepare_report_data() : clés attendues pour chaque scope
  - _onchange_content_scope : packaging_only force include_mp_per_finished=False

Lancement :
  ./odoo-bin -c odoo17.conf -d <db> -i adi_consumption_analysis_packaging \\
      --test-enable --test-tags adi_consumption_analysis_packaging --stop-after-init
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('adi_consumption_analysis_packaging', 'post_install', '-at_install')
class TestPackagingWizard(TransactionCase):
    """Tests du wizard d'impression avec gestion de la portée (scope)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Désactiver le tracking mail pour alléger les fixtures
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        # Produit MP pour les lignes de consommation
        cls.product = cls.env['product.product'].create({
            'name': 'Sucre Test 50KG',
            'type': 'product',
            'standard_price': 1.8,
        })

        # --- Production A : 15 janvier 2026 ---
        cls.prod_a = cls.env['ron.daily.production'].create({
            'production_date': '2026-01-15',
            'production_type': 'solo_classico',
            'company_id': cls.company.id,
            'emballage_solo_qty': 200.0,
            'emballage_solo_unit_cost': 40.0,
            'film_classico_qty': 20.0,
            'film_classico_unit_cost': 12.0,
        })
        cls.prod_a._compute_packaging_costs()

        # Ligne MP sur prod_a
        cls.env['ron.consumption.line'].create({
            'daily_production_id': cls.prod_a.id,
            'product_id': cls.product.id,
            'quantity': 10.0,
            'weight_per_unit': 50.0,
            'unit_cost': 1.8,
        })

        # --- Production B : 20 janvier 2026 ---
        cls.prod_b = cls.env['ron.daily.production'].create({
            'production_date': '2026-01-20',
            'production_type': 'solo_classico',
            'company_id': cls.company.id,
            'emballage_solo_qty': 100.0,
            'emballage_solo_unit_cost': 42.0,
            'film_classico_qty': 10.0,
            'film_classico_unit_cost': 12.0,
        })
        cls.prod_b._compute_packaging_costs()

        # Ligne MP sur prod_b
        cls.env['ron.consumption.line'].create({
            'daily_production_id': cls.prod_b.id,
            'product_id': cls.product.id,
            'quantity': 8.0,
            'weight_per_unit': 50.0,
            'unit_cost': 1.8,
        })

        # --- Scrap/paste sur prod_a et prod_b (couvrent les 2 types) ---
        # Rebut récupérable sur prod_a : 10kg × 100 = 1000
        cls.env['ron.scrap.line'].create({
            'daily_production_id': cls.prod_a.id,
            'scrap_type': 'scrap_recoverable',
            'product_id': cls.product.id,
            'weight_kg': 10.0,
            'cost_per_kg': 100.0,
        })
        # Rebut récupérable sur prod_b : 5kg × 110 = 550
        cls.env['ron.scrap.line'].create({
            'daily_production_id': cls.prod_b.id,
            'scrap_type': 'scrap_recoverable',
            'product_id': cls.product.id,
            'weight_kg': 5.0,
            'cost_per_kg': 110.0,
        })
        # Pâte récupérable sur prod_a : 4kg × 50 = 200
        cls.env['ron.scrap.line'].create({
            'daily_production_id': cls.prod_a.id,
            'scrap_type': 'paste_recoverable',
            'product_id': cls.product.id,
            'weight_kg': 4.0,
            'cost_per_kg': 50.0,
        })

    def _make_wizard(self, scope='all', date_from='2026-01-01', date_to='2026-01-31',
                     production_type='all', compute_net_cost=True):
        """Instancie le wizard avec les paramètres donnés.

        :param scope: 'all', 'raw_material', 'packaging_only', 'recoverables_only'
        :param date_from: Date début (str YYYY-MM-DD)
        :param date_to: Date fin (str YYYY-MM-DD)
        :param production_type: 'all', 'solo_classico' ou 'sandwich_gf'
        :param compute_net_cost: bool, si True le rapport en mode 'all' déduit
            les récupérables du grand total
        :returns: ron.print.consumption.report.wizard record (TransientModel)
        """
        return self.env['ron.print.consumption.report.wizard'].create({
            'date_from': date_from,
            'date_to': date_to,
            'production_type': production_type,
            'company_id': self.company.id,
            'content_scope': scope,
            'include_mp_per_finished': True,
            'compute_net_cost': compute_net_cost,
        })

    # ------------------------------------------------------------------
    # Test 1 : _build_domain() selon le scope
    # ------------------------------------------------------------------
    def test_build_domain_scope_all(self):
        """Scope 'all' ne doit ajouter aucun filtre consumption_category."""
        wizard = self._make_wizard(scope='all')
        domain = wizard._build_domain()

        # Aucun filtre catégorie attendu
        category_filters = [
            t for t in domain
            if isinstance(t, (list, tuple)) and t[0] == 'consumption_category'
        ]
        self.assertFalse(category_filters,
                         "Le scope 'all' ne doit pas filtrer sur consumption_category")

    def test_build_domain_scope_raw_material(self):
        """Scope 'raw_material' doit ajouter ('consumption_category', '=', 'raw_material')."""
        wizard = self._make_wizard(scope='raw_material')
        domain = wizard._build_domain()

        raw_filter = [
            t for t in domain
            if isinstance(t, (list, tuple))
            and t[0] == 'consumption_category'
            and t[1] == '='
            and t[2] == 'raw_material'
        ]
        self.assertEqual(len(raw_filter), 1,
                         "Un filtre consumption_category='raw_material' attendu")

    def test_build_domain_scope_packaging_only(self):
        """Scope 'packaging_only' doit filtrer sur ('packaging', 'film')."""
        wizard = self._make_wizard(scope='packaging_only')
        domain = wizard._build_domain()

        pkg_filter = [
            t for t in domain
            if isinstance(t, (list, tuple))
            and t[0] == 'consumption_category'
            and t[1] == 'in'
        ]
        self.assertEqual(len(pkg_filter), 1,
                         "Un filtre consumption_category in (...) attendu")
        expected_values = set(pkg_filter[0][2])
        self.assertEqual(expected_values, {'packaging', 'film'},
                         "Le filtre doit inclure 'packaging' et 'film'")

    # ------------------------------------------------------------------
    # Test 2 : _prepare_packaging_lines() — agrégation et coût moyen pondéré
    # ------------------------------------------------------------------
    def test_prepare_packaging_lines_aggregation(self):
        """_prepare_packaging_lines doit agréger par sous-type sur la période.

        Emballage SOLO :
          prod_a : 200 u × 40 = 8000
          prod_b : 100 u × 42 = 4200
          → total qty=300, total_cost=12200, unit_cost=12200/300 ≈ 40.67

        Film CLASSICO :
          prod_a : 20 kg × 12 = 240
          prod_b : 10 kg × 12 = 120
          → total qty=30, total_cost=360, unit_cost=12.0
        """
        wizard = self._make_wizard(scope='all')
        lines, total_cost, total_qty = wizard._prepare_packaging_lines()

        self.assertTrue(lines, "La liste de lignes emballage ne doit pas être vide")

        # Indexer par sous-type pour faciliter les assertions
        by_subtype = {l['subtype']: l for l in lines}

        self.assertIn('Emballage SOLO', by_subtype,
                      "'Emballage SOLO' doit figurer dans les lignes")
        self.assertIn('Film CLASSICO', by_subtype,
                      "'Film CLASSICO' doit figurer dans les lignes")

        solo = by_subtype['Emballage SOLO']
        self.assertAlmostEqual(solo['quantity'], 300.0, places=2,
                               msg="Quantité SOLO : 200 + 100 = 300")
        self.assertAlmostEqual(solo['total_cost'], 12200.0, places=2,
                               msg="Coût SOLO : 8000 + 4200 = 12 200")
        expected_unit_cost_solo = 12200.0 / 300.0
        self.assertAlmostEqual(solo['unit_cost'], expected_unit_cost_solo, places=2,
                               msg="unit_cost SOLO = total_cost / qty (coût moyen pondéré)")

        film = by_subtype['Film CLASSICO']
        self.assertAlmostEqual(film['quantity'], 30.0, places=2,
                               msg="Quantité Film CLASSICO : 20 + 10 = 30")
        self.assertAlmostEqual(film['total_cost'], 360.0, places=2,
                               msg="Coût Film CLASSICO : 240 + 120 = 360")
        self.assertAlmostEqual(film['unit_cost'], 12.0, places=2,
                               msg="unit_cost Film CLASSICO = 360 / 30 = 12.0")

        # Vérification du total retourné
        self.assertAlmostEqual(total_cost, 12200.0 + 360.0, places=2,
                               msg="total_cost global doit être la somme des sous-totaux")

    def test_prepare_packaging_lines_sort_order(self):
        """Les lignes doivent être triées par (catégorie, sous-type)."""
        wizard = self._make_wizard(scope='all')
        lines, _, _ = wizard._prepare_packaging_lines()

        if len(lines) > 1:
            sort_keys = [(l['category'], l['subtype']) for l in lines]
            self.assertEqual(sort_keys, sorted(sort_keys),
                             "Les lignes doivent être triées par catégorie puis sous-type")

    # ------------------------------------------------------------------
    # Test 3 : _prepare_report_data() — mode 'all'
    # ------------------------------------------------------------------
    def test_prepare_report_data_mode_all(self):
        """Mode 'all' : data contient lines MP et packaging_lines, show_* = True."""
        wizard = self._make_wizard(scope='all')
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertTrue(data.get('show_raw_material'),
                        "show_raw_material doit être True en mode 'all'")
        self.assertTrue(data.get('show_packaging'),
                        "show_packaging doit être True en mode 'all'")
        self.assertTrue(data.get('lines'),
                        "lines (MP) ne doit pas être vide en mode 'all'")
        self.assertTrue(data.get('packaging_lines') is not None,
                        "packaging_lines doit être présent en mode 'all'")
        self.assertTrue(data.get('packaging_lines'),
                        "packaging_lines ne doit pas être vide (des emballages existent)")

        # combined_total_cost = grand_total_cost + packaging_total_cost
        expected_combined = (data.get('grand_total_cost') or 0.0) + (
            data.get('packaging_total_cost') or 0.0
        )
        self.assertAlmostEqual(
            data.get('combined_total_cost'), expected_combined, places=2,
            msg="combined_total_cost doit être grand_total_cost + packaging_total_cost",
        )

    # ------------------------------------------------------------------
    # Test 4 : _prepare_report_data() — mode 'raw_material'
    # ------------------------------------------------------------------
    def test_prepare_report_data_mode_raw_material(self):
        """Mode 'raw_material' : packaging_lines vide, show_packaging=False."""
        wizard = self._make_wizard(scope='raw_material')
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertTrue(data.get('show_raw_material'),
                        "show_raw_material doit être True en mode 'raw_material'")
        self.assertFalse(data.get('show_packaging'),
                         "show_packaging doit être False en mode 'raw_material'")
        self.assertEqual(data.get('packaging_lines'), [],
                         "packaging_lines doit être [] en mode 'raw_material'")
        self.assertEqual(data.get('packaging_total_cost'), 0.0,
                         "packaging_total_cost doit être 0 en mode 'raw_material'")
        self.assertEqual(
            data.get('content_scope'), 'raw_material',
            "content_scope doit être 'raw_material' dans data",
        )

    # ------------------------------------------------------------------
    # Test 5 : _prepare_report_data() — mode 'packaging_only'
    # ------------------------------------------------------------------
    def test_prepare_report_data_mode_packaging_only(self):
        """Mode 'packaging_only' : lines MP vidées, show_raw_material=False."""
        wizard = self._make_wizard(scope='packaging_only')
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertFalse(data.get('show_raw_material'),
                         "show_raw_material doit être False en mode 'packaging_only'")
        self.assertTrue(data.get('show_packaging'),
                        "show_packaging doit être True en mode 'packaging_only'")
        self.assertEqual(data.get('lines'), [],
                         "lines (MP) doit être [] en mode 'packaging_only'")
        self.assertEqual(data.get('grand_total_cost'), 0.0,
                         "grand_total_cost MP doit être 0 en mode 'packaging_only'")
        self.assertTrue(data.get('packaging_lines'),
                        "packaging_lines ne doit pas être vide en mode 'packaging_only'")

        # combined_total_cost = packaging uniquement
        pkg_cost = data.get('packaging_total_cost') or 0.0
        self.assertAlmostEqual(
            data.get('combined_total_cost'), pkg_cost, places=2,
            msg="combined_total_cost doit égaler packaging_total_cost en mode 'packaging_only'",
        )
        self.assertEqual(
            data.get('content_scope'), 'packaging_only',
            "content_scope doit être 'packaging_only' dans data",
        )

    # ------------------------------------------------------------------
    # Test 6 : _onchange_content_scope force include_mp_per_finished=False
    # ------------------------------------------------------------------
    def test_onchange_packaging_only_disables_mp_per_finished(self):
        """Passer en packaging_only doit forcer include_mp_per_finished à False."""
        # Créer un wizard via new() pour que l'onchange soit disponible
        wizard = self.env['ron.print.consumption.report.wizard'].new({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
            'company_id': self.company.id,
            'content_scope': 'all',
            'include_mp_per_finished': True,
        })

        # Simuler le passage en packaging_only comme le ferait l'interface
        wizard.content_scope = 'packaging_only'
        wizard._onchange_content_scope()

        self.assertFalse(wizard.include_mp_per_finished,
                         "include_mp_per_finished doit être False après passage "
                         "en 'packaging_only'")

    def test_onchange_raw_material_leaves_mp_per_finished_unchanged(self):
        """Passer en 'raw_material' ne doit pas modifier include_mp_per_finished."""
        wizard = self.env['ron.print.consumption.report.wizard'].new({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
            'company_id': self.company.id,
            'content_scope': 'all',
            'include_mp_per_finished': True,
        })

        wizard.content_scope = 'raw_material'
        wizard._onchange_content_scope()

        self.assertTrue(wizard.include_mp_per_finished,
                        "include_mp_per_finished ne doit pas être modifié pour "
                        "un scope autre que 'packaging_only'")

    # ==================================================================
    # Récupérables (Rebuts + Pâte) — scope, agrégation, coût net
    # ==================================================================

    def test_build_domain_scope_recoverables_only(self):
        """Scope 'recoverables_only' : domain doit contenir un filtre
        consumption_category in (scrap_recoverable, paste_recoverable).
        """
        wizard = self._make_wizard(scope='recoverables_only')
        domain = wizard._build_domain()

        rec_filter = [
            t for t in domain
            if isinstance(t, (list, tuple))
            and t[0] == 'consumption_category'
            and t[1] == 'in'
        ]
        self.assertEqual(len(rec_filter), 1,
                         "Un filtre consumption_category in (...) attendu")
        expected = set(rec_filter[0][2])
        self.assertEqual(expected, {'scrap_recoverable', 'paste_recoverable'},
                         "Le filtre doit cibler scrap_recoverable + paste_recoverable")

    def test_prepare_recoverable_lines_aggregation(self):
        """_prepare_recoverable_lines agrège par (scrap_type, product_id).

        Données fixtures :
          Rebut récupérable, produit X :
            prod_a : 10 kg × 100 = 1000
            prod_b : 5 kg × 110 = 550
            → 15 kg, 1550, cost_per_kg = 1550/15 ≈ 103.33
          Pâte récupérable, produit X :
            prod_a : 4 kg × 50 = 200
            → 4 kg, 200, cost_per_kg = 50
        """
        wizard = self._make_wizard(scope='all')
        lines, total_cost, total_weight = wizard._prepare_recoverable_lines()

        self.assertEqual(len(lines), 2,
                         "2 lignes attendues : 1 rebut + 1 pâte (1 seul produit)")

        by_type = {l['scrap_type']: l for l in lines}
        self.assertIn('scrap_recoverable', by_type)
        self.assertIn('paste_recoverable', by_type)

        scrap = by_type['scrap_recoverable']
        self.assertAlmostEqual(scrap['weight_kg'], 15.0, places=2)
        self.assertAlmostEqual(scrap['total_cost'], 1550.0, places=2)
        self.assertAlmostEqual(scrap['cost_per_kg'], 1550.0 / 15.0, places=2)

        paste = by_type['paste_recoverable']
        self.assertAlmostEqual(paste['weight_kg'], 4.0, places=2)
        self.assertAlmostEqual(paste['total_cost'], 200.0, places=2)
        self.assertAlmostEqual(paste['cost_per_kg'], 50.0, places=2)

        # Totaux globaux
        self.assertAlmostEqual(total_cost, 1550.0 + 200.0, places=2)
        self.assertAlmostEqual(total_weight, 15.0 + 4.0, places=2)

        # Tri : Rebut avant Pâte
        self.assertEqual(lines[0]['scrap_type'], 'scrap_recoverable',
                         "Rebut Récupérable doit apparaître avant Pâte Récupérable")

    def test_prepare_report_data_mode_recoverables_only(self):
        """Mode 'recoverables_only' : MP et packaging vidés, recoverable_lines présent."""
        wizard = self._make_wizard(scope='recoverables_only')
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertFalse(data.get('show_raw_material'))
        self.assertFalse(data.get('show_packaging'))
        self.assertTrue(data.get('show_recoverable'))
        self.assertEqual(data.get('lines'), [])
        self.assertEqual(data.get('packaging_lines'), [])
        self.assertTrue(data.get('recoverable_lines'),
                        "recoverable_lines doit être renseigné (fixtures non vides)")
        # En mode récupérables seuls, les 3 totaux sont alignés sur la valeur
        # des récupérables
        rec_cost = data.get('recoverable_total_cost') or 0.0
        self.assertAlmostEqual(data.get('gross_total_cost'), rec_cost, places=2)
        self.assertAlmostEqual(data.get('net_total_cost'), rec_cost, places=2)

    def test_prepare_report_data_mode_all_with_net_cost_enabled(self):
        """Mode 'all' avec compute_net_cost=True : net_total = brut − récupérables."""
        wizard = self._make_wizard(scope='all', compute_net_cost=True)
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertTrue(data.get('show_recoverable'))
        gross = data.get('gross_total_cost') or 0.0
        rec = data.get('recoverable_total_cost') or 0.0
        net = data.get('net_total_cost') or 0.0

        self.assertGreater(rec, 0.0, "Les fixtures incluent des récupérables")
        self.assertAlmostEqual(net, gross - rec, places=2,
                               msg="net_total_cost = gross_total_cost − recoverable_total_cost")
        # combined_total_cost garde la sémantique brute (rétro-compat)
        self.assertAlmostEqual(data.get('combined_total_cost'), gross, places=2,
                               msg="combined_total_cost reste la valeur brute")

    def test_prepare_report_data_mode_all_with_net_cost_disabled(self):
        """Mode 'all' avec compute_net_cost=False : récupérables affichés mais
        non déduits → net_total = brut.
        """
        wizard = self._make_wizard(scope='all', compute_net_cost=False)
        result = wizard._prepare_report_data()
        data = result['data']

        gross = data.get('gross_total_cost') or 0.0
        net = data.get('net_total_cost') or 0.0
        rec = data.get('recoverable_total_cost') or 0.0

        self.assertGreater(rec, 0.0, "Les récupérables doivent être présents en data")
        self.assertAlmostEqual(net, gross, places=2,
                               msg="Sans compute_net_cost, net = brut (récupérables informatifs)")

    # ==================================================================
    # Scope par défaut "consumption" (Rapport de Consommation Globale)
    # ==================================================================

    def test_default_scope_is_consumption(self):
        """Le défaut du wizard doit être 'consumption' — pas de récupérables
        affichés dans le rapport sans action explicite de l'utilisateur.
        """
        wizard = self.env['ron.print.consumption.report.wizard'].create({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
            'company_id': self.company.id,
            # content_scope volontairement non passé → doit prendre le défaut
        })
        self.assertEqual(wizard.content_scope, 'consumption',
                         "Le scope par défaut doit être 'consumption' "
                         "(Rapport de Consommation Globale)")

    def test_build_domain_scope_consumption_excludes_recoverables(self):
        """Scope 'consumption' doit limiter aux catégories MP + Emballages/Films,
        excluant explicitement les récupérables.
        """
        wizard = self._make_wizard(scope='consumption')
        domain = wizard._build_domain()

        cat_filter = [
            t for t in domain
            if isinstance(t, (list, tuple))
            and t[0] == 'consumption_category'
            and t[1] == 'in'
        ]
        self.assertEqual(len(cat_filter), 1,
                         "Un filtre consumption_category in (...) attendu en 'consumption'")
        expected = set(cat_filter[0][2])
        self.assertEqual(expected, {'raw_material', 'packaging', 'film'},
                         "Le filtre doit exclure scrap_recoverable et paste_recoverable")

    def test_prepare_report_data_mode_consumption(self):
        """Mode 'consumption' : MP + packaging affichés, récupérables vides,
        total = MP + packaging (pas de coût net puisque pas de récupérables).
        """
        wizard = self._make_wizard(scope='consumption')
        result = wizard._prepare_report_data()
        data = result['data']

        self.assertTrue(data.get('show_raw_material'))
        self.assertTrue(data.get('show_packaging'))
        self.assertFalse(data.get('show_recoverable'),
                         "Les récupérables ne doivent jamais apparaître en 'consumption'")
        self.assertEqual(data.get('recoverable_lines'), [])
        self.assertEqual(data.get('recoverable_total_cost'), 0.0)

        # gross = combined = net = MP + packaging
        gross = data.get('gross_total_cost') or 0.0
        expected_gross = (data.get('grand_total_cost') or 0.0) + (
            data.get('packaging_total_cost') or 0.0
        )
        self.assertAlmostEqual(gross, expected_gross, places=2,
                               msg="gross_total_cost = MP + packaging")
        self.assertAlmostEqual(data.get('net_total_cost'), gross, places=2,
                               msg="net_total_cost = gross en 'consumption' (pas de récup à déduire)")

    def test_onchange_recoverables_only_disables_mp_per_finished(self):
        """Passer en recoverables_only doit forcer include_mp_per_finished=False."""
        wizard = self.env['ron.print.consumption.report.wizard'].new({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
            'company_id': self.company.id,
            'content_scope': 'all',
            'include_mp_per_finished': True,
        })

        wizard.content_scope = 'recoverables_only'
        wizard._onchange_content_scope()

        self.assertFalse(wizard.include_mp_per_finished,
                         "include_mp_per_finished doit être False après passage "
                         "en 'recoverables_only'")
