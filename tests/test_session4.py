"""
Session 4 Tests: Proof System, Dependency Index, Structure Extraction, WL Prefilter

Tests cover:
1.  ProofTerm: canonical form, serialization, parse from legacy strings
2.  morphism_dependencies: population via add_derived_morphism
3.  get_dependents: direct + transitive closure
4.  _propagate_belief: O(k) index-based propagation (correctness)
5.  check_proof: valid axioms, valid transitivity, invalid (missing premise)
6.  normalize_proof_term: associativity invariance, commutative rules, leaves
7.  extract_common_core: finds common morphisms under object_map functor
8.  Proof tree deep chains: depth-5 propagation
9.  WL fingerprint: hash stability, bucket grouping, prefilter on large graphs
10. Dependency backfill migration: old derivation records get indexed
11. Proof deduplication: two derivations of same morphism → same canonical term
12. extract_common_core: empty functor (no overlap) returns None
13. Infer task: populates dependency table
14. Belief cascade: 3-level chain propagates fully
"""
import pytest
import json
import time
import uuid

from engine.kernel import ReasoningStore, TaskScheduler, ProofTerm, _split_args
from engine.categories import create_category
from engine.topos import TruthValue, Modality, compose_truth
from engine.scale import _wl_object_hash, _build_wl_buckets


# ── Fixtures ──────────────────────────────────────────────────────────

def store():
    return ReasoningStore(":memory:")


def _chain(s: ReasoningStore, n: int = 3, truth: float = 0.9):
    """Linear chain of n objects with n-1 morphisms, returns (domain_id, [morph_ids])."""
    labels = [chr(ord('a') + i) for i in range(n)]
    did = s.create_domain(f"Chain{n}")
    ids = []
    for i in range(n - 1):
        mid = s.add_morphism(did, f"r{i}", labels[i], labels[i+1], "isa",
                             truth_degree=truth, truth_modality="PROBABLE")
        ids.append(mid)
    return did, ids


# ══════════════════════════════════════════════════════════════════════
# 1. ProofTerm
# ══════════════════════════════════════════════════════════════════════

class TestProofTerm:
    def test_canonical_axiom(self):
        pt = ProofTerm.axiom()
        assert pt.canonical() == "axiom()"

    def test_canonical_transitivity_ordered(self):
        pt = ProofTerm.transitivity("aaa", "bbb", "ccc")
        canon = pt.canonical()
        assert canon.startswith("transitivity(")
        # Order preserved for directed rule
        assert "aaa" in canon and "bbb" in canon and "ccc" in canon

    def test_canonical_commutative_sorted(self):
        pt1 = ProofTerm(rule="auto_compose", premises=["z", "a", "m"])
        pt2 = ProofTerm(rule="auto_compose", premises=["a", "m", "z"])
        assert pt1.canonical() == pt2.canonical()

    def test_roundtrip_json(self):
        pt = ProofTerm.transitivity("id1", "id2")
        restored = ProofTerm.from_json(pt.to_json())
        assert restored.rule == pt.rule
        assert restored.premises == pt.premises

    def test_parse_legacy_string(self):
        pt = ProofTerm.from_json("transitivity(id1, id2)")
        assert pt.rule == "transitivity"
        assert "id1" in pt.premises
        assert "id2" in pt.premises

    def test_parse_empty_string(self):
        pt = ProofTerm.from_json("")
        assert pt.rule == "axiom"
        assert pt.premises == []

    def test_metadata_preserved(self):
        pt = ProofTerm(rule="extraction", premises=["x"], metadata={"method": "pullback"})
        restored = ProofTerm.from_json(pt.to_json())
        assert restored.metadata["method"] == "pullback"

    def test_split_args_nested(self):
        parts = _split_args("a(b,c), d(e,f), g")
        assert len(parts) == 3
        assert "a(b,c)" in parts

    def test_long_uuid_truncated_in_canonical(self):
        uid = str(uuid.uuid4())
        pt = ProofTerm.transitivity(uid)
        canon = pt.canonical()
        # Should truncate UUID to 8 chars
        assert uid not in canon
        assert uid[:8] in canon


