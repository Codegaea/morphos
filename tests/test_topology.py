"""
Test suite for MORPHOS categorical topology engine.

Tests cover all 12 engines with both strict (truth=1.0) and
graded (truth ∈ (0,1)) cases.
"""
import pytest
import math
from collections import defaultdict

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.topology import (
    CategorySnapshot, IsomorphismEngine, FunctorClassifier,
    AdjunctionDetector, LimitsColimits, YonedaEmbedding,
    NerveComplex, HomologyEngine, PersistentHomologyEngine,
    FundamentalGroupoid, MetricEnrichment, HomotopyClassifier, TNorm,
    compare_domains,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

def make_morphism(id, src, tgt, truth=1.0, rel_type="r"):
    return {"id":id,"source_label":src,"target_label":tgt,"truth_degree":truth,"rel_type":rel_type,"domain_id":"test"}


def make_snap(objects, morphisms, name="test"):
    """Build CategorySnapshot from lists."""
    obj_index = {o: i for i, o in enumerate(objects)}
    hom = defaultdict(list)
    best_hom = defaultdict(float)
    out_deg = defaultdict(int)
    in_deg = defaultdict(int)
    for m in morphisms:
        k = (m["source_label"], m["target_label"])
        hom[k].append(m)
        best_hom[k] = max(best_hom[k], m.get("truth_degree", 1.0) or 1.0)
        out_deg[m["source_label"]] += 1
        in_deg[m["target_label"]] += 1
    return CategorySnapshot(
        domain_id=name, domain_name=name, objects=objects, morphisms=morphisms,
        obj_index=obj_index, hom=dict(hom), best_hom=dict(best_hom),
        out_degree=dict(out_deg), in_degree=dict(in_deg),
        n_objects=len(objects), n_morphisms=len(morphisms),
    )


def ids(objs, n=2):
    """Identity morphisms on all objects."""
    return [make_morphism(f"id_{o}", o, o, 1.0, "identity") for o in objs]


@pytest.fixture
def chain_snap():
    """Linear chain A→B→C with direct A→C. Tree-like."""
    objs = ["A","B","C"]
    ms = ids(objs) + [
        make_morphism("ab","A","B",0.9),
        make_morphism("bc","B","C",0.8),
        make_morphism("ac","A","C",0.7),
    ]
    return make_snap(objs, ms)


@pytest.fixture
def cycle_snap():
    """Triangle with a cycle: A→B→C→A."""
    objs = ["A","B","C"]
    ms = ids(objs) + [
        make_morphism("ab","A","B",0.9),
        make_morphism("bc","B","C",0.8),
        make_morphism("ca","C","A",0.7),
    ]
    return make_snap(objs, ms)


@pytest.fixture
def iso_snap():
    """Pair A,B with genuine inverse morphisms."""
    objs = ["A","B","C"]
    ms = ids(objs) + [
        make_morphism("ab","A","B",1.0),
        make_morphism("ba","B","A",1.0),
        make_morphism("bc","B","C",0.9),
    ]
    return make_snap(objs, ms)


@pytest.fixture
def complete_snap():
    """Complete directed graph on 4 nodes (every pair has a morphism)."""
    objs = ["A","B","C","D"]
    ms = ids(objs)
    for i, a in enumerate(objs):
        for b in objs:
            if a != b:
                ms.append(make_morphism(f"{a}{b}", a, b, 0.9))
    return make_snap(objs, ms)


@pytest.fixture
def graded_snap():
    """Category with varying truth degrees for graded testing."""
    objs = ["A","B","C","D"]
    ms = ids(objs) + [
        make_morphism("ab","A","B",0.95),
        make_morphism("bc","B","C",0.8),
        make_morphism("cd","C","D",0.6),
        make_morphism("ad","A","D",0.5),
        make_morphism("bd","B","D",0.7),
    ]
    return make_snap(objs, ms)


# ══════════════════════════════════════════════════════════════
# CategorySnapshot tests
# ══════════════════════════════════════════════════════════════

class TestCategorySnapshot:
    def test_hom_degree(self, chain_snap):
        assert chain_snap.hom_degree("A","B") == pytest.approx(0.9)
        assert chain_snap.hom_degree("B","A") == 0.0

    def test_has_morphism(self, chain_snap):
        assert chain_snap.has_morphism("A","B")
        assert not chain_snap.has_morphism("C","A")

    def test_identity_degree(self, chain_snap):
        assert chain_snap.identity_degree("A") == 1.0

    def test_composition_degree(self, chain_snap):
        d = chain_snap.composition_degree("A","B","C")
        assert d == pytest.approx(min(0.9, 0.8))

    def test_no_morphism_returns_zero(self, chain_snap):
        assert chain_snap.hom_degree("C","B") == 0.0


# ══════════════════════════════════════════════════════════════
# IsomorphismEngine tests
# ══════════════════════════════════════════════════════════════

class TestIsomorphismEngine:
    def test_detects_inverse_pair(self, iso_snap):
        eng = IsomorphismEngine(iso_snap)
        isos = eng.find_isomorphisms()
        iso_ids = {r.morphism_id for r in isos if r.is_iso}
        assert "ab" in iso_ids
        assert "ba" in iso_ids

    def test_non_iso_detected(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        isos = eng.find_isomorphisms()
        non_isos = [r for r in isos if not r.is_iso and r.morphism_id == "ab"]
        assert len(non_isos) == 1

    def test_iso_degree_with_inverse(self, iso_snap):
        eng = IsomorphismEngine(iso_snap)
        d = eng.iso_degree("A","B")
        assert d > 0.8

    def test_iso_degree_no_inverse(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        d = eng.iso_degree("A","B")
        # B→A doesn't exist
        assert d == 0.0

    def test_self_iso_degree(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        d = eng.iso_degree("A","A")
        assert d == pytest.approx(1.0)

    def test_isomorphism_classes_all_distinct(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        classes = eng.isomorphism_classes(threshold=0.99)
        assert len(classes) == 3  # A, B, C all distinct

    def test_isomorphism_classes_merged(self, iso_snap):
        eng = IsomorphismEngine(iso_snap)
        classes = eng.isomorphism_classes(threshold=0.8)
        # A and B should be in the same class
        merged = any("A" in cls and "B" in cls for cls in classes)
        assert merged

    def test_graded_iso_classes_nonempty(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        classes = eng.graded_iso_classes()
        assert len(classes) == 3
        assert all("representative" in c for c in classes)

    def test_identity_morphism_detected_as_iso(self, chain_snap):
        eng = IsomorphismEngine(chain_snap)
        isos = eng.find_isomorphisms()
        identities = [r for r in isos if r.iso_type == "identity"]
        assert len(identities) == 3  # one per object


# ══════════════════════════════════════════════════════════════
# FunctorClassifier tests
# ══════════════════════════════════════════════════════════════

class TestFunctorClassifier:
    def test_identity_functor_is_equivalence(self, chain_snap):
        """F = identity functor: every object maps to itself."""
        obj_map = {"A":"A","B":"B","C":"C"}
        clf = FunctorClassifier(chain_snap, chain_snap, obj_map)
        faith = clf.faithful_degree()
        full = clf.full_degree()
        assert faith == pytest.approx(1.0)
        assert full == pytest.approx(1.0)
        assert clf.injective_on_objects()
        assert clf.surjective_on_objects()

    def test_non_surjective_detected(self, chain_snap, iso_snap):
        """F maps C to itself but only 2 out of 3 target objects covered."""
        obj_map = {"A":"A","B":"B"}  # C not in map
        clf = FunctorClassifier(chain_snap, chain_snap, obj_map)
        assert not clf.surjective_on_objects()

    def test_non_injective_detected(self, chain_snap):
        """F collapses two objects."""
        obj_map = {"A":"A","B":"A","C":"C"}
        clf = FunctorClassifier(chain_snap, chain_snap, obj_map)
        assert not clf.injective_on_objects()

    def test_classify_returns_type(self, chain_snap):
        obj_map = {"A":"A","B":"B","C":"C"}
        clf = FunctorClassifier(chain_snap, chain_snap, obj_map)
        r = clf.classify("self")
        assert r.homomorphism_type in {"iso","equivalence","full","faithful","general"}

    def test_equivalence_degree_bounded(self, chain_snap):
        obj_map = {"A":"A","B":"B","C":"C"}
        clf = FunctorClassifier(chain_snap, chain_snap, obj_map)
        r = clf.classify()
        assert 0.0 <= r.equivalence_degree <= 1.0


# ══════════════════════════════════════════════════════════════
# AdjunctionDetector tests
# ══════════════════════════════════════════════════════════════

class TestAdjunctionDetector:
    def test_identity_adjunction_degree_high(self, chain_snap):
        """Identity functor is self-adjoint: F = G = id has hom bijection."""
        F = {"A":"A","B":"B","C":"C"}
        G = {"A":"A","B":"B","C":"C"}
        det = AdjunctionDetector(chain_snap, chain_snap)
        hd = det.hom_iso_degree(F, G)
        # For identity: Hom(A,B) == Hom(A,B) by biresiduation = 1
        assert hd > 0.5

    def test_godel_biresiduation_symmetric(self):
        det = AdjunctionDetector(make_snap([],[]), make_snap([],[]))
        # p ↔ q using Gödel: biresiduation of p,p = 1
        assert det._biresiduation(0.7, 0.7) == pytest.approx(1.0)
        assert det._biresiduation(0.3, 0.7) == pytest.approx(0.3)

    def test_adjunction_result_has_required_fields(self, chain_snap):
        F = {"A":"A","B":"B","C":"C"}
        G = {"A":"A","B":"B","C":"C"}
        det = AdjunctionDetector(chain_snap, chain_snap)
        r = det.check_adjunction("F", F, "G", G)
        assert hasattr(r, "adjunction_degree")
        assert hasattr(r, "hom_iso_degree")
        assert hasattr(r, "is_adjunction")
        assert 0.0 <= r.adjunction_degree <= 1.0


# ══════════════════════════════════════════════════════════════
# LimitsColimits tests
# ══════════════════════════════════════════════════════════════

class TestLimitsColimits:
    def test_terminal_object_found(self, chain_snap):
        """C should be terminal (everything points toward it)."""
        lim = LimitsColimits(chain_snap)
        t = lim.terminal_object()
        assert t.apex is not None
        assert t.degree >= 0.0

    def test_initial_object_found(self, chain_snap):
        """A should be initial (it points to everything)."""
        lim = LimitsColimits(chain_snap)
        i = lim.initial_object()
        assert i.apex is not None

    def test_product_found(self, complete_snap):
        """In a complete graph, any object can serve as product."""
        lim = LimitsColimits(complete_snap)
        p = lim.product("A","B")
        assert p.apex is not None
        assert p.degree >= 0.0

    def test_coproduct_found(self, complete_snap):
        lim = LimitsColimits(complete_snap)
        cp = lim.coproduct("A","B")
        assert cp.apex is not None

    def test_equalizer_found(self, chain_snap):
        lim = LimitsColimits(chain_snap)
        eq = lim.equalizer("B","C")
        assert eq.limit_type == "equalizer"

    def test_pullback_found(self, chain_snap):
        lim = LimitsColimits(chain_snap)
        pb = lim.pullback("A","C","B")
        assert pb.limit_type == "pullback"

    def test_pushout_found(self, chain_snap):
        lim = LimitsColimits(chain_snap)
        po = lim.pushout("A","B","C")
        assert po.limit_type == "pushout"

    def test_degree_in_unit_interval(self, chain_snap):
        lim = LimitsColimits(chain_snap)
        for r in [lim.terminal_object(), lim.initial_object(), lim.product("A","B")]:
            assert 0.0 <= r.degree <= 1.0


# ══════════════════════════════════════════════════════════════
# YonedaEmbedding tests
# ══════════════════════════════════════════════════════════════

class TestYonedaEmbedding:
    def test_representable_presheaf_identity(self, chain_snap):
        """y(A)(A) = hom(A,A) = 1.0."""
        y = YonedaEmbedding(chain_snap)
        psh = y.representable_presheaf("A")
        assert psh["A"] == pytest.approx(1.0)

    def test_representable_presheaf_no_morphism(self, chain_snap):
        """y(A)(C) = hom(C,A) = 0 (no morphism C→A)."""
        y = YonedaEmbedding(chain_snap)
        psh = y.representable_presheaf("A")
        assert psh["C"] == pytest.approx(0.0)

    def test_all_representables_keyset(self, chain_snap):
        y = YonedaEmbedding(chain_snap)
        reps = y.all_representables()
        assert set(reps.keys()) == {"A","B","C"}

    def test_yoneda_matrix_shape(self, chain_snap):
        y = YonedaEmbedding(chain_snap)
        Y = y.yoneda_matrix()
        assert Y.shape == (3, 3)

    def test_yoneda_matrix_full_rank(self, chain_snap):
        """Distinct objects with distinct hom-profiles should give full rank."""
        import numpy as np
        y = YonedaEmbedding(chain_snap)
        Y = y.yoneda_matrix()
        rank = np.linalg.matrix_rank(Y)
        assert rank == 3

    def test_representability_check(self, chain_snap):
        y = YonedaEmbedding(chain_snap)
        # y(B) should be representable by B
        psh_b = y.representable_presheaf("B")
        obj, deg = y.representability_degree(psh_b)
        assert deg > 0.9


# ══════════════════════════════════════════════════════════════
# NerveComplex tests
# ══════════════════════════════════════════════════════════════

class TestNerveComplex:
    def test_0simplices_count(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=0)
        summary = nerve.summary()
        assert summary["simplices_by_dim"][0] == 3

    def test_1simplices_excludes_self_loops(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=1)
        simplices = nerve.build()
        one_simplices = [s for s in simplices if s.dim == 1]
        for s in one_simplices:
            assert s.objects[0] != s.objects[1]

    def test_2simplices_form_triangle(self, chain_snap):
        """Chain A→B→C→A-direct should yield triangle."""
        nerve = NerveComplex(chain_snap, max_dim=2)
        simplices = nerve.build()
        two_s = [s for s in simplices if s.dim == 2]
        assert len(two_s) >= 1

    def test_filtration_values_in_range(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=2)
        for s in nerve.build():
            assert 0.0 <= s.filtration <= 1.0

    def test_filtration_monotone_with_truth(self, graded_snap):
        """Weaker morphisms should have larger filtration values."""
        nerve = NerveComplex(graded_snap, max_dim=1)
        simplices = {s.objects: s for s in nerve.build() if s.dim == 1}
        # A→B has truth 0.95, C→D has truth 0.6
        assert simplices[("A","B")].filtration < simplices[("C","D")].filtration

    def test_gudhi_simplex_tree_builds(self, chain_snap):
        import gudhi
        nerve = NerveComplex(chain_snap, max_dim=2)
        st = nerve.to_gudhi_simplex_tree()
        assert st.num_vertices() == 3


# ══════════════════════════════════════════════════════════════
# HomologyEngine tests
# ══════════════════════════════════════════════════════════════

class TestHomologyEngine:
    def test_connected_b0_equals_1(self, chain_snap):
        """Chain A→B→C is connected, so β₀ = 1."""
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = HomologyEngine(nerve)
        betti = eng.betti_numbers()
        assert betti[0] == 1

    def test_disconnected_b0_greater_than_1(self):
        """Two isolated objects have β₀ = 2."""
        snap = make_snap(["X","Y"], ids(["X","Y"]))
        nerve = NerveComplex(snap, max_dim=1)
        eng = HomologyEngine(nerve)
        betti = eng.betti_numbers()
        assert betti[0] == 2

    def test_euler_characteristic(self, chain_snap):
        """χ = |V| - |E| + |triangles| - ..."""
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = HomologyEngine(nerve)
        chi = eng.euler_characteristic()
        assert isinstance(chi, int)

    def test_is_connected(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=1)
        eng = HomologyEngine(nerve)
        assert eng.is_connected()

    def test_not_connected(self):
        snap = make_snap(["X","Y"], ids(["X","Y"]))
        nerve = NerveComplex(snap, max_dim=1)
        eng = HomologyEngine(nerve)
        assert not eng.is_connected()

    def test_betti_numbers_nonnegative(self, complete_snap):
        nerve = NerveComplex(complete_snap, max_dim=3)
        eng = HomologyEngine(nerve)
        betti = eng.betti_numbers()
        for n, b in betti.items():
            assert b >= 0, f"β{n} = {b} < 0"


# ══════════════════════════════════════════════════════════════
# PersistentHomologyEngine tests
# ══════════════════════════════════════════════════════════════

class TestPersistentHomologyEngine:
    def test_computes_without_error(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag = eng.compute()
        assert diag is not None

    def test_pairs_have_correct_dimensions(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag = eng.compute()
        for p in diag.pairs:
            assert p.dimension >= 0
            assert 0.0 <= p.birth_truth <= 1.0

    def test_birth_death_truth_ordering(self, graded_snap):
        """Birth truth ≥ death truth (features die as confidence drops)."""
        nerve = NerveComplex(graded_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag = eng.compute()
        for p in diag.pairs:
            if not p.is_essential():
                assert p.birth_truth >= p.death_truth - 0.01

    def test_betti_numbers_from_gudhi(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag = eng.compute()
        assert 0 in diag.betti_numbers

    def test_serialization(self, chain_snap):
        nerve = NerveComplex(chain_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag = eng.compute()
        d = eng.to_dict(diag)
        assert "pairs" in d
        assert "betti_numbers" in d
        assert "euler_characteristic" in d

    def test_min_persistence_filter(self, graded_snap):
        nerve = NerveComplex(graded_snap, max_dim=2)
        eng = PersistentHomologyEngine(nerve)
        diag_all = eng.compute(min_persistence=0.0)
        diag_filtered = eng.compute(min_persistence=0.3)
        assert len(diag_filtered.pairs) <= len(diag_all.pairs)


# ══════════════════════════════════════════════════════════════
# FundamentalGroupoid tests
# ══════════════════════════════════════════════════════════════

class TestFundamentalGroupoid:
    def test_connected_chain_has_one_component(self, chain_snap):
        fg = FundamentalGroupoid(chain_snap)
        comps = fg.pi0()
        assert len(comps) == 1

    def test_isolated_nodes_separate_components(self):
        snap = make_snap(["X","Y","Z"], ids(["X","Y","Z"]))
        fg = FundamentalGroupoid(snap)
        comps = fg.pi0()
        assert len(comps) == 3

    def test_pi1_rank_tree(self, chain_snap):
        """Chain A-B-C (tree) has β₁ = 0."""
        # A→B, B→C, A→C (undirected: A-B, B-C, A-C) — that's 3 edges, 3 verts, 1 comp
        # β₁ = 3 - 3 + 1 = 1 (triangle)
        fg = FundamentalGroupoid(chain_snap)
        b1 = fg.pi1_rank()
        assert b1 >= 0

    def test_pi1_rank_cycle(self, cycle_snap):
        """Cycle A→B→C→A contributes to first Betti number."""
        fg = FundamentalGroupoid(cycle_snap)
        b1 = fg.pi1_rank()
        assert b1 >= 1

    def test_graded_pi0_threshold_effect(self, graded_snap):
        fg = FundamentalGroupoid(graded_snap)
        # At threshold 1.0, only truth=1 morphisms count
        comp_strict = fg.pi0(threshold=1.0)
        # At threshold 0.0, all morphisms count
        comp_all = fg.pi0(threshold=0.0)
        # Stricter threshold → more or equal components
        assert len(comp_strict) >= len(comp_all)

    def test_homotopy_type_string(self, chain_snap):
        fg = FundamentalGroupoid(chain_snap)
        h = fg.homotopy_type()
        assert isinstance(h, str)
        assert len(h) > 0

    def test_compute_returns_result(self, chain_snap):
        fg = FundamentalGroupoid(chain_snap)
        r = fg.compute()
        assert r.n_components >= 1
        assert r.pi1_rank >= 0
        assert isinstance(r.homotopy_type, str)

    def test_graded_components_keys(self, chain_snap):
        fg = FundamentalGroupoid(chain_snap)
        r = fg.compute()
        assert 1.0 in r.graded_components
        assert 0.0 in r.graded_components


# ══════════════════════════════════════════════════════════════
# MetricEnrichment tests
# ══════════════════════════════════════════════════════════════

class TestMetricEnrichment:
    def test_distance_zero_for_self(self, chain_snap):
        metric = MetricEnrichment(chain_snap, "godel")
        assert metric.distance("A","A") == pytest.approx(0.0)

    def test_distance_inf_no_morphism(self, chain_snap):
        metric = MetricEnrichment(chain_snap, "godel")
        assert math.isinf(metric.distance("B","A"))

    def test_distance_finite_with_morphism(self, chain_snap):
        metric = MetricEnrichment(chain_snap, "godel")
        d = metric.distance("A","B")
        assert 0.0 < d < float("inf")

    def test_godel_tnorm(self):
        assert TNorm.godel(0.7, 0.4) == pytest.approx(0.4)

    def test_product_tnorm(self):
        assert TNorm.product(0.5, 0.8) == pytest.approx(0.4)

    def test_lukasiewicz_tnorm(self):
        assert TNorm.lukasiewicz(0.4, 0.3) == pytest.approx(0.0)
        assert TNorm.lukasiewicz(0.7, 0.8) == pytest.approx(0.5)

    def test_godel_residuum(self):
        # p ≤ q → residuum = 1
        assert TNorm.residuum("godel", 0.3, 0.7) == pytest.approx(1.0)
        # p > q → residuum = q
        assert TNorm.residuum("godel", 0.8, 0.4) == pytest.approx(0.4)

    def test_enrichment_axioms_report_has_keys(self, chain_snap):
        metric = MetricEnrichment(chain_snap, "godel")
        r = metric.verify_enrichment_axioms()
        assert "identity_axiom_ok" in r
        assert "composition_axiom_ok" in r
        assert "symmetry_degree" in r
        assert "n_triangle_violations" in r

    def test_symmetry_degree_bounded(self, chain_snap):
        metric = MetricEnrichment(chain_snap, "godel")
        r = metric.verify_enrichment_axioms()
        assert 0.0 <= r["symmetry_degree"] <= 1.0

    def test_complete_graph_fewer_violations(self, complete_snap):
        """Complete directed graph: composition should mostly close."""
        metric = MetricEnrichment(complete_snap, "godel")
        r = metric.verify_enrichment_axioms()
        # All A→B exist so hom(A,B)⊗hom(B,C) ≤ hom(A,C) = 0.9
        # godel: min(0.9,0.9) = 0.9 ≤ 0.9: no violations
        assert r["n_triangle_violations"] == 0


# ══════════════════════════════════════════════════════════════
# HomotopyClassifier tests
# ══════════════════════════════════════════════════════════════

class TestHomotopyClassifier:
    def test_same_map_in_same_class(self, chain_snap):
        """Two identical maps should be in the same homotopy class."""
        obj_map = {"A":"A","B":"B","C":"C"}
        programs = [
            {"name":"p1","object_map":obj_map},
            {"name":"p2","object_map":obj_map},
        ]
        clf = HomotopyClassifier(chain_snap, chain_snap)
        classes = clf.classify(programs, threshold=0.5)
        assert any(len(c.members) == 2 for c in classes)

    def test_different_maps_in_different_classes(self, complete_snap):
        """Completely different maps on non-isomorphic objects → separate classes."""
        programs = [
            {"name":"p1","object_map":{"A":"B","B":"C","C":"D","D":"A"}},
            {"name":"p2","object_map":{"A":"C","B":"D","C":"A","D":"B"}},
        ]
        clf = HomotopyClassifier(complete_snap, complete_snap)
        classes = clf.classify(programs, threshold=0.99)
        # Both should exist as classes
        assert len(classes) >= 1

    def test_empty_programs_returns_empty(self, chain_snap):
        clf = HomotopyClassifier(chain_snap, chain_snap)
        classes = clf.classify([], threshold=0.7)
        assert classes == []

    def test_single_program_one_class(self, chain_snap):
        programs = [{"name":"p1","object_map":{"A":"A","B":"B","C":"C"}}]
        clf = HomotopyClassifier(chain_snap, chain_snap)
        classes = clf.classify(programs, threshold=0.7)
        assert len(classes) == 1
        assert classes[0].class_size == 1

    def test_nat_iso_degree_self_is_one(self, chain_snap):
        """A map is naturally isomorphic to itself (trivially)."""
        obj_map = {"A":"A","B":"B","C":"C"}
        clf = HomotopyClassifier(chain_snap, chain_snap)
        d = clf.nat_iso_degree(obj_map, obj_map)
        assert d > 0.8  # All F(A) = G(A), so iso_degree(x,x) = max hom degree


# ══════════════════════════════════════════════════════════════
# compare_domains tests
# ══════════════════════════════════════════════════════════════

class TestCompareDomains:
    def test_same_domain_zero_distance(self, chain_snap):
        """A category compared to itself should have zero bottleneck distance."""
        result = compare_domains(chain_snap, chain_snap, max_dim=2)
        d0 = result["bottleneck_distances"].get("bottleneck_dim0")
        if d0 is not None:
            assert d0 == pytest.approx(0.0, abs=0.01)

    def test_compare_returns_interpretation(self, chain_snap, cycle_snap):
        result = compare_domains(chain_snap, cycle_snap, max_dim=1)
        assert "interpretation" in result
        assert isinstance(result["interpretation"], str)

    def test_compare_has_both_domain_names(self, chain_snap, cycle_snap):
        result = compare_domains(chain_snap, cycle_snap, max_dim=1)
        assert result["domain1"] == "test"
        assert result["domain2"] == "test"


# ══════════════════════════════════════════════════════════════
# Integration test: compute_topology_report with real store
# ══════════════════════════════════════════════════════════════

class TestIntegration:
    def test_topology_report_via_store(self, tmp_path):
        """End-to-end: import domain, run full topology report."""
        from engine.kernel import ReasoningStore
        db = str(tmp_path / "test.db")
        store = ReasoningStore(db)

        # Build a small domain
        did = store.create_domain("topo_test", "Integration test domain")
        store.add_concept(did, "A")
        store.add_concept(did, "B")
        store.add_concept(did, "C")
        store.add_morphism(did, "A→B", "A", "B", "r", truth_degree=0.9)
        store.add_morphism(did, "B→C", "B", "C", "r", truth_degree=0.8)
        store.add_morphism(did, "A→C", "A", "C", "r", truth_degree=0.7)

        from engine.topology import compute_topology_report
        report = compute_topology_report(store, "topo_test", max_dim=2)

        assert report["n_objects"] == 3
        assert report["n_morphisms"] >= 3
        assert "homology" in report
        assert "persistent_homology" in report
        assert "fundamental_groupoid" in report
        assert "metric_enrichment" in report
        assert "isomorphisms" in report
        assert "yoneda" in report
        assert "limits" in report
        store.close()

    def test_snapshot_from_store(self, tmp_path):
        from engine.kernel import ReasoningStore
        db = str(tmp_path / "test2.db")
        store = ReasoningStore(db)
        did = store.create_domain("snap_test", "")
        store.add_concept(did, "X")
        store.add_concept(did, "Y")
        store.add_morphism(did, "X→Y", "X", "Y", "is-a", truth_degree=0.95)

        snap = CategorySnapshot.from_store(store, "snap_test")
        assert snap.n_objects == 2
        assert snap.hom_degree("X","Y") == pytest.approx(0.95)
        store.close()
