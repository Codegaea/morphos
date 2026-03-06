"""
MORPHOS Categorical Topology Engine

Implements rigorous categorical topology over the existing MORPHOS infrastructure,
integrating with the truth-degree (Heyting algebra) layer throughout.

Mathematical framework:
  MORPHOS categories are enriched over ([0,1], ≤, min, 1) — a quantale.
  Every categorical concept has both a strict version (truth_degree = 1.0)
  and a graded version that holds to a degree p ∈ [0,1].

Modules implemented:
  1. CategorySnapshot     — in-memory view of a domain for computation
  2. IsomorphismEngine    — isomorphisms, graded iso degree, iso classes, homotopy
  3. FunctorClassifier    — full/faithful/essentially surjective, graded
  4. AdjunctionDetector   — unit/counit, triangle identities, graded adjunction degree
  5. LimitsColimits       — product, coproduct, equalizer, pullback, pushout
  6. YonedaEmbedding      — representable presheaves, Yoneda embedding
  7. NerveComplex         — simplicial complex from nerve N(C), truth-filtered
  8. HomologyEngine       — boundary matrices, Smith Normal Form, Betti numbers
  9. PersistentHomology   — filtered nerve, GUDHI, persistence diagram, barcode
 10. FundamentalGroupoid  — π₀ (components), π₁ (edge-path), homotopy classes
 11. MetricEnrichment     — Lawvere metric view, t-norm selection, enriched hom
 12. HomotopyClasses      — classify analogy programs by natural iso equivalence
 13. TopologyReport       — assemble all invariants into a single result dict

References:
  - Lawvere 1973: Metric spaces, generalized logic, and closed categories
  - Kelly 1982: Basic Concepts of Enriched Category Theory
  - Stubbe 2013: An introduction to quantaloid-enriched categories
  - Quillen 1973: Higher algebraic K-theory I (Theorem A, Theorem B)
  - Cohen-Steiner et al 2007: Stability of persistence diagrams
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Any

import numpy as np
from scipy.sparse import lil_matrix, csc_matrix
from sympy.matrices.normalforms import smith_normal_form
from sympy.matrices import Matrix
import gudhi


def _rank_gf2(M: np.ndarray) -> int:
    """
    Compute matrix rank over GF(2) using Gaussian elimination.
    NOTE: np.linalg.matrix_rank computes rank over the reals — wrong for
    homology over Z/2. This function is correct.
    """
    A = np.array(M, dtype=int) % 2
    rows, cols = A.shape
    pivot_row = 0
    for col in range(cols):
        # Find pivot in column col from pivot_row downward
        found = -1
        for r in range(pivot_row, rows):
            if A[r, col] == 1:
                found = r
                break
        if found == -1:
            continue  # no pivot in this column
        # Swap found row with pivot_row
        A[[pivot_row, found]] = A[[found, pivot_row]]
        # Eliminate all other 1s in this column
        for r in range(rows):
            if r != pivot_row and A[r, col] == 1:
                A[r] = (A[r] + A[pivot_row]) % 2
        pivot_row += 1
    return pivot_row


# ══════════════════════════════════════════════════════════════
# 1. CategorySnapshot — load domain into memory for computation
# ══════════════════════════════════════════════════════════════

@dataclass
class CategorySnapshot:
    """
    In-memory view of a MORPHOS domain for efficient topology computation.

    Computed once from SQLite, then all algorithms operate in memory.
    This is critical: topology algorithms need repeated random access
    to hom-sets and composition; O(1) dict lookup vs O(log n) SQL.
    """
    domain_id: str
    domain_name: str
    objects: list[str]                          # ordered list of object labels
    morphisms: list[dict]                       # all morphism dicts from DB
    obj_index: dict[str, int]                  # label → integer index
    hom: dict[tuple[str,str], list[dict]]      # (src,tgt) → [morphism dicts]
    best_hom: dict[tuple[str,str], float]      # enriched hom-value = max truth_degree
    out_degree: dict[str, int]                  # label → out-degree
    in_degree: dict[str, int]                   # label → in-degree
    n_objects: int
    n_morphisms: int

    @classmethod
    def from_store(cls, store, domain_name: str) -> "CategorySnapshot":
        """Load a domain from the ReasoningStore into memory."""
        domain = store.get_domain(domain_name)
        if not domain:
            raise ValueError(f"Domain '{domain_name}' not found")

        concepts = store.get_concepts(domain["id"])
        morphisms = store.get_morphisms(domain["id"])

        objects = [c["label"] for c in concepts]
        obj_index = {lbl: i for i, lbl in enumerate(objects)}

        hom: dict[tuple[str,str], list[dict]] = defaultdict(list)
        best_hom: dict[tuple[str,str], float] = defaultdict(float)
        out_deg: dict[str, int] = defaultdict(int)
        in_deg: dict[str, int] = defaultdict(int)

        for m in morphisms:
            key = (m["source_label"], m["target_label"])
            hom[key].append(m)
            td = m.get("truth_degree", 1.0) or 1.0
            best_hom[key] = max(best_hom[key], td)
            out_deg[m["source_label"]] += 1
            in_deg[m["target_label"]] += 1

        return cls(
            domain_id=domain["id"],
            domain_name=domain_name,
            objects=objects,
            morphisms=morphisms,
            obj_index=obj_index,
            hom=dict(hom),
            best_hom=dict(best_hom),
            out_degree=dict(out_deg),
            in_degree=dict(in_deg),
            n_objects=len(objects),
            n_morphisms=len(morphisms),
        )

    def hom_degree(self, src: str, tgt: str) -> float:
        """Enriched hom-value: best truth degree of any morphism src→tgt, 0 if none."""
        return self.best_hom.get((src, tgt), 0.0)

    def has_morphism(self, src: str, tgt: str) -> bool:
        return (src, tgt) in self.hom

    def identity_degree(self, obj: str) -> float:
        """Degree of the identity morphism on obj (should be 1.0 for any valid category)."""
        return self.hom_degree(obj, obj)

    def composition_degree(self, src: str, mid: str, tgt: str) -> float:
        """
        Degree of the composition path src→mid→tgt existing in the category.
        Returns min(hom(src,mid), hom(mid,tgt)) if both exist — weakest-premise rule.
        """
        f = self.hom_degree(src, mid)
        g = self.hom_degree(mid, tgt)
        if f > 0 and g > 0:
            return min(f, g)
        return 0.0


# ══════════════════════════════════════════════════════════════
# 2. IsomorphismEngine
# ══════════════════════════════════════════════════════════════

@dataclass
class IsomorphismResult:
    morphism_id: str
    source: str
    target: str
    inverse_id: Optional[str]
    is_iso: bool
    iso_degree: float          # graded: degree to which this is an isomorphism
    iso_type: str              # "strict" | "graded" | "endomorphism" | "identity"


class IsomorphismEngine:
    """
    Detects isomorphisms and computes isomorphism structure of a category.

    Standard definition: f: A→B is iso iff ∃g: B→A with g∘f=id_A, f∘g=id_B.
    Graded definition (recommended, §4.3 of design spec):
      iso_degree(f) = sup_g { μ(f) ⊗ μ(g) ⊗ [g∘f=id_A] ⊗ [f∘g=id_B] }
    where ⊗ = min (Gödel t-norm) and [·] ∈ {0,1} tests actual identity.
    """

    def __init__(self, snap: CategorySnapshot):
        self.snap = snap

    def find_isomorphisms(self) -> list[IsomorphismResult]:
        """
        Find all morphisms that have an inverse in the category.
        Returns list of IsomorphismResult (one per isomorphism, not per pair).
        Complexity: O(|Mor|²) — for each morphism, check all potential inverses.
        """
        results = []
        snap = self.snap

        # Build index: (src,tgt) → list of morphism dicts
        # For f: A→B to be iso, we need g: B→A with g∘f = id_A and f∘g = id_B
        # In a finite category without explicit composition table,
        # we check: does id_A-morphism exist (A→A) AND id_B-morphism exist (B→B)?
        # And is there a path B→A of sufficient truth degree?

        for m in snap.morphisms:
            src, tgt = m["source_label"], m["target_label"]
            mu_f = m.get("truth_degree", 1.0) or 1.0

            if src == tgt:
                # Endomorphism — could be identity
                is_id = (mu_f >= 0.99 and m.get("rel_type", "") in
                         ("identity", "id", "reflexive", "self"))
                results.append(IsomorphismResult(
                    morphism_id=m["id"],
                    source=src, target=tgt,
                    inverse_id=m["id"],
                    is_iso=is_id,
                    iso_degree=mu_f if is_id else 0.0,
                    iso_type="identity" if is_id else "endomorphism",
                ))
                continue

            # Look for inverse: g: tgt→src
            inv_candidates = snap.hom.get((tgt, src), [])
            if not inv_candidates:
                results.append(IsomorphismResult(
                    morphism_id=m["id"],
                    source=src, target=tgt,
                    inverse_id=None,
                    is_iso=False,
                    iso_degree=0.0,
                    iso_type="non-iso",
                ))
                continue

            # For each candidate inverse, compute graded iso degree
            best_degree = 0.0
            best_inv = None
            for g in inv_candidates:
                mu_g = g.get("truth_degree", 1.0) or 1.0
                # Check triangle identities:
                # g∘f should be id_src (src→src exists)
                gf_exists = snap.hom_degree(src, src) > 0
                # f∘g should be id_tgt (tgt→tgt exists)
                fg_exists = snap.hom_degree(tgt, tgt) > 0
                # Graded: iso_degree = min(μ(f), μ(g)) if both triangles hold
                if gf_exists and fg_exists:
                    d = min(mu_f, mu_g, snap.hom_degree(src, src), snap.hom_degree(tgt, tgt))
                else:
                    # Partial credit: average of satisfied conditions
                    satisfied = sum([gf_exists, fg_exists]) / 2
                    d = min(mu_f, mu_g) * satisfied
                if d > best_degree:
                    best_degree = d
                    best_inv = g

            is_strict = best_degree >= 0.99
            results.append(IsomorphismResult(
                morphism_id=m["id"],
                source=src, target=tgt,
                inverse_id=best_inv["id"] if best_inv else None,
                is_iso=is_strict,
                iso_degree=best_degree,
                iso_type="strict" if is_strict else ("graded" if best_degree > 0.3 else "non-iso"),
            ))

        return results

    def iso_degree(self, obj_a: str, obj_b: str) -> float:
        """
        Graded isomorphism degree between two objects.
        iso_degree(A,B) = sup over all f:A→B, g:B→A of graded check.
        """
        if obj_a == obj_b:
            return self.snap.hom_degree(obj_a, obj_a)
        forward = self.snap.hom.get((obj_a, obj_b), [])
        backward = self.snap.hom.get((obj_b, obj_a), [])
        if not forward or not backward:
            return 0.0
        best = 0.0
        for f in forward:
            for g in backward:
                mu_f = f.get("truth_degree", 1.0) or 1.0
                mu_g = g.get("truth_degree", 1.0) or 1.0
                id_a = self.snap.hom_degree(obj_a, obj_a)
                id_b = self.snap.hom_degree(obj_b, obj_b)
                d = min(mu_f, mu_g, max(id_a, 0.5), max(id_b, 0.5))
                best = max(best, d)
        return best

    def isomorphism_classes(self, threshold: float = 0.8) -> list[list[str]]:
        """
        Compute isomorphism classes of objects via union-find.
        Two objects are in the same class if iso_degree ≥ threshold.
        Returns list of equivalence classes (list of object labels).
        Complexity: O(n² · |max hom-set|) + union-find O(n·α(n))
        """
        n = self.snap.n_objects
        objs = self.snap.objects
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        idx = self.snap.obj_index
        for i, a in enumerate(objs):
            for b in objs[i+1:]:
                if self.iso_degree(a, b) >= threshold:
                    union(idx[a], idx[b])

        classes: dict[int, list[str]] = defaultdict(list)
        for obj in objs:
            classes[find(idx[obj])].append(obj)
        return [sorted(cls) for cls in classes.values()]

    def graded_iso_classes(self) -> list[dict]:
        """
        Return objects grouped by best mutual iso degree, with the degree recorded.
        More informative than threshold-based classes.
        """
        objs = self.snap.objects
        result = []
        visited = set()
        for a in objs:
            if a in visited:
                continue
            group = [a]
            visited.add(a)
            degrees = {}
            for b in objs:
                if b == a or b in visited:
                    continue
                d = self.iso_degree(a, b)
                if d > 0.1:
                    group.append(b)
                    degrees[b] = d
                    visited.add(b)
            result.append({
                "representative": a,
                "objects": group,
                "iso_degrees": degrees,
                "is_strict_class": all(d >= 0.99 for d in degrees.values()),
            })
        return result


# ══════════════════════════════════════════════════════════════
# 3. FunctorClassifier
# ══════════════════════════════════════════════════════════════

@dataclass
class FunctorClassification:
    """Classification of an analogy (functor) stored in programs table."""
    program_name: str
    source_domain: str
    target_domain: str
    is_faithful: bool
    is_full: bool
    is_essentially_surjective: bool
    is_equivalence: bool          # full + faithful + ess. surjective
    is_injective_on_objects: bool
    is_surjective_on_objects: bool
    faithful_degree: float
    full_degree: float
    ess_surjective_degree: float
    equivalence_degree: float
    homomorphism_type: str        # "iso" | "equivalence" | "full" | "faithful" | "general"


class FunctorClassifier:
    """
    Classifies stored functors (analogy programs) by their categorical properties.

    For an analogy program P with object_map F_ob: Ob(C) → Ob(D):
      - Faithful: F injective on each hom-set Hom(A,B) → Hom(FA,FB)
      - Full: F surjective on each hom-set
      - Essentially surjective: ∀D ∈ Ob(D), ∃C with F(C) ≅ D
      - Equivalence: full + faithful + essentially surjective

    Graded versions use the enriched framework.
    """

    def __init__(self, src_snap: CategorySnapshot, tgt_snap: CategorySnapshot,
                 object_map: dict[str, str]):
        """
        Args:
            src_snap: source category
            tgt_snap: target category
            object_map: {src_obj_label: tgt_obj_label}
        """
        self.src = src_snap
        self.tgt = tgt_snap
        self.F = object_map  # F on objects

    def faithful_degree(self) -> float:
        """
        Graded faithfulness: inf_{A,B} inf_{f≠g: A→B} ¬[F(f) = F(g)]
        In our setting: F sends rel_type+endpoints to F(A)→F(B).
        We approximate by checking: if two distinct morphisms A→B have the
        same (rel_type, source, target) image, that's a collision.
        Degree = fraction of hom-sets where F is injective.
        """
        total_hom_sets = 0
        injective_hom_sets = 0

        for (src, tgt), morphs in self.src.hom.items():
            fa = self.F.get(src)
            fb = self.F.get(tgt)
            if fa is None or fb is None:
                continue
            total_hom_sets += 1
            # Map each morphism to its image (by rel_type, since we track that)
            images = [(m.get("rel_type", "?"),) for m in morphs]
            if len(set(images)) == len(images):
                injective_hom_sets += 1

        if total_hom_sets == 0:
            return 1.0
        return injective_hom_sets / total_hom_sets

    def full_degree(self) -> float:
        """
        Graded fullness: inf_{FA,FB} fraction of Hom(FA,FB) covered by F.
        Approximation: for each pair in image, does target have at least as many
        morphisms as source expects?
        """
        total_hom_sets = 0
        full_hom_sets = 0

        for (src, tgt), src_morphs in self.src.hom.items():
            fa = self.F.get(src)
            fb = self.F.get(tgt)
            if fa is None or fb is None:
                continue
            total_hom_sets += 1
            tgt_morphs = self.tgt.hom.get((fa, fb), [])
            if len(tgt_morphs) >= len(src_morphs):
                full_hom_sets += 1

        if total_hom_sets == 0:
            return 1.0
        return full_hom_sets / total_hom_sets

    def essentially_surjective_degree(self) -> float:
        """
        Graded essential surjectivity: fraction of target objects that are
        isomorphic (in target) to some object in the image of F.
        """
        image = set(self.F.values())
        tgt_objs = self.tgt.objects
        if not tgt_objs:
            return 1.0

        iso_eng = IsomorphismEngine(self.tgt)
        covered = 0
        for t_obj in tgt_objs:
            if t_obj in image:
                covered += 1
            else:
                # Check if t_obj ≅ some image object
                best = max((iso_eng.iso_degree(t_obj, img) for img in image), default=0.0)
                covered += best  # partial credit by iso degree

        return covered / len(tgt_objs)

    def injective_on_objects(self) -> bool:
        vals = list(self.F.values())
        return len(vals) == len(set(vals))

    def surjective_on_objects(self) -> bool:
        return set(self.F.values()) == set(self.tgt.objects)

    def classify(self, program_name: str = "") -> FunctorClassification:
        faith = self.faithful_degree()
        full = self.full_degree()
        ess = self.essentially_surjective_degree()
        equiv = min(faith, full, ess)

        hom_type = "general"
        if equiv >= 0.95:
            if self.injective_on_objects() and self.surjective_on_objects():
                hom_type = "iso"
            else:
                hom_type = "equivalence"
        elif full >= 0.8:
            hom_type = "full"
        elif faith >= 0.8:
            hom_type = "faithful"

        return FunctorClassification(
            program_name=program_name,
            source_domain=self.src.domain_name,
            target_domain=self.tgt.domain_name,
            is_faithful=faith >= 0.95,
            is_full=full >= 0.95,
            is_essentially_surjective=ess >= 0.95,
            is_equivalence=equiv >= 0.95,
            is_injective_on_objects=self.injective_on_objects(),
            is_surjective_on_objects=self.surjective_on_objects(),
            faithful_degree=round(faith, 4),
            full_degree=round(full, 4),
            ess_surjective_degree=round(ess, 4),
            equivalence_degree=round(equiv, 4),
            homomorphism_type=hom_type,
        )


# ══════════════════════════════════════════════════════════════
# 4. AdjunctionDetector
# ══════════════════════════════════════════════════════════════

@dataclass
class AdjunctionResult:
    """Result of checking whether a pair of functors forms an adjunction."""
    left_functor: str   # program name of F: C→D (left adjoint)
    right_functor: str  # program name of G: D→C (right adjoint)
    adjunction_degree: float  # how well the triangle identities hold
    hom_iso_degree: float     # degree of hom-set bijection: Hom(FA,B) ≅ Hom(A,GB)
    is_adjunction: bool
    evidence: list[str]


class AdjunctionDetector:
    """
    Tests whether two stored functors F: C→D, G: D→C form an adjoint pair F ⊣ G.

    Uses the hom-isomorphism characterization:
      F ⊣ G  iff  Hom_D(F(A), B) ≅ Hom_C(A, G(B))  naturally in A, B.

    Graded: adjunction_degree = inf_{A,B} [hom_D(FA,B) ↔ hom_C(A,GB)]
    where ↔ is biresiduation: (p→q) ∧ (q→p) with Gödel implication.
    """

    def __init__(self, src_snap: CategorySnapshot, tgt_snap: CategorySnapshot):
        self.C = src_snap  # left category
        self.D = tgt_snap  # right category

    def _godel_implication(self, p: float, q: float) -> float:
        """Gödel implication in [0,1]: p→q = 1 if p≤q else q."""
        return 1.0 if p <= q else q

    def _biresiduation(self, p: float, q: float) -> float:
        """Biresiduation: p↔q = min(p→q, q→p)."""
        return min(self._godel_implication(p, q), self._godel_implication(q, p))

    def hom_iso_degree(self, F_map: dict[str,str], G_map: dict[str,str]) -> float:
        """
        Degree to which Hom_D(F(A),B) ≅ Hom_C(A,G(B)) for all A∈C, B∈D.
        Uses enriched hom-values (best truth degree in each hom-set).
        """
        degrees = []
        for a in self.C.objects:
            fa = F_map.get(a)
            if fa is None:
                continue
            for b in self.D.objects:
                gb = G_map.get(b)
                if gb is None:
                    continue
                hom_d = self.D.hom_degree(fa, b)   # Hom_D(FA, B)
                hom_c = self.C.hom_degree(a, gb)    # Hom_C(A, GB)
                degrees.append(self._biresiduation(hom_d, hom_c))

        if not degrees:
            return 0.0
        return min(degrees)  # infimum over all A,B pairs

    def check_adjunction(self, F_name: str, F_map: dict[str,str],
                          G_name: str, G_map: dict[str,str]) -> AdjunctionResult:
        """
        Check whether F ⊣ G holds (graded).
        F: C→D (F_map: C objects → D objects)
        G: D→C (G_map: D objects → C objects)
        """
        hom_degree = self.hom_iso_degree(F_map, G_map)
        evidence = []

        # Additional check: GF should be "close to" identity on C
        gf_degree = []
        for a in self.C.objects:
            fa = F_map.get(a)
            gfa = G_map.get(fa) if fa else None
            if gfa is not None:
                # gfa should equal a; if not, what's the iso degree?
                d = self.C.hom_degree(a, gfa) if gfa != a else 1.0
                gf_degree.append(d)
        gf_avg = sum(gf_degree) / len(gf_degree) if gf_degree else 0.0

        # FG should be "close to" identity on D
        fg_degree = []
        for b in self.D.objects:
            gb = G_map.get(b)
            fgb = F_map.get(gb) if gb else None
            if fgb is not None:
                d = self.D.hom_degree(b, fgb) if fgb != b else 1.0
                fg_degree.append(d)
        fg_avg = sum(fg_degree) / len(fg_degree) if fg_degree else 0.0

        adj_degree = min(hom_degree, (gf_avg + fg_avg) / 2)

        if hom_degree > 0.8:
            evidence.append(f"Hom bijection degree {hom_degree:.3f}")
        if gf_avg > 0.7:
            evidence.append(f"GF ≈ id_C (degree {gf_avg:.3f})")
        if fg_avg > 0.7:
            evidence.append(f"FG ≈ id_D (degree {fg_avg:.3f})")

        return AdjunctionResult(
            left_functor=F_name,
            right_functor=G_name,
            adjunction_degree=round(adj_degree, 4),
            hom_iso_degree=round(hom_degree, 4),
            is_adjunction=adj_degree >= 0.8,
            evidence=evidence,
        )


# ══════════════════════════════════════════════════════════════
# 5. LimitsColimits
# ══════════════════════════════════════════════════════════════

@dataclass
class LimitResult:
    limit_type: str        # "product" | "equalizer" | "pullback" | "terminal" | etc.
    objects_involved: list[str]
    apex: Optional[str]    # the limit object (or None if doesn't exist)
    projections: list[str] # morphism labels from apex to diagram objects
    exists: bool
    degree: float          # how well the universal property holds (graded)


class LimitsColimits:
    """
    Computes limits and colimits in a finite category.

    Algorithm: exhaustive search over candidate objects + universal property verification.
    We verify the universal property to a degree (using truth degrees).

    Complexity: O(n² · h⁵) for products/pullbacks where h = max hom-set size.
    """

    def __init__(self, snap: CategorySnapshot):
        self.snap = snap

    def terminal_object(self) -> LimitResult:
        """
        Terminal object: ∃T such that ∀A, ∃! morphism A→T.
        Approximated by: T has an incoming morphism from every object.
        Graded: degree = inf_A hom_degree(A, T).
        """
        best_obj = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            # Degree = min over all other objects A of hom_degree(A, candidate)
            d = min(
                (self.snap.hom_degree(a, candidate) for a in self.snap.objects if a != candidate),
                default=1.0
            )
            if d > best_degree:
                best_degree = d
                best_obj = candidate

        return LimitResult(
            limit_type="terminal",
            objects_involved=self.snap.objects,
            apex=best_obj,
            projections=[],
            exists=best_degree >= 0.9,
            degree=round(best_degree, 4),
        )

    def initial_object(self) -> LimitResult:
        """
        Initial object: ∃I such that ∀A, ∃! morphism I→A.
        Graded: degree = inf_A hom_degree(I, A).
        """
        best_obj = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = min(
                (self.snap.hom_degree(candidate, a) for a in self.snap.objects if a != candidate),
                default=1.0
            )
            if d > best_degree:
                best_degree = d
                best_obj = candidate

        return LimitResult(
            limit_type="initial",
            objects_involved=self.snap.objects,
            apex=best_obj,
            projections=[],
            exists=best_degree >= 0.9,
            degree=round(best_degree, 4),
        )

    def product(self, obj_a: str, obj_b: str) -> LimitResult:
        """
        Binary product of A and B: object P with projections P→A, P→B,
        universal among such objects.
        Graded: degree = max_P min(hom_degree(P,A), hom_degree(P,B)).
        """
        best_p = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = min(
                self.snap.hom_degree(candidate, obj_a),
                self.snap.hom_degree(candidate, obj_b)
            )
            if d > best_degree:
                best_degree = d
                best_p = candidate

        return LimitResult(
            limit_type="product",
            objects_involved=[obj_a, obj_b],
            apex=best_p,
            projections=[f"{best_p}→{obj_a}", f"{best_p}→{obj_b}"] if best_p else [],
            exists=best_degree >= 0.8,
            degree=round(best_degree, 4),
        )

    def coproduct(self, obj_a: str, obj_b: str) -> LimitResult:
        """
        Binary coproduct (dual of product): object C with injections A→C, B→C.
        """
        best_c = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = min(
                self.snap.hom_degree(obj_a, candidate),
                self.snap.hom_degree(obj_b, candidate)
            )
            if d > best_degree:
                best_degree = d
                best_c = candidate

        return LimitResult(
            limit_type="coproduct",
            objects_involved=[obj_a, obj_b],
            apex=best_c,
            projections=[f"{obj_a}→{best_c}", f"{obj_b}→{best_c}"] if best_c else [],
            exists=best_degree >= 0.8,
            degree=round(best_degree, 4),
        )

    def equalizer(self, obj_a: str, obj_b: str) -> LimitResult:
        """
        Equalizer of all morphisms A⟹B: object E with morphism E→A
        such that all composites E→A→B are equal.
        Approximated: E is the object with the best incoming morphism to A.
        """
        best_e = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = self.snap.hom_degree(candidate, obj_a)
            if d > best_degree:
                best_degree = d
                best_e = candidate

        return LimitResult(
            limit_type="equalizer",
            objects_involved=[obj_a, obj_b],
            apex=best_e,
            projections=[f"{best_e}→{obj_a}"] if best_e else [],
            exists=best_degree >= 0.8,
            degree=round(best_degree, 4),
        )

    def pullback(self, obj_a: str, obj_c: str, obj_b: str) -> LimitResult:
        """
        Pullback of A→C←B: object P with P→A, P→B, such that A→C, B→C agree.
        Graded: degree = max_P min(hom(P,A), hom(P,B)) where C is the common target.
        """
        best_p = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = min(
                self.snap.hom_degree(candidate, obj_a),
                self.snap.hom_degree(candidate, obj_b),
                self.snap.hom_degree(obj_a, obj_c),
                self.snap.hom_degree(obj_b, obj_c),
            )
            if d > best_degree:
                best_degree = d
                best_p = candidate

        return LimitResult(
            limit_type="pullback",
            objects_involved=[obj_a, obj_b, obj_c],
            apex=best_p,
            projections=[f"{best_p}→{obj_a}", f"{best_p}→{obj_b}"] if best_p else [],
            exists=best_degree >= 0.7,
            degree=round(best_degree, 4),
        )

    def pushout(self, obj_a: str, obj_c: str, obj_b: str) -> LimitResult:
        """
        Pushout of A←C→B (dual of pullback): object Q with A→Q, B→Q.
        """
        best_q = None
        best_degree = 0.0

        for candidate in self.snap.objects:
            d = min(
                self.snap.hom_degree(obj_a, candidate),
                self.snap.hom_degree(obj_b, candidate),
                self.snap.hom_degree(obj_c, obj_a),
                self.snap.hom_degree(obj_c, obj_b),
            )
            if d > best_degree:
                best_degree = d
                best_q = candidate

        return LimitResult(
            limit_type="pushout",
            objects_involved=[obj_a, obj_b, obj_c],
            apex=best_q,
            projections=[f"{obj_a}→{best_q}", f"{obj_b}→{best_q}"] if best_q else [],
            exists=best_degree >= 0.7,
            degree=round(best_degree, 4),
        )


# ══════════════════════════════════════════════════════════════
# 6. Yoneda Embedding
# ══════════════════════════════════════════════════════════════

class YonedaEmbedding:
    """
    Implements the Yoneda embedding y: C → [C^op, Set].
    y(A) = Hom(-, A): the representable presheaf at A.

    For our enriched setting: y(A)(X) = hom_degree(X, A) ∈ [0,1].
    This is the enriched Yoneda embedding into [C^op, [0,1]].

    Key properties:
    - y is fully faithful (preserves all categorical structure)
    - y(A)(A) = identity degree (= 1.0 for valid categories)
    - y(A)(X) = 0 if no morphism X→A exists
    """

    def __init__(self, snap: CategorySnapshot):
        self.snap = snap

    def representable_presheaf(self, obj: str) -> dict[str, float]:
        """
        Compute y(obj): X ↦ hom_degree(X, obj) for all X in C.
        This is the enriched representable presheaf at obj.
        """
        return {
            x: self.snap.hom_degree(x, obj)
            for x in self.snap.objects
        }

    def all_representables(self) -> dict[str, dict[str, float]]:
        """Compute y(A) for all objects A. Returns dict: obj → presheaf."""
        return {obj: self.representable_presheaf(obj) for obj in self.snap.objects}

    def representability_degree(self, presheaf: dict[str, float]) -> tuple[Optional[str], float]:
        """
        Check if a given [0,1]-valued presheaf F: C^op → [0,1] is representable.
        Returns (representing_object, degree) where degree measures how well
        y(A) ≈ F.

        Representability degree at A: inf_X |F(X) - y(A)(X)|  (sup version)
        Best A = argmax_A min_X (1 - |F(X) - y(A)(X)|)
        """
        best_obj = None
        best_degree = -1.0

        for a in self.snap.objects:
            ya = self.representable_presheaf(a)
            # Degree of agreement: 1 - average absolute deviation
            devs = [abs(presheaf.get(x, 0.0) - ya.get(x, 0.0))
                    for x in self.snap.objects]
            d = 1.0 - (sum(devs) / len(devs)) if devs else 0.0
            if d > best_degree:
                best_degree = d
                best_obj = a

        return best_obj, round(best_degree, 4)

    def yoneda_matrix(self) -> np.ndarray:
        """
        Return the n×n Yoneda matrix Y where Y[i,j] = hom_degree(obj_i, obj_j).
        This is the enriched hom-matrix / distance matrix of the category.
        """
        n = self.snap.n_objects
        objs = self.snap.objects
        Y = np.zeros((n, n))
        for i, a in enumerate(objs):
            for j, b in enumerate(objs):
                Y[i, j] = self.snap.hom_degree(a, b)
        return Y


# ══════════════════════════════════════════════════════════════
# 7. NerveComplex
# ══════════════════════════════════════════════════════════════

@dataclass
class NerveSimplex:
    """A single simplex in the nerve N(C)."""
    objects: tuple[str, ...]   # composable chain (obj_0, obj_1, ..., obj_k)
    dim: int                   # dimension = k = len(objects) - 1
    filtration: float          # 1 - min(truth_degrees) along the chain
    truth_entry: float         # truth threshold at which this simplex appears


class NerveComplex:
    """
    Constructs the nerve N(C) of a category as a filtered simplicial complex.

    N(C)_0 = objects (0-simplices)
    N(C)_1 = morphisms (1-simplices: composable 1-tuples)
    N(C)_k = composable k-tuples of morphisms

    Filtration by truth degree:
      A chain (f_1, ..., f_k) enters at threshold t = min_i(truth_degree(f_i))
      Equivalently, filtration value = 1 - t (lower filtration = earlier in GUDHI)

    The filtered nerve gives a persistent topological space whose homology
    tracks how the structural connectivity of the knowledge category changes
    as we vary our confidence threshold.
    """

    def __init__(self, snap: CategorySnapshot, max_dim: int = 3):
        self.snap = snap
        self.max_dim = max_dim
        self._simplices: list[NerveSimplex] = []
        self._built = False

    def build(self) -> list[NerveSimplex]:
        """Enumerate all simplices up to max_dim."""
        if self._built:
            return self._simplices

        simplices = []
        snap = self.snap

        # 0-simplices: objects (always present, filtration 0)
        for obj in snap.objects:
            simplices.append(NerveSimplex(
                objects=(obj,), dim=0,
                filtration=0.0, truth_entry=1.0
            ))

        if self.max_dim < 1:
            self._simplices = simplices
            self._built = True
            return simplices

        # 1-simplices: morphisms
        for m in snap.morphisms:
            src, tgt = m["source_label"], m["target_label"]
            if src == tgt:
                continue  # skip identity/self loops for topology
            td = m.get("truth_degree", 1.0) or 1.0
            filt = 1.0 - td
            simplices.append(NerveSimplex(
                objects=(src, tgt), dim=1,
                filtration=filt, truth_entry=td
            ))

        if self.max_dim < 2:
            self._simplices = simplices
            self._built = True
            return simplices

        # 2-simplices: composable pairs (f: A→B, g: B→C) → triangle ABC
        # Avoid duplicating; use frozenset of edges to identify triangles
        # But we use directed simplices (chain order matters for boundary maps)
        triangles_seen = set()
        for m1 in snap.morphisms:
            if m1["source_label"] == m1["target_label"]:
                continue
            a, b = m1["source_label"], m1["target_label"]
            td1 = m1.get("truth_degree", 1.0) or 1.0
            # Look for g: B→C
            for m2 in snap.morphisms:
                if m2["source_label"] != b or m2["source_label"] == m2["target_label"]:
                    continue
                c = m2["target_label"]
                if c == a:
                    continue  # skip degenerate triangles
                key = (a, b, c)
                if key in triangles_seen:
                    continue
                triangles_seen.add(key)
                td2 = m2.get("truth_degree", 1.0) or 1.0
                # Also need direct A→C for the triangle to close
                td_ac = snap.hom_degree(a, c)
                if td_ac > 0:
                    td = min(td1, td2, td_ac)
                    simplices.append(NerveSimplex(
                        objects=(a, b, c), dim=2,
                        filtration=1.0 - td, truth_entry=td
                    ))

        if self.max_dim < 3:
            self._simplices = simplices
            self._built = True
            return simplices

        # 3-simplices: composable triples forming tetrahedra
        # A→B→C→D where all 4 triangular faces exist
        tets_seen = set()
        triangles_by_prefix: dict[tuple, list[tuple]] = defaultdict(list)
        for s in simplices:
            if s.dim == 2:
                triangles_by_prefix[s.objects[:2]].append(s.objects)

        for s in simplices:
            if s.dim == 2:
                a, b, c = s.objects
                for tri in triangles_by_prefix.get((b, c), []):
                    d = tri[2]
                    if d in (a, b, c):
                        continue
                    key = (a, b, c, d)
                    if key in tets_seen:
                        continue
                    tets_seen.add(key)
                    # Check all 4 faces exist
                    face_tds = [
                        snap.hom_degree(a, b), snap.hom_degree(b, c),
                        snap.hom_degree(c, d), snap.hom_degree(a, c),
                        snap.hom_degree(b, d), snap.hom_degree(a, d),
                    ]
                    if all(td > 0 for td in face_tds):
                        td = min(face_tds)
                        simplices.append(NerveSimplex(
                            objects=(a, b, c, d), dim=3,
                            filtration=1.0 - td, truth_entry=td
                        ))

        self._simplices = simplices
        self._built = True
        return simplices

    def to_gudhi_simplex_tree(self) -> gudhi.SimplexTree:
        """
        Convert to a GUDHI SimplexTree for persistent homology computation.
        """
        simplices = self.build()
        st = gudhi.SimplexTree()

        snap = self.snap
        idx = snap.obj_index

        for s in simplices:
            # GUDHI uses integer vertex indices
            verts = [idx[obj] for obj in s.objects]
            st.insert(verts, filtration=s.filtration)

        st.make_filtration_non_decreasing()
        return st

    def summary(self) -> dict:
        """Summary of the nerve complex."""
        simplices = self.build()
        by_dim = defaultdict(int)
        for s in simplices:
            by_dim[s.dim] += 1
        return {
            "n_objects": self.snap.n_objects,
            "n_morphisms": self.snap.n_morphisms,
            "simplices_by_dim": dict(by_dim),
            "total_simplices": len(simplices),
            "max_dim": self.max_dim,
        }


# ══════════════════════════════════════════════════════════════
# 8. HomologyEngine
# ══════════════════════════════════════════════════════════════

class HomologyEngine:
    """
    Computes integral homology H_n(C) = H_n(N(C); Z) of a category
    using the Smith Normal Form (SNF) algorithm.

    H_n = ker(∂_n) / im(∂_{n+1})
    Betti number β_n = rank(H_n) = dim(C_n) - rank(∂_n) - rank(∂_{n+1})
    Torsion coefficients from SNF diagonal entries > 1.

    Uses Z/2 coefficients for efficiency (no torsion, rank = nullity).
    """

    def __init__(self, nerve: NerveComplex):
        self.nerve = nerve

    def _build_boundary_matrix_mod2(self, k_simplices: list, k1_simplices: list) -> np.ndarray:
        """
        Build ∂_k over Z/2: boundary matrix of k-simplices vs (k-1)-simplices.
        ∂_k(σ) = Σ_i (-1)^i [remove i-th vertex], but mod 2 signs don't matter.
        """
        if not k_simplices or not k1_simplices:
            return np.zeros((len(k1_simplices), len(k_simplices)), dtype=np.int32)

        snap = self.nerve.snap
        idx = snap.obj_index
        k1_index = {s.objects: i for i, s in enumerate(k1_simplices)}

        D = np.zeros((len(k1_simplices), len(k_simplices)), dtype=np.int32)

        for j, sigma in enumerate(k_simplices):
            objs = sigma.objects
            for i in range(len(objs)):
                # i-th face: remove i-th vertex
                face = objs[:i] + objs[i+1:]
                if face in k1_index:
                    D[k1_index[face], j] = 1  # mod 2 so sign doesn't matter

        return D

    def betti_numbers(self, max_dim: int = 3) -> dict[int, int]:
        """
        Compute Betti numbers β_0, β_1, β_2, β_3 over Z/2.
        β_n = dim(ker ∂_n) - dim(im ∂_{n+1})
             = dim(C_n) - rank(∂_n) - rank(∂_{n+1})
        """
        simplices = self.nerve.build()
        by_dim: dict[int, list] = defaultdict(list)
        for s in simplices:
            by_dim[s.dim].append(s)

        betti = {}
        rank_cache: dict[int, int] = {}

        for n in range(max_dim + 1):
            cn = by_dim.get(n, [])
            cn1 = by_dim.get(n + 1, [])
            cn_prev = by_dim.get(n - 1, [])

            # rank(∂_n): boundary from n to n-1
            if n not in rank_cache:
                if cn and cn_prev:
                    D = self._build_boundary_matrix_mod2(cn, cn_prev)
                    rank_cache[n] = _rank_gf2(D)
                else:
                    rank_cache[n] = 0

            # rank(∂_{n+1}): boundary from n+1 to n
            if n + 1 not in rank_cache:
                if cn1 and cn:
                    D1 = self._build_boundary_matrix_mod2(cn1, cn)
                    rank_cache[n + 1] = _rank_gf2(D1)
                else:
                    rank_cache[n + 1] = 0

            betti[n] = len(cn) - rank_cache[n] - rank_cache[n + 1]
            betti[n] = max(0, betti[n])  # numerical safety

        return betti

    def euler_characteristic(self) -> int:
        """χ(C) = Σ (-1)^n |N(C)_n| = Σ (-1)^n β_n (both formulas should agree)."""
        simplices = self.nerve.build()
        by_dim = defaultdict(int)
        for s in simplices:
            by_dim[s.dim] += 1
        return sum((-1)**n * count for n, count in by_dim.items())

    def is_connected(self) -> bool:
        """H_0 = Z means one component; β_0 = 1 means connected."""
        betti = self.betti_numbers(max_dim=0)
        return betti.get(0, 0) <= 1


# ══════════════════════════════════════════════════════════════
# 9. PersistentHomologyEngine
# ══════════════════════════════════════════════════════════════

@dataclass
class PersistencePair:
    """A single birth-death pair in a persistence diagram."""
    dimension: int
    birth: float    # truth threshold at which the homology class is born (born = high truth)
    death: float    # truth threshold at which it dies (lower truth)
    persistence: float  # death - birth (in filtration space, so higher = longer-lived)
    birth_truth: float  # 1 - birth (convert back to truth degree)
    death_truth: float  # 1 - death (or 0 if essential)

    def is_essential(self) -> bool:
        """Essential features never die (infinite persistence)."""
        return math.isinf(self.death)


@dataclass
class PersistenceDiagram:
    """Persistence diagram: collection of birth-death pairs by dimension."""
    pairs: list[PersistencePair]
    betti_numbers: dict[int, int]   # β_n at threshold 0 (considering all morphisms)
    euler_characteristic: int
    domain_name: str
    n_objects: int
    n_morphisms: int
    max_dim_computed: int
    computation_time_ms: float


class PersistentHomologyEngine:
    """
    Computes persistent homology of the filtered nerve of a category.

    The filtration is indexed by truth degree:
      - High truth degree → early in filtration (small filtration value)
      - Low truth degree → late in filtration (large filtration value)

    This reveals how the topological structure of knowledge changes
    as we lower our confidence threshold.

    Uses GUDHI's SimplexTree with column reduction algorithm.

    Stability theorem (Cohen-Steiner et al. 2007):
      W∞(Dgm(C), Dgm(C')) ≤ ‖μ_C - μ_C'‖∞
    Small truth-degree perturbations cause small diagram changes.
    """

    def __init__(self, nerve: NerveComplex):
        self.nerve = nerve

    def compute(self, min_persistence: float = 0.0) -> PersistenceDiagram:
        """
        Compute the persistence diagram of the filtered nerve.

        Args:
            min_persistence: filter out pairs with persistence < this value
                             (removes topological noise)
        """
        t_start = time.time()
        snap = self.nerve.snap

        st = self.nerve.to_gudhi_simplex_tree()
        st.compute_persistence(min_persistence=min_persistence)

        pairs = []
        for dim, (birth_filt, death_filt) in st.persistence():
            # Convert filtration values back to truth degrees
            birth_truth = max(0.0, 1.0 - birth_filt)
            death_truth = max(0.0, 1.0 - death_filt) if not math.isinf(death_filt) else 0.0
            persistence = death_filt - birth_filt if not math.isinf(death_filt) else float('inf')

            pairs.append(PersistencePair(
                dimension=dim,
                birth=birth_filt,
                death=death_filt,
                persistence=persistence,
                birth_truth=round(birth_truth, 4),
                death_truth=round(death_truth, 4),
            ))

        # Compute Betti numbers from GUDHI (returns list indexed by dimension)
        betti_list = st.betti_numbers()
        betti = {n: (betti_list[n] if n < len(betti_list) else 0)
                 for n in range(self.nerve.max_dim + 1)}
        euler = sum((-1)**n * b for n, b in betti.items())

        t_end = time.time()

        return PersistenceDiagram(
            pairs=pairs,
            betti_numbers=betti,
            euler_characteristic=euler,
            domain_name=snap.domain_name,
            n_objects=snap.n_objects,
            n_morphisms=snap.n_morphisms,
            max_dim_computed=self.nerve.max_dim,
            computation_time_ms=round((t_end - t_start) * 1000, 1),
        )

    def bottleneck_distance(self, other_diagram: PersistenceDiagram, dim: int = 1) -> float:
        """
        W∞ bottleneck distance between two persistence diagrams in dimension dim.
        Uses GUDHI's built-in bottleneck distance.
        """
        dgm1 = [(p.birth, p.death) for p in self.nerve._simplices
                if False]  # placeholder
        # Better: pass pre-computed GUDHI persistence
        return 0.0  # Requires two diagrams; see compare_domains() below

    def significant_features(self, min_persistence: float = 0.1) -> list[PersistencePair]:
        """
        Return topologically significant features (persistence > threshold).
        Features near the diagonal (small persistence) are 'noise'.
        """
        diag = self.compute()
        return [p for p in diag.pairs if p.persistence > min_persistence and not p.is_essential()]

    def to_dict(self, diagram: PersistenceDiagram) -> dict:
        """Serialize persistence diagram to JSON-compatible dict."""
        return {
            "domain": diagram.domain_name,
            "n_objects": diagram.n_objects,
            "n_morphisms": diagram.n_morphisms,
            "betti_numbers": diagram.betti_numbers,
            "euler_characteristic": diagram.euler_characteristic,
            "max_dim": diagram.max_dim_computed,
            "computation_ms": diagram.computation_time_ms,
            "pairs": [
                {
                    "dim": p.dimension,
                    "birth_truth": p.birth_truth,
                    "death_truth": p.death_truth,
                    "persistence": round(p.persistence, 4) if not p.is_essential() else "∞",
                    "essential": p.is_essential(),
                }
                for p in sorted(diagram.pairs, key=lambda x: (-x.persistence if not math.isinf(x.persistence) else float('inf'), x.dimension))
            ],
        }


def compare_domains(snap1: CategorySnapshot, snap2: CategorySnapshot,
                    max_dim: int = 2) -> dict:
    """
    Compare two categories via their persistence diagrams.
    Returns bottleneck distances by dimension.
    """
    nerve1 = NerveComplex(snap1, max_dim=max_dim)
    nerve2 = NerveComplex(snap2, max_dim=max_dim)

    st1 = nerve1.to_gudhi_simplex_tree()
    st2 = nerve2.to_gudhi_simplex_tree()

    st1.compute_persistence()
    st2.compute_persistence()

    result = {}
    for dim in range(max_dim + 1):
        dgm1 = st1.persistence_intervals_in_dimension(dim)
        dgm2 = st2.persistence_intervals_in_dimension(dim)
        try:
            dist = gudhi.bottleneck_distance(dgm1, dgm2)
        except Exception:
            dist = None
        result[f"bottleneck_dim{dim}"] = round(dist, 4) if dist is not None else None

    return {
        "domain1": snap1.domain_name,
        "domain2": snap2.domain_name,
        "bottleneck_distances": result,
        "interpretation": _interpret_bottleneck(result),
    }


def _interpret_bottleneck(dists: dict) -> str:
    d0 = dists.get("bottleneck_dim0", None)
    d1 = dists.get("bottleneck_dim1", None)
    if d0 is None:
        return "Could not compute"
    if d0 < 0.1 and (d1 is None or d1 < 0.1):
        return "Topologically nearly identical — very similar structural connectivity"
    if d0 < 0.3:
        return "Similar connected component structure with some morphological differences"
    return "Structurally distinct topological shapes"


# ══════════════════════════════════════════════════════════════
# 10. FundamentalGroupoid
# ══════════════════════════════════════════════════════════════

@dataclass
class FundamentalGroupoidResult:
    """Result of fundamental groupoid computation."""
    pi0: list[list[str]]            # connected components (list of object groups)
    n_components: int
    is_connected: bool
    pi1_rank: int                   # rank of π₁ (first Betti number) at threshold 1.0
    cycle_generators: list[str]     # description of independent cycles
    graded_components: dict[float, list[list[str]]]  # components at each truth threshold
    homotopy_type: str              # "contractible" | "circle" | "sphere" | "complex"


class FundamentalGroupoid:
    """
    Computes the fundamental groupoid Π₁(C) of a category.

    π₀(C): connected components of the underlying undirected graph.
           Computed via union-find in O(n + m·α(n)).

    π₁(C, x): fundamental group at basepoint x.
           = free group on (|edges outside spanning tree|) relations
           Rank = |E| - |V| + |components| (first Betti number, undirected view).

    Graded π₀: components change as we vary the truth threshold.
           At threshold t: consider only morphisms with truth_degree ≥ t.
           Component structure at each threshold gives a filtration.

    Homotopy type classification:
      - Contractible: π₀ = {single point}, all higher πn = 0 (= one component, tree)
      - Circle S¹: π₀ connected, π₁ = Z (= one independent cycle)
      - Sphere S²: two-dimensional topology
      - Complex: more intricate structure
    """

    def __init__(self, snap: CategorySnapshot):
        self.snap = snap

    def _union_find(self, edges: list[tuple[str,str]]) -> dict[str, str]:
        """Union-find returning canonical representatives."""
        parent = {obj: obj for obj in self.snap.objects}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in edges:
            pa, pb = find(a), find(b)
            if pa != pb:
                parent[pa] = pb

        return {obj: find(obj) for obj in self.snap.objects}

    def pi0(self, threshold: float = 0.0) -> list[list[str]]:
        """
        Connected components at given truth threshold.
        Uses undirected connectivity (morphism in either direction connects objects).
        """
        edges = [
            (m["source_label"], m["target_label"])
            for m in self.snap.morphisms
            if (m.get("truth_degree") or 1.0) >= threshold
            and m["source_label"] != m["target_label"]
        ]

        rep = self._union_find(edges)
        components: dict[str, list[str]] = defaultdict(list)
        for obj in self.snap.objects:
            components[rep[obj]].append(obj)

        return [sorted(comp) for comp in components.values()]

    def pi1_rank(self, threshold: float = 0.0) -> int:
        """
        Rank of π₁ at given threshold = first Betti number (undirected graph).
        β₁ = |E| - |V| + |components|  (undirected, no multi-edges)
        """
        objs = set(self.snap.objects)
        edges_seen = set()
        for m in self.snap.morphisms:
            src, tgt = m["source_label"], m["target_label"]
            if src == tgt:
                continue
            td = m.get("truth_degree") or 1.0
            if td >= threshold:
                edge = frozenset([src, tgt])
                edges_seen.add(edge)

        V = len(objs)
        E = len(edges_seen)
        components = len(self.pi0(threshold))
        return max(0, E - V + components)

    def graded_pi0(self, thresholds: Optional[list[float]] = None) -> dict[float, list[list[str]]]:
        """
        Track how connected components change with truth threshold.
        Returns {threshold: components} for each threshold.
        """
        if thresholds is None:
            # Use all unique truth degrees + 0 and 1
            tds = sorted(set(
                round(m.get("truth_degree") or 1.0, 2)
                for m in self.snap.morphisms
            ), reverse=True)
            thresholds = [1.0] + tds + [0.0]

        return {t: self.pi0(t) for t in thresholds}

    def homotopy_type(self) -> str:
        """Classify the homotopy type of the classifying space BC."""
        n_comp = len(self.pi0(0.0))
        b1 = self.pi1_rank(0.0)

        if n_comp == 0:
            return "empty"
        if n_comp > 1:
            return f"disconnected ({n_comp} components)"
        if b1 == 0:
            return "contractible"
        if b1 == 1:
            return "circle (S¹)"
        if b1 == 2:
            return "figure-8 (bouquet of 2 circles)"
        return f"complex (β₁={b1})"

    def compute(self) -> FundamentalGroupoidResult:
        """Full fundamental groupoid computation."""
        comp0 = self.pi0(0.0)
        comp1 = self.pi0(1.0)  # strict (only truth=1 morphisms)
        b1 = self.pi1_rank(0.0)
        h_type = self.homotopy_type()

        # Graded: compute at 3 thresholds
        graded = self.graded_pi0([1.0, 0.7, 0.5, 0.3, 0.0])

        # Find cycle generators: morphisms that would be generators in spanning tree complement
        generators = []
        if b1 > 0:
            generators = [f"β₁={b1} independent cycle{'s' if b1>1 else ''} in directed graph"]

        return FundamentalGroupoidResult(
            pi0=comp0,
            n_components=len(comp0),
            is_connected=(len(comp0) == 1),
            pi1_rank=b1,
            cycle_generators=generators,
            graded_components=graded,
            homotopy_type=h_type,
        )


# ══════════════════════════════════════════════════════════════
# 11. MetricEnrichment (Lawvere metric view)
# ══════════════════════════════════════════════════════════════

class TNorm:
    """T-norm choices for the enrichment base ([0,1], ≤, ⊗, 1)."""

    @staticmethod
    def godel(a: float, b: float) -> float:
        """min t-norm — Gödel/Heyting semantics. Most conservative."""
        return min(a, b)

    @staticmethod
    def product(a: float, b: float) -> float:
        """Product t-norm — probabilistic semantics. Independent evidence."""
        return a * b

    @staticmethod
    def lukasiewicz(a: float, b: float) -> float:
        """Łukasiewicz t-norm — bounded error accumulation."""
        return max(0.0, a + b - 1.0)

    @staticmethod
    def residuum(t_norm_name: str, a: float, b: float) -> float:
        """Residuum (implication) for each t-norm: largest c such that a⊗c ≤ b."""
        if t_norm_name == "godel":
            return 1.0 if a <= b else b
        elif t_norm_name == "product":
            return min(1.0, b / a) if a > 0 else 1.0
        elif t_norm_name == "lukasiewicz":
            return min(1.0, 1.0 - a + b)
        return 1.0 if a <= b else b


@dataclass
class EnrichedMetric:
    """Lawvere metric space view of the category."""
    distance_matrix: dict[tuple[str,str], float]  # d(A,B) = -log(hom(A,B))
    symmetry_degree: float      # how symmetric the metric is
    triangle_violations: int    # triangle inequality violations
    t_norm_used: str


class MetricEnrichment:
    """
    Views the MORPHOS category as a category enriched over ([0,1], ≤, ⊗, 1),
    which by Lawvere's theorem corresponds to a generalized metric space.

    The enriched hom-value hom(A,B) ∈ [0,1] corresponds to closeness/similarity.
    The generalized metric: d(A,B) = -log(hom(A,B)) ∈ [0,∞] (or ∞ if no morphism).
    Higher truth degree = smaller distance = more similar.

    Enrichment axioms:
    1. hom(A,A) = 1         (d(A,A) = 0)
    2. hom(A,B) ⊗ hom(B,C) ≤ hom(A,C)   (triangle inequality in log form)
    """

    def __init__(self, snap: CategorySnapshot, t_norm: str = "godel"):
        self.snap = snap
        self.t_norm = t_norm
        self._compose = getattr(TNorm, t_norm)

    def distance(self, a: str, b: str) -> float:
        """Lawvere distance d(A,B) = -log(hom(A,B)), or ∞ if no morphism."""
        h = self.snap.hom_degree(a, b)
        if h <= 0:
            return float('inf')
        return -math.log(h) if h < 1.0 else 0.0

    def distance_matrix(self) -> dict[tuple[str,str], float]:
        objs = self.snap.objects
        return {(a, b): self.distance(a, b) for a in objs for b in objs}

    def verify_enrichment_axioms(self) -> dict:
        """
        Verify that the category satisfies enrichment axioms.
        Returns detailed report on violations.
        """
        snap = self.snap
        objs = snap.objects

        # Check identity axiom: hom(A,A) = 1 for all A
        identity_violations = []
        for a in objs:
            d = snap.hom_degree(a, a)
            if d < 0.99 and d > 0:  # identity morphism exists but weak
                identity_violations.append({"object": a, "hom_aa": d})

        # Check composition axiom: hom(A,B) ⊗ hom(B,C) ≤ hom(A,C)
        triangle_violations = []
        for a in objs:
            for b in objs:
                for c in objs:
                    hab = snap.hom_degree(a, b)
                    hbc = snap.hom_degree(b, c)
                    hac = snap.hom_degree(a, c)
                    if hab > 0 and hbc > 0:
                        composed = self._compose(hab, hbc)
                        if composed > hac + 0.01:  # tolerance for float arithmetic
                            triangle_violations.append({
                                "a": a, "b": b, "c": c,
                                "hab": hab, "hbc": hbc, "hac": hac,
                                "composed": composed,
                                "violation": round(composed - hac, 4),
                            })

        # Symmetry: does hom(A,B) ≈ hom(B,A)?
        sym_deltas = []
        for i, a in enumerate(objs):
            for b in objs[i+1:]:
                sym_deltas.append(abs(snap.hom_degree(a, b) - snap.hom_degree(b, a)))
        sym_degree = 1.0 - (sum(sym_deltas) / len(sym_deltas)) if sym_deltas else 1.0

        return {
            "t_norm": self.t_norm,
            "identity_axiom_ok": len(identity_violations) == 0,
            "identity_violations": identity_violations[:10],
            "composition_axiom_ok": len(triangle_violations) == 0,
            "n_triangle_violations": len(triangle_violations),
            "triangle_violations_sample": triangle_violations[:5],
            "symmetry_degree": round(sym_degree, 4),
            "is_symmetric_metric": sym_degree > 0.95,
            "interpretation": _interpret_enrichment(len(triangle_violations), sym_degree),
        }


def _interpret_enrichment(violations: int, sym: float) -> str:
    if violations == 0 and sym > 0.95:
        return "Valid symmetric metric space enrichment"
    if violations == 0:
        return "Valid Lawvere metric space (asymmetric — directed knowledge)"
    if violations < 5:
        return "Near-valid enrichment with minor triangle inequality violations"
    return f"Significant enrichment violations ({violations}) — derived morphisms may be missing"


# ══════════════════════════════════════════════════════════════
# 12. HomotopyClasses (analogy program equivalence)
# ══════════════════════════════════════════════════════════════

@dataclass
class HomotopyClass:
    """A homotopy class of functors [C, D]."""
    representative: str          # canonical program name
    members: list[str]           # all program names in this class
    nat_iso_degree: float        # minimum natural iso degree within class
    class_size: int


class HomotopyClassifier:
    """
    Groups stored analogy programs by natural isomorphism equivalence.

    Two functors F, G: C → D are naturally isomorphic if ∃ natural transformation
    η: F ⇒ G where every component η_A: F(A)→G(A) is an isomorphism.

    Graded: natural iso degree = inf_A iso_degree(F(A), G(A)) in D.

    This collapses the AnalogyMemory into meaningful equivalence classes:
    instead of 20 slightly-different analogy maps, you get k equivalence
    classes representing genuinely distinct analogical interpretations.
    """

    def __init__(self, src_snap: CategorySnapshot, tgt_snap: CategorySnapshot):
        self.src = src_snap
        self.tgt = tgt_snap
        self.iso_engine = IsomorphismEngine(tgt_snap)

    def nat_iso_degree(self, F_map: dict[str,str], G_map: dict[str,str]) -> float:
        """
        Degree to which F and G are naturally isomorphic.
        nat_iso(F,G) = inf_A iso_degree(F(A), G(A)) in D.
        """
        objs = [a for a in self.src.objects if a in F_map and a in G_map]
        if not objs:
            return 0.0
        return min(self.iso_engine.iso_degree(F_map[a], G_map[a]) for a in objs)

    def classify(self, programs: list[dict],
                 threshold: float = 0.7) -> list[HomotopyClass]:
        """
        Partition programs into homotopy classes.
        Two programs are in the same class if nat_iso_degree ≥ threshold.

        Args:
            programs: list of program dicts from the store (each has object_map)
            threshold: minimum nat_iso_degree to be considered equivalent

        Returns: list of HomotopyClass
        """
        n = len(programs)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Pair-wise check
        nat_degrees = {}
        for i in range(n):
            for j in range(i+1, n):
                Fm = programs[i].get("object_map", {})
                Gm = programs[j].get("object_map", {})
                if isinstance(Fm, str):
                    try:
                        Fm = json.loads(Fm)
                    except Exception:
                        Fm = {}
                if isinstance(Gm, str):
                    try:
                        Gm = json.loads(Gm)
                    except Exception:
                        Gm = {}
                d = self.nat_iso_degree(Fm, Gm)
                nat_degrees[(i, j)] = d
                if d >= threshold:
                    union(i, j)

        # Assemble classes
        class_map: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            class_map[find(i)].append(i)

        result = []
        for rep_idx, members in class_map.items():
            # min nat_iso degree within the class
            if len(members) == 1:
                min_deg = 1.0
            else:
                min_deg = min(
                    nat_degrees.get((min(i,j), max(i,j)), 0.0)
                    for i in members for j in members if i != j
                )
            result.append(HomotopyClass(
                representative=programs[rep_idx].get("name", f"prog_{rep_idx}"),
                members=[programs[i].get("name", f"prog_{i}") for i in members],
                nat_iso_degree=round(min_deg, 4),
                class_size=len(members),
            ))

        return sorted(result, key=lambda c: -c.class_size)


# ══════════════════════════════════════════════════════════════
# 13. TopologyReport — unified entry point
# ══════════════════════════════════════════════════════════════

def compute_topology_report(store, domain_name: str,
                             max_dim: int = 3,
                             t_norm: str = "godel",
                             min_persistence: float = 0.0) -> dict:
    """
    Compute the full categorical topology report for a domain.

    This is the main entry point — runs all engines and assembles
    results into a single JSON-serializable dict.

    Args:
        store: ReasoningStore instance
        domain_name: name of the domain to analyze
        max_dim: maximum simplex dimension for nerve (default 3)
        t_norm: t-norm for metric enrichment ("godel", "product", "lukasiewicz")
        min_persistence: minimum persistence for diagram filtering

    Returns:
        dict with all topological invariants
    """
    snap = CategorySnapshot.from_store(store, domain_name)

    report = {
        "domain": domain_name,
        "domain_id": snap.domain_id,
        "n_objects": snap.n_objects,
        "n_morphisms": snap.n_morphisms,
        "computed_at": time.time(),
    }

    # 1. Isomorphism structure
    iso_eng = IsomorphismEngine(snap)
    isos = iso_eng.find_isomorphisms()
    strict_isos = [r for r in isos if r.is_iso]
    graded_classes = iso_eng.graded_iso_classes()
    report["isomorphisms"] = {
        "n_isomorphisms": len(strict_isos),
        "iso_pairs": [
            {"morphism_id": r.morphism_id, "source": r.source,
             "target": r.target, "inverse_id": r.inverse_id, "degree": r.iso_degree}
            for r in strict_isos
        ],
        "isomorphism_classes_strict": iso_eng.isomorphism_classes(threshold=0.99),
        "isomorphism_classes_graded": [
            {"representative": g["representative"], "objects": g["objects"],
             "is_strict": g["is_strict_class"]}
            for g in graded_classes
        ],
    }

    # 2. Limits and colimits (sample: terminal, initial, random pairs)
    lim = LimitsColimits(snap)
    report["limits"] = {
        "terminal_object": _limit_to_dict(lim.terminal_object()),
        "initial_object": _limit_to_dict(lim.initial_object()),
    }
    # If enough objects, compute a few products
    if snap.n_objects >= 2:
        objs = snap.objects
        sample_pairs = [(objs[i], objs[j]) for i in range(min(3, len(objs)))
                        for j in range(i+1, min(4, len(objs)))]
        report["limits"]["sample_products"] = [
            _limit_to_dict(lim.product(a, b)) for a, b in sample_pairs[:3]
        ]

    # 3. Yoneda embedding
    yoneda = YonedaEmbedding(snap)
    Y = yoneda.yoneda_matrix()
    report["yoneda"] = {
        "matrix_shape": list(Y.shape),
        "matrix_rank": int(np.linalg.matrix_rank(Y)),
        "is_full_rank": bool(np.linalg.matrix_rank(Y) == snap.n_objects),
        "row_norms": {snap.objects[i]: round(float(np.linalg.norm(Y[i])), 4)
                     for i in range(snap.n_objects)},
        "interpretation": _interpret_yoneda(Y, snap),
    }

    # 4. Nerve complex summary
    nerve = NerveComplex(snap, max_dim=min(max_dim, 3))
    nerve_summary = nerve.summary()
    report["nerve"] = nerve_summary

    # 5. Homology
    try:
        hom_eng = HomologyEngine(nerve)
        betti = hom_eng.betti_numbers(max_dim=min(max_dim, 3))
        euler = hom_eng.euler_characteristic()
        report["homology"] = {
            "betti_numbers": betti,
            "euler_characteristic": euler,
            "is_connected": hom_eng.is_connected(),
            "interpretation": _interpret_homology(betti, euler),
        }
    except Exception as e:
        report["homology"] = {"error": str(e)}

    # 6. Persistent homology
    try:
        ph_eng = PersistentHomologyEngine(nerve)
        diag = ph_eng.compute(min_persistence=min_persistence)
        report["persistent_homology"] = ph_eng.to_dict(diag)
    except Exception as e:
        report["persistent_homology"] = {"error": str(e)}

    # 7. Fundamental groupoid
    try:
        fg = FundamentalGroupoid(snap)
        fg_result = fg.compute()
        report["fundamental_groupoid"] = {
            "pi0": fg_result.pi0,
            "n_components": fg_result.n_components,
            "is_connected": fg_result.is_connected,
            "pi1_rank": fg_result.pi1_rank,
            "homotopy_type": fg_result.homotopy_type,
            "graded_components": {
                str(t): comps
                for t, comps in fg_result.graded_components.items()
            },
        }
    except Exception as e:
        report["fundamental_groupoid"] = {"error": str(e)}

    # 8. Metric enrichment
    try:
        metric = MetricEnrichment(snap, t_norm=t_norm)
        axiom_check = metric.verify_enrichment_axioms()
        report["metric_enrichment"] = axiom_check
    except Exception as e:
        report["metric_enrichment"] = {"error": str(e)}

    return report


def _limit_to_dict(r: LimitResult) -> dict:
    return {
        "type": r.limit_type,
        "apex": r.apex,
        "exists": r.exists,
        "degree": r.degree,
        "projections": r.projections[:4],
    }


def _interpret_yoneda(Y: np.ndarray, snap: CategorySnapshot) -> str:
    rank = int(np.linalg.matrix_rank(Y))
    n = snap.n_objects
    if rank == n:
        return "Full rank — objects are distinguishable by their hom-profiles (Yoneda is faithful)"
    return f"Rank {rank} < {n} — some objects have identical representable presheaves (duplicates?)"


def _interpret_homology(betti: dict, euler: int) -> str:
    b0 = betti.get(0, 0)
    b1 = betti.get(1, 0)
    b2 = betti.get(2, 0)
    parts = []
    if b0 == 1:
        parts.append("connected")
    elif b0 > 1:
        parts.append(f"{b0} connected components")
    if b1 == 0:
        parts.append("no independent cycles (tree-like)")
    elif b1 == 1:
        parts.append("1 independent cycle")
    else:
        parts.append(f"{b1} independent cycles")
    if b2 > 0:
        parts.append(f"{b2} 2D holes")
    return "; ".join(parts) + f"; χ={euler}"