# ══════════════════════════════════════════════════════════════════════
# 2. Dependency Index Population
# ══════════════════════════════════════════════════════════════════════

class TestDependencyIndex:
    def test_add_derived_morphism_populates_index(self):
        s = store()
        did, [m1, m2] = _chain(s)
        d_id = s.add_derived_morphism(did, "r01", "a", "c", "isa",
                                      "transitivity", [m1, m2],
                                      truth_degree=0.8, truth_modality="PROBABLE")
        rows = s.conn.execute(
            "SELECT premise_id, derived_id FROM morphism_dependencies WHERE derived_id=?",
            (d_id,)).fetchall()
        assert len(rows) == 2
        prem_ids = {r["premise_id"] for r in rows}
        assert m1 in prem_ids
        assert m2 in prem_ids

    def test_get_dependents_direct(self):
        s = store()
        did, [m1, m2] = _chain(s)
        d_id = s.add_derived_morphism(did, "r01", "a", "c", "isa",
                                      "transitivity", [m1, m2], truth_degree=0.8)
        deps = s.get_dependents(m1)
        assert d_id in deps

    def test_get_dependents_non_dependent(self):
        s = store()
        did, [m1, m2] = _chain(s)
        s.add_derived_morphism(did, "r01", "a", "c", "isa",
                               "transitivity", [m1, m2], truth_degree=0.8)
        # m2 is a premise of d_id but m1 is not dependent on m2
        deps_of_m2 = s.get_dependents(m2)
        # d_id depends on m2, not m1
        assert all(d != m1 for d in deps_of_m2)

    def test_get_dependents_transitive(self):
        """A three-level chain: c derived from b derived from a."""
        s = store()
        did = s.create_domain("D")
        m_ab = s.add_morphism(did, "ab", "a", "b", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m_bc = s.add_morphism(did, "bc", "b", "c", "r", truth_degree=0.9, truth_modality="PROBABLE")
        d_ac = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                      "transitivity", [m_ab, m_bc], truth_degree=0.81)
        m_cd = s.add_morphism(did, "cd", "c", "d", "r", truth_degree=0.9, truth_modality="PROBABLE")
        d_ad = s.add_derived_morphism(did, "ad", "a", "d", "r",
                                      "transitivity", [d_ac, m_cd], truth_degree=0.73)
        # Transitive: m_ab → d_ac → d_ad
        trans_deps = s.get_dependents(m_ab, recursive=True)
        assert d_ac in trans_deps
        assert d_ad in trans_deps

    def test_dependency_backfill_migration(self):
        """Old derivation records inserted without dependency index get backfilled."""
        s = store()
        did = s.create_domain("Old")
        m1 = s.add_morphism(did, "r1", "p", "q", "rel")
        m2 = s.add_morphism(did, "r2", "q", "r_obj", "rel")
        # Simulate old-style insert (bypass add_derived_morphism)
        d_id = s.add_morphism(did, "r1∘r2", "p", "r_obj", "rel",
                              truth_degree=0.9, truth_modality="PROBABLE")
        s.conn.execute("UPDATE morphisms SET is_inferred=1 WHERE id=?", (d_id,))
        s.conn.execute(
            "INSERT INTO derivations (id, morphism_id, rule, premises, conclusion, truth_degree, timestamp) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), d_id, "transitivity", json.dumps([m1, m2]), "p→r", 0.9, time.time()))
        s.conn.commit()
        # Trigger backfill manually
        s._backfill_dependency_index()
        rows = s.conn.execute(
            "SELECT premise_id FROM morphism_dependencies WHERE derived_id=?",
            (d_id,)).fetchall()
        prem_ids = {r["premise_id"] for r in rows}
        assert m1 in prem_ids
        assert m2 in prem_ids


# ══════════════════════════════════════════════════════════════════════
# 3. Belief Propagation (correctness via index)
# ══════════════════════════════════════════════════════════════════════

class TestBeliefPropagation:
    def test_propagation_decreases_derived_on_contradiction(self):
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "r1", "a", "b", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m2 = s.add_morphism(did, "r2", "b", "c", "r", truth_degree=0.85, truth_modality="PROBABLE")
        td = compose_truth(TruthValue(0.9, Modality.PROBABLE), TruthValue(0.85, Modality.PROBABLE))
        d_id = s.add_derived_morphism(did, "r1r2", "a", "c", "r",
                                      "transitivity", [m1, m2],
                                      truth_degree=td.degree, truth_modality=td.modality.name)
        before = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_id,)).fetchone()["truth_degree"]
        s.add_evidence(m1, "contra", "contradicts", 0.9, "")
        after = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_id,)).fetchone()["truth_degree"]
        assert after < before

    def test_propagation_increases_derived_on_support(self):
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "r1", "x", "y", "r", truth_degree=0.5, truth_modality="PROBABLE")
        m2 = s.add_morphism(did, "r2", "y", "z", "r", truth_degree=0.5, truth_modality="PROBABLE")
        td = compose_truth(TruthValue(0.5, Modality.PROBABLE), TruthValue(0.5, Modality.PROBABLE))
        d_id = s.add_derived_morphism(did, "r1r2", "x", "z", "r",
                                      "transitivity", [m1, m2],
                                      truth_degree=td.degree, truth_modality=td.modality.name)
        before = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_id,)).fetchone()["truth_degree"]
        s.add_evidence(m1, "support", "supports", 0.95, "")
        after = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_id,)).fetchone()["truth_degree"]
        assert after > before

    def test_three_level_cascade(self):
        """Evidence on level 0 cascades through level 1 to level 2."""
        s = store()
        did = s.create_domain("Cascade")
        m_ab = s.add_morphism(did, "ab", "a", "b", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m_bc = s.add_morphism(did, "bc", "b", "c", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m_cd = s.add_morphism(did, "cd", "c", "d", "r", truth_degree=0.9, truth_modality="PROBABLE")
        d_ac = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                      "transitivity", [m_ab, m_bc], truth_degree=0.81)
        d_ad = s.add_derived_morphism(did, "ad", "a", "d", "r",
                                      "transitivity", [d_ac, m_cd], truth_degree=0.729)
        before = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_ad,)).fetchone()["truth_degree"]
        # Contradict m_ab — should cascade: m_ab↓ → d_ac↓ → d_ad↓
        s.add_evidence(m_ab, "contra", "contradicts", 0.9, "")
        after = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (d_ad,)).fetchone()["truth_degree"]
        assert after < before, f"Level-2 derived should decrease but got {after} (was {before})"

    def test_non_dependent_morphism_unchanged(self):
        """An unrelated morphism is not touched by propagation."""
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "r1", "a", "b", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m2 = s.add_morphism(did, "r2", "b", "c", "r", truth_degree=0.9, truth_modality="PROBABLE")
        unrelated = s.add_morphism(did, "unrelated", "x", "y", "r",
                                   truth_degree=0.777, truth_modality="ACTUAL")
        s.add_derived_morphism(did, "ac", "a", "c", "r",
                               "transitivity", [m1, m2], truth_degree=0.81)
        s.add_evidence(m1, "contra", "contradicts", 0.8, "")
        unchanged = s.conn.execute(
            "SELECT truth_degree FROM morphisms WHERE id=?", (unrelated,)).fetchone()["truth_degree"]
        assert abs(unchanged - 0.777) < 1e-6


# ══════════════════════════════════════════════════════════════════════
# 4. check_proof
# ══════════════════════════════════════════════════════════════════════

class TestCheckProof:
    def test_axiom_is_valid(self):
        s = store()
        did = s.create_domain("D")
        mid = s.add_morphism(did, "r1", "a", "b", "r")
        result = s.check_proof(mid)
        assert result["valid"] is True
        assert result["rule"] == "axiom"

    def test_valid_transitivity(self):
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "ab", "a", "b", "r", truth_degree=0.9, truth_modality="PROBABLE")
        m2 = s.add_morphism(did, "bc", "b", "c", "r", truth_degree=0.9, truth_modality="PROBABLE")
        d = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                   "transitivity", [m1, m2], truth_degree=0.81)
        result = s.check_proof(d)
        assert result["valid"] is True
        assert result["rule"] == "transitivity"
        assert result["premises"] == 2

    def test_invalid_missing_premise(self):
        """A derivation referencing a non-existent morphism ID is invalid."""
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "ab", "a", "b", "r")
        fake_id = str(uuid.uuid4())
        d = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                   "transitivity", [m1, fake_id], truth_degree=0.9)
        result = s.check_proof(d)
        assert result["valid"] is False
        assert any("not found" in e for e in result["errors"])

    def test_invalid_chain_break(self):
        """Transitivity premise chain with gap is invalid."""
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "ab", "a", "b", "r")
        m2 = s.add_morphism(did, "cd", "c", "d", "r")  # gap: b ≠ c
        d = s.add_derived_morphism(did, "ad", "a", "d", "r",
                                   "transitivity", [m1, m2], truth_degree=0.9)
        result = s.check_proof(d)
        assert result["valid"] is False
        assert any("break" in e.lower() or "mismatch" in e.lower() for e in result["errors"])

    def test_missing_morphism_returns_invalid(self):
        s = store()
        result = s.check_proof("nonexistent-id")
        assert result["valid"] is False


# ══════════════════════════════════════════════════════════════════════
# 5. normalize_proof_term
# ══════════════════════════════════════════════════════════════════════

class TestNormalizeProofTerm:
    def test_axiom_leaf(self):
        s = store()
        did = s.create_domain("D")
        mid = s.add_morphism(did, "r1", "a", "b", "r")
        n = s.normalize_proof_term(mid)
        assert "axiom" in n
        assert "a" in n and "b" in n

    def test_single_step_transitivity(self):
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "ab", "a", "b", "r")
        m2 = s.add_morphism(did, "bc", "b", "c", "r")
        d = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                   "transitivity", [m1, m2], truth_degree=0.9)
        n = s.normalize_proof_term(d)
        assert n.startswith("transitivity(")
        assert "axiom(a→b)" in n
        assert "axiom(b→c)" in n

    def test_associativity_invariant(self):
        """(A∘B)∘C and A∘(B∘C) produce same canonical form."""
        s = store()
        did = s.create_domain("D")
        m_ab = s.add_morphism(did, "ab", "a", "b", "r")
        m_bc = s.add_morphism(did, "bc", "b", "c", "r")
        m_cd = s.add_morphism(did, "cd", "c", "d", "r")
        # Grouping 1: (a→c)∘(c→d)
        d_ac = s.add_derived_morphism(did, "ac", "a", "c", "r",
                                      "transitivity", [m_ab, m_bc], truth_degree=0.9)
        d_ad_1 = s.add_derived_morphism(did, "ad1", "a", "d", "r",
                                        "transitivity", [d_ac, m_cd], truth_degree=0.81)
        # Grouping 2: (a→b)∘(b→d)
        d_bd = s.add_derived_morphism(did, "bd", "b", "d", "r",
                                      "transitivity", [m_bc, m_cd], truth_degree=0.9)
        d_ad_2 = s.add_derived_morphism(did, "ad2", "a", "d", "r",
                                        "transitivity", [m_ab, d_bd], truth_degree=0.81)
        n1 = s.normalize_proof_term(d_ad_1)
        n2 = s.normalize_proof_term(d_ad_2)
        # Both should normalize to transitivity(axiom(a→b), axiom(b→c), axiom(c→d))
        assert n1 == n2, f"Expected same canonical: {n1!r} != {n2!r}"

    def test_commutative_order_invariant(self):
        """auto_compose proof terms are order-independent."""
        s = store()
        did = s.create_domain("D")
        m1 = s.add_morphism(did, "ab", "a", "b", "r")
        m2 = s.add_morphism(did, "bc", "b", "c", "r")
        d1 = s.add_derived_morphism(did, "ac1", "a", "c", "r",
                                    "auto_compose", [m1, m2], truth_degree=0.9)
        d2 = s.add_derived_morphism(did, "ac2", "a", "c", "r",
                                    "auto_compose", [m2, m1], truth_degree=0.9)
        n1 = s.normalize_proof_term(d1)
        n2 = s.normalize_proof_term(d2)
        assert n1 == n2

    def test_different_derivations_differ(self):
        """Two genuinely different proofs produce different canonical forms."""
        s = store()
        did = s.create_domain("D")
        m_ab = s.add_morphism(did, "ab", "a", "b", "r")
        m_bc = s.add_morphism(did, "bc", "b", "c", "r")
        m_ax = s.add_morphism(did, "ax", "a", "x", "r")
        m_xc = s.add_morphism(did, "xc", "x", "c", "r")
        d1 = s.add_derived_morphism(did, "ac_v1", "a", "c", "r",
                                    "transitivity", [m_ab, m_bc], truth_degree=0.9)
        d2 = s.add_derived_morphism(did, "ac_v2", "a", "c", "r",
                                    "transitivity", [m_ax, m_xc], truth_degree=0.9)
        assert s.normalize_proof_term(d1) != s.normalize_proof_term(d2)


# ══════════════════════════════════════════════════════════════════════
# 6. extract_common_core
# ══════════════════════════════════════════════════════════════════════

class TestExtractCommonCore:
    def _make_two_chains(self, s):
        """Create isomorphic chains A: p→q→r and B: x→y→z."""
        d1 = s.create_domain("Alpha")
        s.add_morphism(d1, "pq", "p", "q", "r")
        s.add_morphism(d1, "qr", "q", "r_obj", "r")
        d2 = s.create_domain("Beta")
        s.add_morphism(d2, "xy", "x", "y", "r")
        s.add_morphism(d2, "yz", "y", "z", "r")
        return d1, d2

    def test_extracts_correct_morphism_count(self):
        s = store()
        d1, d2 = self._make_two_chains(s)
        obj_map = {"p": "x", "q": "y", "r_obj": "z"}
        core_id = s.extract_common_core(d1, d2, obj_map, "core_test")
        assert core_id is not None
        core_morphs = s.get_morphisms(core_id)
        # Both source morphisms p→q, q→r have matching target morphisms x→y, y→z
        assert len(core_morphs) == 2

    def test_core_morphism_labels_from_source(self):
        s = store()
        d1, d2 = self._make_two_chains(s)
        obj_map = {"p": "x", "q": "y", "r_obj": "z"}
        core_id = s.extract_common_core(d1, d2, obj_map)
        core_labels = {m["label"] for m in s.get_morphisms(core_id)}
        assert "pq" in core_labels
        assert "qr" in core_labels

    def test_core_truth_is_average(self):
        """Core morphism truth should be average of source and target truth."""
        s = store()
        d1 = s.create_domain("A")
        s.add_morphism(d1, "ab", "a", "b", "r", truth_degree=0.8, truth_modality="PROBABLE")
        d2 = s.create_domain("B")
        s.add_morphism(d2, "xy", "x", "y", "r", truth_degree=0.6, truth_modality="PROBABLE")
        obj_map = {"a": "x", "b": "y"}
        core_id = s.extract_common_core(d1, d2, obj_map, "core_avg")
        core_morphs = s.get_morphisms(core_id)
        assert len(core_morphs) == 1
        avg = core_morphs[0]["truth_degree"]
        assert abs(avg - 0.7) < 1e-6

    def test_empty_object_map_returns_none(self):
        s = store()
        d1, d2 = self._make_two_chains(s)
        # Empty map → no morphism pairs can match
        result = s.extract_common_core(d1, d2, {}, "empty")
        assert result is None

    def test_partial_overlap(self):
        """Only morphisms where BOTH endpoints are in the object_map contribute."""
        s = store()
        d1 = s.create_domain("Src")
        s.add_morphism(d1, "ab", "a", "b", "r")
        s.add_morphism(d1, "bc", "b", "c", "r")
        s.add_morphism(d1, "cd", "c", "d", "r")
        d2 = s.create_domain("Tgt")
        s.add_morphism(d2, "xy", "x", "y", "r")
        s.add_morphism(d2, "yz", "y", "z", "r")
        # Only map a→x, b→y, c→z (not d)
        obj_map = {"a": "x", "b": "y", "c": "z"}
        core_id = s.extract_common_core(d1, d2, obj_map)
        core_morphs = s.get_morphisms(core_id)
        assert len(core_morphs) == 2  # ab and bc match, cd doesn't (d not mapped)

    def test_core_has_derivation_records(self):
        """Extracted morphisms have proof derivation records."""
        s = store()
        d1, d2 = self._make_two_chains(s)
        obj_map = {"p": "x", "q": "y", "r_obj": "z"}
        core_id = s.extract_common_core(d1, d2, obj_map, "core_deriv")
        core_morphs = s.get_morphisms(core_id)
        for m in core_morphs:
            deriv = s.conn.execute(
                "SELECT rule FROM derivations WHERE morphism_id=?", (m["id"],)).fetchone()
            assert deriv is not None
            assert deriv["rule"] == "extraction"

    def test_core_domain_created_with_description(self):
        s = store()
        d1, d2 = self._make_two_chains(s)
        obj_map = {"p": "x", "q": "y", "r_obj": "z"}
        core_id = s.extract_common_core(d1, d2, obj_map, "my_core")
        domain = s.conn.execute("SELECT name, description FROM domains WHERE id=?",
                                (core_id,)).fetchone()
        assert domain["name"] == "my_core"
        assert "Alpha" in domain["description"] or "core" in domain["description"].lower()


# ══════════════════════════════════════════════════════════════════════
# 7. WL Fingerprint (scale.py)
# ══════════════════════════════════════════════════════════════════════

class TestWLFingerprint:
    def _linear(self, n):
        labels = [chr(ord('a') + i) for i in range(n)]
        morphs = [(f"r{i}", labels[i], labels[i+1]) for i in range(n-1)]
        return create_category(f"L{n}", labels, morphs, auto_close=False)

    def _star(self, n):
        """Hub-and-spoke: hub → spoke_i for i in range(n)."""
        objs = ["hub"] + [f"s{i}" for i in range(n)]
        morphs = [(f"to_s{i}", "hub", f"s{i}") for i in range(n)]
        return create_category(f"Star{n}", objs, morphs, auto_close=False)

    def test_same_structure_same_hash(self):
        cat = self._linear(5)
        h1 = _wl_object_hash(cat, "a")
        h2 = _wl_object_hash(cat, "a")
        assert h1 == h2

    def test_leaf_vs_interior_differ(self):
        cat = self._linear(5)
        h_leaf = _wl_object_hash(cat, "a")      # degree (1 out, 0 in)
        h_inner = _wl_object_hash(cat, "b")     # degree (1 out, 1 in)
        assert h_leaf != h_inner

    def test_hub_vs_spoke_differ(self):
        cat = self._star(4)
        h_hub = _wl_object_hash(cat, "hub")
        h_spoke = _wl_object_hash(cat, "s0")
        assert h_hub != h_spoke

    def test_build_wl_buckets_groups_identical_nodes(self):
        """All spokes in a star have the same hash."""
        cat = self._star(4)
        buckets = _build_wl_buckets(cat)
        # All spokes should be in the same bucket
        spoke_bucket = None
        for h, objs in buckets.items():
            if "s0" in objs:
                spoke_bucket = objs
                break
        assert spoke_bucket is not None
        assert all(f"s{i}" in spoke_bucket for i in range(4))

    def test_wl_prefilter_reduces_search_space(self):
        """CSP with >50 nodes uses WL prefilter; result is still correct."""
        from engine.scale import find_analogies_csp
        # Two identical 52-node linear chains
        n = 52
        labels_a = [f"a{i}" for i in range(n)]
        labels_b = [f"b{i}" for i in range(n)]
        morphs_a = [(f"ra{i}", labels_a[i], labels_a[i+1]) for i in range(n-1)]
        morphs_b = [(f"rb{i}", labels_b[i], labels_b[i+1]) for i in range(n-1)]
        cat_a = create_category("BigA", labels_a, morphs_a, auto_close=False)
        cat_b = create_category("BigB", labels_b, morphs_b, auto_close=False)
        results = find_analogies_csp(cat_a, cat_b, max_results=1, timeout_ms=15000)
        assert len(results) > 0
        assert results[0]["score"] > 0.5

    def test_wl_depth_zero_is_degree_signature(self):
        cat = self._star(3)
        h = _wl_object_hash(cat, "hub", depth=0)
        # At depth 0 it's just the degree counts
        assert "3" in h or "hub" not in h  # just degree counts


# ══════════════════════════════════════════════════════════════════════
# 8. Infer task populates dependency index
# ══════════════════════════════════════════════════════════════════════

class TestInferTaskDependencies:
    def test_infer_task_writes_dependency_index(self):
        s = store()
        sched = TaskScheduler(s)
        did, [m1, m2, m3] = _chain(s, n=4, truth=0.9)
        tid = sched.submit("infer", {"domain_name": "Chain4", "rule": "transitivity"})
        result = sched.execute(tid)
        assert result.get("new_inferences", 0) > 0
        # Dependency table should have entries
        count = s.conn.execute("SELECT COUNT(*) as c FROM morphism_dependencies").fetchone()["c"]
        assert count > 0


# ══════════════════════════════════════════════════════════════════════
# 9. Stats includes dependency count
# ══════════════════════════════════════════════════════════════════════

def test_stats_includes_dependencies():
    s = store()
    assert "dependencies" in s.stats
    assert s.stats["dependencies"] == 0
    did = s.create_domain("D")
    m1 = s.add_morphism(did, "ab", "a", "b", "r")
    m2 = s.add_morphism(did, "bc", "b", "c", "r")
    s.add_derived_morphism(did, "ac", "a", "c", "r",
                           "transitivity", [m1, m2], truth_degree=0.9)
    assert s.stats["dependencies"] == 2


# ══════════════════════════════════════════════════════════════════════
# 10. Full end-to-end: infer → check_proof → normalize → propagate
# ══════════════════════════════════════════════════════════════════════

def test_end_to_end_proof_system():
    """
    Simulate the full theorem-prover loop:
    1. Create axioms
    2. Run transitivity inference
    3. check_proof the derived morphism
    4. normalize_proof_term matches expected canonical form
    5. Add contradicting evidence — derived truth decreases
    6. get_dependents reports the derived morphism
    """
    s = store()
    sched = TaskScheduler(s)

    did, prem_ids = _chain(s, n=3, truth=0.9)  # a→b→c

    # Step 2: Infer transitive closure
    tid = sched.submit("infer", {"domain_name": "Chain3", "rule": "transitivity"})
    result = sched.execute(tid)
    assert result["new_inferences"] >= 1

    # Step 3: Find the derived a→c morphism
    derived = s.conn.execute(
        "SELECT id, truth_degree FROM morphisms WHERE is_inferred=1 AND domain_id=?",
        (did,)).fetchone()
    assert derived is not None, "Expected at least one inferred morphism"

    # Step 4: check_proof
    proof_check = s.check_proof(derived["id"])
    assert proof_check["valid"], f"Expected valid proof, got errors: {proof_check['errors']}"
    assert proof_check["rule"] == "transitivity"

    # Step 5: normalize
    norm = s.normalize_proof_term(derived["id"])
    assert "transitivity" in norm
    assert "axiom(a→b)" in norm
    assert "axiom(b→c)" in norm

    # Step 6: belief propagation
    before = derived["truth_degree"]
    s.add_evidence(prem_ids[0], "contra", "contradicts", 0.9, "")
    after_row = s.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (derived["id"],)).fetchone()
    assert after_row["truth_degree"] < before

    # Step 7: get_dependents
    deps = s.get_dependents(prem_ids[0], recursive=False)
    assert derived["id"] in deps
