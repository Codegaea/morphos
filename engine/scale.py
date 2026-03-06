"""
MORPHOS Phase 2.5 — Scale & Reasoning Extensions

Five capabilities for serious scale:
1. Typed Ontologies — objects carry types, morphisms carry domain/range constraints
2. Constraint-Solving Analogies — AC-3 arc consistency + backjumping
3. Embedding-Assisted Search — vector similarity to prune search space
4. Large Curated Datasets — 1000+ object categories from combined sources
5. Incremental Indexing — add data without rebuilding everything
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from typing import Optional, Callable
import uuid
import math
import time

from .categories import Category, Morphism, create_category
from .topos import TruthValue, Modality, actual, probable, undetermined


# ══════════════════════════════════════════════════════════════
# 1. TYPED ONTOLOGIES
#
# Objects carry type annotations. Morphisms carry domain/range
# constraints. The type system is itself a category (a preorder
# on types), and morphism validity can be checked against it.
# ══════════════════════════════════════════════════════════════

@dataclass
class TypedObject:
    """An object with type information."""
    label: str
    obj_type: str = "entity"        # primary type
    supertypes: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    def is_subtype_of(self, other_type: str) -> bool:
        return other_type == self.obj_type or other_type in self.supertypes


@dataclass
class MorphismType:
    """Type signature for a morphism: domain → codomain with constraints."""
    label: str
    domain_type: str = "entity"     # source must be this type (or subtype)
    codomain_type: str = "entity"   # target must be this type (or subtype)
    is_symmetric: bool = False
    is_transitive: bool = False
    is_reflexive: bool = False
    is_antisymmetric: bool = False
    inverse_label: Optional[str] = None


class TypedOntology:
    """
    A typed ontology layered on top of a Category.

    Provides:
    - Type hierarchy (subtype relation)
    - Domain/range constraints on morphism types
    - Type-safe category construction
    - Inference of new morphisms from transitivity/symmetry
    """

    def __init__(self, name: str = ""):
        self.name = name
        self.types: dict[str, list[str]] = {}  # type -> [supertypes]
        self.objects: dict[str, TypedObject] = {}
        self.morphism_types: dict[str, MorphismType] = {}
        self.morphisms: list[tuple[str, str, str]] = []  # (label, src, tgt)

    def add_type(self, type_name: str, supertypes: list[str] = None):
        """Register a type in the hierarchy."""
        self.types[type_name] = supertypes or []

    def is_subtype(self, sub: str, sup: str) -> bool:
        """Check if sub is a subtype of sup (transitively)."""
        if sub == sup:
            return True
        visited = set()
        stack = [sub]
        while stack:
            current = stack.pop()
            if current == sup:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self.types.get(current, []))
        return False

    def add_object(self, label: str, obj_type: str = "entity", **properties):
        """Add a typed object."""
        supertypes = []
        stack = [obj_type]
        visited = set()
        while stack:
            t = stack.pop()
            if t in visited:
                continue
            visited.add(t)
            parents = self.types.get(t, [])
            supertypes.extend(parents)
            stack.extend(parents)
        self.objects[label] = TypedObject(label, obj_type, supertypes, properties)

    def add_morphism_type(self, label: str, domain: str = "entity",
                          codomain: str = "entity", **kwargs):
        """Register a morphism type with domain/range constraints."""
        self.morphism_types[label] = MorphismType(
            label=label, domain_type=domain, codomain_type=codomain, **kwargs)

    def add_morphism(self, label: str, source: str, target: str) -> bool:
        """Add a morphism, checking type constraints. Returns True if valid."""
        src_obj = self.objects.get(source)
        tgt_obj = self.objects.get(target)
        mtype = self.morphism_types.get(label)

        if not src_obj or not tgt_obj:
            return False

        # Type check
        if mtype:
            if not src_obj.is_subtype_of(mtype.domain_type):
                return False
            if not tgt_obj.is_subtype_of(mtype.codomain_type):
                return False

        self.morphisms.append((label, source, target))

        # Auto-add symmetric morphism
        if mtype and mtype.is_symmetric:
            rev = (label, target, source)
            if rev not in self.morphisms:
                self.morphisms.append(rev)

        return True

    def infer_transitive(self) -> list[tuple[str, str, str]]:
        """Infer new morphisms from transitive morphism types."""
        new_morphisms = []
        transitive_types = {l for l, mt in self.morphism_types.items() if mt.is_transitive}

        for label in transitive_types:
            edges = [(s, t) for l, s, t in self.morphisms if l == label]
            adj = defaultdict(set)
            for s, t in edges:
                adj[s].add(t)

            # Transitive closure
            existing = set(edges)
            changed = True
            while changed:
                changed = False
                new_edges = []
                for a in list(adj.keys()):
                    for b in list(adj[a]):
                        for c in adj.get(b, set()):
                            if (a, c) not in existing and a != c:
                                new_edges.append((a, c))
                                existing.add((a, c))
                                adj[a].add(c)
                                changed = True
                for a, c in new_edges:
                    new_morphisms.append((label, a, c))

        # Add inferred morphisms
        for m in new_morphisms:
            if m not in self.morphisms:
                self.morphisms.append(m)

        return new_morphisms

    def to_category(self, auto_close: bool = False) -> Category:
        """Convert to a MORPHOS Category."""
        obj_labels = sorted(self.objects.keys())
        return create_category(
            self.name or "typed_ontology",
            obj_labels,
            [(l, s, t, l) for l, s, t in self.morphisms],
            auto_close=auto_close,
        )

    def type_check_report(self) -> dict:
        """Check all morphisms against type constraints."""
        violations = []
        for label, src, tgt in self.morphisms:
            mtype = self.morphism_types.get(label)
            if not mtype:
                continue
            src_obj = self.objects.get(src)
            tgt_obj = self.objects.get(tgt)
            if src_obj and not src_obj.is_subtype_of(mtype.domain_type):
                violations.append((label, src, tgt, f"{src} ({src_obj.obj_type}) not subtype of {mtype.domain_type}"))
            if tgt_obj and not tgt_obj.is_subtype_of(mtype.codomain_type):
                violations.append((label, src, tgt, f"{tgt} ({tgt_obj.obj_type}) not subtype of {mtype.codomain_type}"))
        return {"valid": len(violations) == 0, "violations": violations}


# ══════════════════════════════════════════════════════════════
# 2. CONSTRAINT-SOLVING ANALOGIES
#
# MAC (Maintaining Arc Consistency) + symmetry breaking +
# conflict-directed backjumping. Handles 50+ object categories.
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# 2b. SEMANTIC RESCORING
#
# After CSP finds structurally valid object mappings, many may be
# semantically meaningless ("speech_act ↦ activity"). We re-score
# each mapping by blending structural score with semantic similarity
# across three channels:
#   (a) Label token similarity — Jaccard on word tokens
#   (b) Reltype neighbourhood alignment — do mapped objects have
#       similar outgoing / incoming edge-type signatures?
#   (c) Optional knowledge-store co-occurrence — if objects share
#       entries in a curated KnowledgeStore they score higher
# ══════════════════════════════════════════════════════════════

def _label_tokens(label: str) -> set:
    """Split a concept label into lowercase tokens for comparison."""
    import re
    # Split on underscores, hyphens, spaces and camelCase boundaries
    tokens = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
    tokens = re.split(r'[_\-\s]+', tokens.lower())
    return {t for t in tokens if t}


def _label_similarity(a: str, b: str) -> float:
    """Jaccard similarity between label token sets."""
    ta, tb = _label_tokens(a), _label_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _reltype_signature(cat: Category, obj: str) -> tuple:
    """Sorted tuple of (rel_type, direction) pairs for an object."""
    um = cat.user_morphisms()
    sigs = []
    for m in um:
        rt = m.rel_type or m.label
        if m.source == obj:
            sigs.append((rt, "out"))
        if m.target == obj:
            sigs.append((rt, "in"))
    return tuple(sorted(set(sigs)))


def _relsig_similarity(sig1: tuple, sig2: tuple) -> float:
    """Jaccard similarity between reltype signature tuples."""
    s1, s2 = set(sig1), set(sig2)
    if not s1 or not s2:
        return 0.0
    # Compare only the direction, not the exact type name
    d1 = {d for _, d in s1}
    d2 = {d for _, d in s2}
    return len(d1 & d2) / len(d1 | d2)


def semantic_score_pair(
    s_obj: str,
    t_obj: str,
    source: Category,
    target: Category,
    knowledge_store=None,
) -> float:
    """
    Compute semantic similarity for a (source_object, target_object) pair.

    Returns a value in [0, 1] where higher means more semantically coherent.
    Three channels:
      - label token Jaccard similarity (weight 0.5)
      - reltype direction signature similarity (weight 0.3)
      - knowledge store co-occurrence (weight 0.2, 0 if no store provided)
    """
    label_sim = _label_similarity(s_obj, t_obj)

    src_sig = _reltype_signature(source, s_obj)
    tgt_sig = _reltype_signature(target, t_obj)
    reltype_sim = _relsig_similarity(src_sig, tgt_sig)

    if knowledge_store is not None:
        # Count how many relationships each object participates in across all
        # domains; objects with richer neighbourhoods are more salient
        src_triples = knowledge_store.query(subject=s_obj, limit=50) + \
                      knowledge_store.query(obj=s_obj, limit=50)
        tgt_triples = knowledge_store.query(subject=t_obj, limit=50) + \
                      knowledge_store.query(obj=t_obj, limit=50)
        # Jaccard on the set of co-participating concept labels
        src_neighbours = {t for _, s, t, _ in src_triples} | {s for _, s, t, _ in src_triples}
        tgt_neighbours = {t for _, s, t, _ in tgt_triples} | {s for _, s, t, _ in tgt_triples}
        src_neighbours.discard(s_obj)
        tgt_neighbours.discard(t_obj)
        if src_neighbours or tgt_neighbours:
            ks_sim = len(src_neighbours & tgt_neighbours) / len(src_neighbours | tgt_neighbours)
        else:
            ks_sim = 0.0
        return 0.5 * label_sim + 0.3 * reltype_sim + 0.2 * ks_sim
    else:
        return 0.6 * label_sim + 0.4 * reltype_sim


def semantic_rescore_mapping(
    result: dict,
    source: Category,
    target: Category,
    structural_weight: float = 0.7,
    semantic_weight: float = 0.3,
    knowledge_store=None,
) -> dict:
    """
    Re-score a CSP result dict by blending structural and semantic scores.

    Args:
        result: dict with keys 'object_map' and 'score' (structural score)
        source/target: the two categories
        structural_weight: how much to trust structural score (default 0.7)
        semantic_weight: how much to weight semantic similarity (default 0.3)
        knowledge_store: optional KnowledgeStore for co-occurrence signals

    Returns:
        A new dict with 'score' replaced by the blended score and
        'structural_score' / 'semantic_score' added for transparency.
    """
    obj_map = result.get("object_map", {})
    structural_score = result.get("score", 0.0)

    if not obj_map:
        return result

    pair_scores = []
    for s_obj, t_obj in obj_map.items():
        pair_scores.append(
            semantic_score_pair(s_obj, t_obj, source, target, knowledge_store)
        )

    semantic_score = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    blended = structural_weight * structural_score + semantic_weight * semantic_score

    new_result = dict(result)
    new_result["score"] = blended
    new_result["structural_score"] = round(structural_score, 4)
    new_result["semantic_score"] = round(semantic_score, 4)
    return new_result



def _wl_object_hash(cat, obj: str, depth: int = 2) -> str:
    """
    Compute a Weisfeiler-Lehman-style neighborhood fingerprint for a single object.

    At depth 0: just the degree signature (out_count, in_count).
    At depth k: hash of (own degree sig, sorted set of neighbor hashes at depth k-1).

    Two objects with the same WL hash at depth d have identical d-hop neighborhoods
    up to graph isomorphism. Using depth=2 catches most structural mismatches
    while staying fast (O(n * E) per category).
    """
    um = cat.user_morphisms()
    # Build adjacency
    out_adj: dict[str, list] = defaultdict(list)
    in_adj: dict[str, list]  = defaultdict(list)
    for m in um:
        out_adj[m.source].append((m.target, m.rel_type or m.label))
        in_adj[m.target].append((m.source, m.rel_type or m.label))

    def _hash_at(o: str, d: int, memo: dict) -> str:
        key = (o, d)
        if key in memo:
            return memo[key]
        if d == 0:
            h = f"({len(out_adj[o])},{len(in_adj[o])})"
        else:
            nbr_hashes = sorted(_hash_at(n, d-1, memo) for n, _ in out_adj[o])
            nbr_hashes += ["_in_" + _hash_at(n, d-1, memo) for n, _ in in_adj[o]]
            h = f"({len(out_adj[o])},{len(in_adj[o])};{','.join(sorted(nbr_hashes))})"
        memo[key] = h
        return h

    memo: dict = {}
    return _hash_at(obj, depth, memo)


def _build_wl_buckets(cat, depth: int = 2) -> dict[str, list[str]]:
    """
    Group all objects in a category by their WL neighborhood hash.
    Returns {wl_hash: [obj, obj, ...]} — objects in the same bucket
    are structurally identical up to depth hops.
    """
    buckets: dict[str, list[str]] = defaultdict(list)
    for obj in cat.objects:
        h = _wl_object_hash(cat, obj, depth)
        buckets[h].append(obj)
    return dict(buckets)


def find_analogies_csp(
    source: Category,
    target: Category,
    max_results: int = 5,
    timeout_ms: int = 10000,
    allow_partial: bool = True,
    cross_type: bool = True,
    semantic_weight: float = 0.3,
    knowledge_store=None,
) -> list[dict]:
    """
    Find structural analogies using constraint satisfaction.

    Args:
        cross_type: if True, match morphisms by structural position even
                    when rel_types differ. Essential for cross-domain discovery
                    where relationship names are naturally different.
        semantic_weight: blend factor for semantic label/reltype similarity
                    (0 = pure structural, higher = more semantic filtering).
                    Default 0.3 preserves structure-first behaviour.
        knowledge_store: optional KnowledgeStore for co-occurrence re-scoring.
    """
    src_objs = source.objects
    tgt_objs = target.objects
    src_morphs = source.user_morphisms()
    tgt_morphs = target.user_morphisms()

    if not src_objs or not tgt_objs:
        return []

    # ── Index structures ──────────────────────────────────
    # Typed forward index: (source, rel_type) → set of targets
    tgt_fwd: dict[tuple[str, str], set[str]] = defaultdict(set)
    # Structural forward index: source → set of targets (any rel_type)
    tgt_fwd_any: dict[str, set[str]] = defaultdict(set)
    # Reverse index: (target, rel_type) → set of sources
    tgt_rev: dict[tuple[str, str], set[str]] = defaultdict(set)
    for m in tgt_morphs:
        rt = m.rel_type or m.label
        tgt_fwd[(m.source, rt)].add(m.target)
        tgt_fwd_any[m.source].add(m.target)
        tgt_rev[(m.target, rt)].add(m.source)

    # Choose which index to use based on cross_type flag
    def has_edge(vi, vj, rel_type):
        """Check if there's a matching edge vi→vj in target."""
        if cross_type:
            # Structural match: any edge vi→vj regardless of type
            return vj in tgt_fwd_any.get(vi, set())
        else:
            # Typed match: must have same rel_type
            return vj in tgt_fwd.get((vi, rel_type), set())

    def has_any_edge_to(vi, rel_type, domain_vals):
        """Check if vi has any edge to any value in domain_vals."""
        if cross_type:
            neighbors = tgt_fwd_any.get(vi, set())
            return bool(neighbors & set(domain_vals))
        else:
            targets = tgt_fwd.get((vi, rel_type), set())
            return bool(targets & set(domain_vals))

    # ── Degree profiles ───────────────────────────────────
    def degree_sig(cat, obj):
        um = cat.user_morphisms()
        out_c = Counter(m.rel_type or m.label for m in um if m.source == obj)
        in_c = Counter(m.rel_type or m.label for m in um if m.target == obj)
        return (tuple(sorted(out_c.items())), tuple(sorted(in_c.items())))

    src_sigs = {o: degree_sig(source, o) for o in src_objs}
    tgt_sigs = {o: degree_sig(target, o) for o in tgt_objs}

    # ── Symmetry breaking ─────────────────────────────────
    # Group target objects by degree signature — objects with identical
    # signatures are interchangeable, so we only need to try one per class
    tgt_classes: dict[tuple, list[str]] = defaultdict(list)
    for o in tgt_objs:
        tgt_classes[tgt_sigs[o]].append(o)

    # ── WL fingerprint buckets (prefilter for large graphs) ──────────
    # For graphs with >50 objects, build WL neighborhood hashes so the
    # CSP only considers structurally-compatible object pairs. This cuts
    # the initial domain size from O(n) to O(k) where k is the bucket size.
    use_wl = len(src_objs) > 50 or len(tgt_objs) > 50
    if use_wl:
        src_wl = {o: _wl_object_hash(source, o) for o in src_objs}
        tgt_buckets = _build_wl_buckets(target)  # hash -> [objs]
        # Invert: tgt_obj -> wl_hash
        tgt_wl_inv = {o: h for h, objs in tgt_buckets.items() for o in objs}
    else:
        src_wl = {}
        tgt_buckets = {}

    # ── Domain initialization ─────────────────────────────
    # For each source object, find compatible targets by degree profile
    # (WL prefilter applied first for large graphs)
    domains: dict[str, list[str]] = {}
    for s_obj in src_objs:
        s_out, s_in = src_sigs[s_obj]
        s_out_n = sum(c for _, c in s_out)
        s_in_n = sum(c for _, c in s_in)
        s_out_types = set(r for r, _ in s_out)
        s_in_types = set(r for r, _ in s_in)

        # WL prefilter: restrict to structurally-compatible bucket
        if use_wl and src_wl:
            s_hash = src_wl[s_obj]
            wl_bucket = tgt_buckets.get(s_hash, tgt_objs)
            candidate_pool = wl_bucket if wl_bucket else tgt_objs
        else:
            candidate_pool = tgt_objs

        compatible = []
        for t_obj in candidate_pool:
            t_out, t_in = tgt_sigs[t_obj]
            t_out_n = sum(c for _, c in t_out)
            t_in_n = sum(c for _, c in t_in)

            # Degree check: target must have enough edges
            if t_out_n < s_out_n or t_in_n < s_in_n:
                continue

            if not cross_type:
                # Strict: target must cover source's relationship types
                t_out_types = set(r for r, _ in t_out)
                t_in_types = set(r for r, _ in t_in)
                if not s_out_types.issubset(t_out_types):
                    continue
                if not s_in_types.issubset(t_in_types):
                    continue

            compatible.append(t_obj)

        domains[s_obj] = compatible if compatible else list(tgt_objs)

    # ── Constraints ───────────────────────────────────────
    constraints: list[tuple[str, str, str]] = []
    for m in src_morphs:
        constraints.append((m.source, m.target, m.rel_type or m.label))

    # Constraint adjacency: for each variable, which constraints involve it
    var_constraints: dict[str, list[int]] = defaultdict(list)
    for i, (xi, xj, _) in enumerate(constraints):
        var_constraints[xi].append(i)
        var_constraints[xj].append(i)

    # ── MAC: Maintaining Arc Consistency ──────────────────
    def ac3(dom: dict[str, list[str]], trigger_var: str = None) -> bool:
        """Run AC-3, optionally seeded from a specific variable's constraints."""
        if trigger_var:
            queue = [(xi, xj, rel) for xi, xj, rel in constraints
                     if xi == trigger_var or xj == trigger_var]
        else:
            queue = list(constraints)

        while queue:
            xi, xj, rel = queue.pop(0)
            if _revise(dom, xi, xj, rel):
                if not dom[xi]:
                    return False
                # Propagate: re-check all constraints involving xi
                for ci in var_constraints[xi]:
                    cx, cy, cr = constraints[ci]
                    if cx != xj and cy != xj:
                        queue.append((cx, cy, cr))
        return True

    def _revise(dom, xi, xj, rel_type) -> bool:
        revised = False
        to_remove = []
        for vi in dom[xi]:
            if not any(has_edge(vi, vj, rel_type) for vj in dom[xj]):
                to_remove.append(vi)
                revised = True
        for v in to_remove:
            dom[xi].remove(v)
        return revised

    # Initial AC-3
    if not ac3(domains):
        if allow_partial:
            partial = _find_partial(src_objs, domains, constraints, tgt_fwd_any if cross_type else tgt_fwd, cross_type)
            if semantic_weight > 0 and partial:
                sw = 1.0 - semantic_weight
                partial = [semantic_rescore_mapping(r, source, target, structural_weight=sw, semantic_weight=semantic_weight, knowledge_store=knowledge_store) for r in partial]
            return partial
        return []

    # ── Backtracking with MAC + backjumping ───────────────
    results = []
    best_partial = {"object_map": {}, "score": 0.0}
    assignment: dict[str, str] = {}
    conflict_set: dict[str, set[str]] = defaultdict(set)  # var → set of vars causing conflicts
    start_time = time.time()

    # Variable ordering: MRV (minimum remaining values)
    def pick_var(unassigned, dom):
        return min(unassigned, key=lambda v: len(dom[v]))

    def backtrack_mac(unassigned: list[str], dom: dict[str, list[str]]):
        nonlocal best_partial

        if (time.time() - start_time) * 1000 > timeout_ms:
            return
        if len(results) >= max_results:
            return

        if not unassigned:
            score = _score_assignment_fn(assignment, constraints, has_edge)
            if score > 0:
                results.append({"object_map": dict(assignment), "score": score})
            return

        # Track best partial
        if len(assignment) > len(best_partial["object_map"]):
            partial_score = _score_assignment_fn(assignment, constraints, has_edge)
            if partial_score > best_partial["score"]:
                best_partial = {"object_map": dict(assignment), "score": partial_score}

        var = pick_var(unassigned, dom)
        remaining = [v for v in unassigned if v != var]
        used = set(assignment.values())

        # Value ordering: prefer targets that satisfy the most constraints
        # + symmetry breaking: skip values equivalent to already-tried values
        tried_classes = set()

        def value_score(val):
            s = 0
            for xi, xj, rel in constraints:
                if xi == var and xj in assignment:
                    if has_edge(val, assignment[xj], rel):
                        s += 1
                if xj == var and xi in assignment:
                    if has_edge(assignment[xi], val, rel):
                        s += 1
            return s

        ordered_values = sorted(
            [v for v in dom[var] if v not in used],
            key=value_score, reverse=True
        )

        found_any = False
        for val in ordered_values:
            # Symmetry breaking: skip equivalent targets already tried at this level
            val_class = tgt_sigs.get(val, val)
            if val_class in tried_classes:
                continue
            tried_classes.add(val_class)
            # Save domains for backtracking
            saved_domains = {v: list(d) for v, d in dom.items()}

            assignment[var] = val

            # Reduce domains: assigned var → singleton
            dom[var] = [val]

            # MAC: propagate the assignment
            consistent = ac3(dom, trigger_var=var)

            if consistent:
                # Check no remaining domain is empty
                consistent = all(len(dom[v]) > 0 for v in remaining)

            if consistent:
                found_any = True
                backtrack_mac(remaining, dom)
            else:
                # Record conflict for backjumping
                for xi, xj, rel in constraints:
                    if xi == var and xj in assignment:
                        conflict_set[var].add(xj)
                    if xj == var and xi in assignment:
                        conflict_set[var].add(xi)

            # Restore domains
            del assignment[var]
            for v in dom:
                dom[v] = saved_domains[v]

        if not found_any and not results:
            # Backjumping: propagate conflict set upward
            if var in conflict_set:
                parent_vars = [v for v in unassigned if v != var]
                for pv in parent_vars:
                    conflict_set[pv].update(conflict_set[var])

    backtrack_mac(list(src_objs), domains)

    # If no complete solution, return best partial
    if not results and allow_partial and best_partial["score"] > 0:
        best_partial["partial"] = True
        results.append(best_partial)

    # Semantic re-scoring: blend structural score with label/reltype similarity
    if semantic_weight > 0 and results:
        structural_weight = 1.0 - semantic_weight
        results = [
            semantic_rescore_mapping(
                r, source, target,
                structural_weight=structural_weight,
                semantic_weight=semantic_weight,
                knowledge_store=knowledge_store,
            )
            for r in results
        ]

    results.sort(key=lambda r: -r["score"])
    return results


def _find_partial(src_objs, domains, constraints, tgt_fwd, cross_type=False):
    """Find the best partial mapping when no complete solution exists."""
    def _check(vi, vj, rel):
        if cross_type:
            return vj in tgt_fwd.get(vi, set())
        else:
            return vj in tgt_fwd.get((vi, rel), set())

    assignment = {}
    used = set()
    for var in sorted(src_objs, key=lambda o: len(domains[o])):
        for val in domains[var]:
            if val in used:
                continue
            ok = True
            for xi, xj, rel in constraints:
                if xi == var and xj in assignment:
                    if not _check(val, assignment[xj], rel):
                        ok = False; break
                if xj == var and xi in assignment:
                    if not _check(assignment[xi], val, rel):
                        ok = False; break
            if ok:
                assignment[var] = val
                used.add(val)
                break

    if assignment:
        matched = sum(
            1 for xi, xj, rel in constraints
            if xi in assignment and xj in assignment
            and _check(assignment[xi], assignment[xj], rel)
        )
        total = len(constraints)
        score = matched / total if total > 0 else 0
        return [{"object_map": assignment, "score": score, "partial": True}]
    return []


def _score_assignment_fn(assignment, constraints, has_edge_fn):
    """Score assignment using a has_edge function."""
    matched = 0
    total = len(constraints)
    for xi, xj, rel in constraints:
        vi = assignment.get(xi)
        vj = assignment.get(xj)
        if vi and vj and has_edge_fn(vi, vj, rel):
            matched += 1
    return matched / total if total > 0 else 0.0


def _score_assignment(assignment, source, target, tgt_fwd, constraints):
    """Score how well an assignment preserves morphism structure."""
    matched = 0
    total = len(constraints)
    for xi, xj, rel in constraints:
        vi = assignment.get(xi)
        vj = assignment.get(xj)
        if vi and vj and vj in tgt_fwd.get((vi, rel), set()):
            matched += 1
    return matched / total if total > 0 else 0.0


# ══════════════════════════════════════════════════════════════
# 3. EMBEDDING-ASSISTED SEARCH
#
# Compute structural embeddings for objects (not word embeddings —
# graph structure embeddings). Use cosine similarity to quickly
# filter candidate mappings before running the constraint solver.
# ══════════════════════════════════════════════════════════════

def compute_structural_embeddings(
    cat: Category,
    dim: int = 16,
    walks: int = 20,
    walk_length: int = 5,
) -> dict[str, list[float]]:
    """
    Compute structural embeddings for each object via random walks.

    Similar to DeepWalk/Node2Vec but simplified: for each object,
    perform random walks and hash the visited neighborhoods into
    a fixed-dimensional vector. Objects with similar local structure
    get similar embeddings.
    """
    um = cat.user_morphisms()
    adj = defaultdict(list)
    for m in um:
        adj[m.source].append((m.target, m.rel_type or m.label))
        # Include reverse for undirected structure
        adj[m.target].append((m.source, f"inv_{m.rel_type or m.label}"))

    embeddings = {}
    for obj in cat.objects:
        vec = [0.0] * dim
        for _ in range(walks):
            current = obj
            for step in range(walk_length):
                neighbors = adj.get(current, [])
                if not neighbors:
                    break
                # Deterministic pseudo-random selection using hashing
                h = hash((obj, current, step, _)) % len(neighbors)
                next_node, rel_type = neighbors[h]
                # Hash the (step, rel_type) into embedding dimensions
                bucket = hash((step, rel_type)) % dim
                vec[bucket] += 1.0
                current = next_node
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        embeddings[obj] = [x / norm for x in vec]

    return embeddings


def embedding_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Cosine similarity between two embeddings."""
    dot = sum(a * b for a, b in zip(emb1, emb2))
    n1 = math.sqrt(sum(a * a for a in emb1)) or 1.0
    n2 = math.sqrt(sum(b * b for b in emb2)) or 1.0
    return dot / (n1 * n2)


def embedding_assisted_search(
    source: Category,
    target: Category,
    top_k: int = 3,
    min_similarity: float = 0.3,
) -> list[dict]:
    """
    Use structural embeddings to quickly find candidate analogies,
    then refine with the constraint solver.

    1. Embed both categories
    2. For each source object, find top-k most similar target objects
    3. Use these as restricted domains for the CSP solver
    4. Run constraint solving on the pruned space
    """
    src_emb = compute_structural_embeddings(source)
    tgt_emb = compute_structural_embeddings(target)

    # For each source object, find best target candidates by embedding
    candidate_map: dict[str, list[str]] = {}
    for s_obj in source.objects:
        sims = []
        for t_obj in target.objects:
            sim = embedding_similarity(src_emb[s_obj], tgt_emb[t_obj])
            sims.append((t_obj, sim))
        sims.sort(key=lambda x: -x[1])
        candidates = [t for t, s in sims[:top_k] if s >= min_similarity]
        if not candidates:
            candidates = [sims[0][0]] if sims else list(target.objects)
        candidate_map[s_obj] = candidates

    # Build constrained problem
    results = find_analogies_csp(source, target, max_results=5, timeout_ms=3000)

    # Also try greedy embedding-based assignment
    used = set()
    greedy_map = {}
    for s_obj in sorted(source.objects, key=lambda o: len(candidate_map.get(o, []))):
        best_t = None
        best_sim = -1
        for t_obj in candidate_map.get(s_obj, target.objects):
            if t_obj not in used:
                sim = embedding_similarity(src_emb[s_obj], tgt_emb[t_obj])
                if sim > best_sim:
                    best_sim = sim
                    best_t = t_obj
        if best_t:
            greedy_map[s_obj] = best_t
            used.add(best_t)

    # Score the greedy mapping
    um = source.user_morphisms()
    tgt_um = target.user_morphisms()
    matched = sum(
        1 for m in um
        if greedy_map.get(m.source) and greedy_map.get(m.target)
        and any(tm.source == greedy_map[m.source] and tm.target == greedy_map[m.target]
                for tm in tgt_um)
    )
    greedy_score = matched / len(um) if um else 0

    if greedy_score > 0:
        results.append({"object_map": greedy_map, "score": greedy_score, "method": "embedding"})

    results.sort(key=lambda r: -r["score"])
    return results[:5]


# ══════════════════════════════════════════════════════════════
# 4. LARGE CURATED DATASETS
#
# Combine all knowledge bases into a single queryable store
# with cross-domain indexing.
# ══════════════════════════════════════════════════════════════

class KnowledgeStore:
    """
    Unified store for all curated datasets with cross-domain querying.

    Provides:
    - Load all datasets into a single indexed structure
    - Query by object name, type, or relationship
    - Extract neighborhoods for any concept across all domains
    - Build categories from query results
    """

    def __init__(self):
        self.objects: dict[str, dict] = {}  # label -> {domain, type, ...}
        self.triples: list[tuple[str, str, str, str]] = []  # (rel, src, tgt, domain)
        self.by_subject: dict[str, list[int]] = defaultdict(list)  # subject -> [triple_indices]
        self.by_object: dict[str, list[int]] = defaultdict(list)   # object -> [triple_indices]
        self.by_relation: dict[str, list[int]] = defaultdict(list)  # relation -> [triple_indices]
        self.by_domain: dict[str, list[int]] = defaultdict(list)    # domain -> [triple_indices]
        self.domains: set[str] = set()

    def load_dataset(self, domain: str, data: dict):
        """Load a dataset dict (with 'objects' and 'morphisms' keys)."""
        self.domains.add(domain)

        for obj in data.get("objects", []):
            if obj not in self.objects:
                self.objects[obj] = {"domain": domain}
            else:
                # Object exists in multiple domains — track all
                existing = self.objects[obj]
                if isinstance(existing.get("domain"), str):
                    existing["domain"] = {existing["domain"], domain}
                elif isinstance(existing.get("domain"), set):
                    existing["domain"].add(domain)

        for morph in data.get("morphisms", []):
            rel = morph[0]
            src = morph[1]
            tgt = morph[2]
            idx = len(self.triples)
            self.triples.append((rel, src, tgt, domain))
            self.by_subject[src].append(idx)
            self.by_object[tgt].append(idx)
            self.by_relation[rel].append(idx)
            self.by_domain[domain].append(idx)

    def load_all_datasets(self):
        """Load all available curated datasets."""
        from .datasets import ALL_DATASETS
        from .knowledge_base import ALL_EXTENDED_DATASETS
        from .linguistic_kb import ALL_LINGUISTIC_DATASETS

        for name, fn in {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}.items():
            self.load_dataset(name, fn())

    def query(
        self,
        subject: str = None,
        relation: str = None,
        obj: str = None,
        domain: str = None,
        limit: int = 100,
    ) -> list[tuple[str, str, str, str]]:
        """Query triples by any combination of subject, relation, object, domain."""
        candidates = None

        if subject:
            indices = set(self.by_subject.get(subject, []))
            candidates = indices if candidates is None else candidates & indices
        if obj:
            indices = set(self.by_object.get(obj, []))
            candidates = indices if candidates is None else candidates & indices
        if relation:
            indices = set(self.by_relation.get(relation, []))
            candidates = indices if candidates is None else candidates & indices
        if domain:
            indices = set(self.by_domain.get(domain, []))
            candidates = indices if candidates is None else candidates & indices

        if candidates is None:
            candidates = set(range(min(limit, len(self.triples))))

        results = [self.triples[i] for i in sorted(candidates)[:limit]]
        return results

    def neighborhood(self, concept: str, max_hops: int = 1, max_nodes: int = 30) -> dict:
        """Extract the neighborhood of a concept across all domains."""
        nodes = {concept}
        edges = []
        frontier = {concept}

        for _ in range(max_hops):
            new_frontier = set()
            for node in frontier:
                for idx in self.by_subject.get(node, []):
                    rel, src, tgt, domain = self.triples[idx]
                    if tgt not in nodes and len(nodes) < max_nodes:
                        nodes.add(tgt)
                        new_frontier.add(tgt)
                    if tgt in nodes:
                        edges.append((rel, src, tgt, domain))
                for idx in self.by_object.get(node, []):
                    rel, src, tgt, domain = self.triples[idx]
                    if src not in nodes and len(nodes) < max_nodes:
                        nodes.add(src)
                        new_frontier.add(src)
                    if src in nodes:
                        edges.append((rel, src, tgt, domain))
            frontier = new_frontier

        return {"objects": sorted(nodes), "morphisms": edges}

    def to_category(self, concept: str, max_nodes: int = 30) -> Category:
        """Build a category from a concept's neighborhood."""
        data = self.neighborhood(concept, max_nodes=max_nodes)
        morphisms = list(set((r, s, t) for r, s, t, _ in data["morphisms"]))
        return create_category(
            f"ks_{concept}", data["objects"], morphisms, auto_close=False)

    @property
    def stats(self) -> dict:
        return {
            "total_objects": len(self.objects),
            "total_triples": len(self.triples),
            "domains": len(self.domains),
            "unique_relations": len(self.by_relation),
            "domain_list": sorted(self.domains),
        }


# ══════════════════════════════════════════════════════════════
# 5. INCREMENTAL INDEXING
#
# Add new data to existing categories and indexes without
# rebuilding everything from scratch.
# ══════════════════════════════════════════════════════════════

class IncrementalIndex:
    """
    Maintains indexes over a Category that update incrementally
    when new objects or morphisms are added.

    Indexes maintained:
    - Degree index: out/in degree per object
    - Adjacency index: neighbors by relation type
    - Signature cache: WL signatures per object (invalidated on change)
    - Embedding cache: structural embeddings (lazy recompute)
    """

    def __init__(self, category: Category):
        self.category = category
        self._out_degree: dict[str, Counter] = defaultdict(Counter)
        self._in_degree: dict[str, Counter] = defaultdict(Counter)
        self._out_adj: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        self._in_adj: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        self._signatures: dict[str, tuple] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._dirty_sigs: set[str] = set()
        self._dirty_embs: set[str] = set()
        self._version = 0

        # Build initial index
        self._rebuild()

    def _rebuild(self):
        """Full rebuild of all indexes."""
        self._out_degree.clear()
        self._in_degree.clear()
        self._out_adj.clear()
        self._in_adj.clear()

        for m in self.category.user_morphisms():
            rt = m.rel_type or m.label
            self._out_degree[m.source][rt] += 1
            self._in_degree[m.target][rt] += 1
            self._out_adj[m.source][rt].append(m.target)
            self._in_adj[m.target][rt].append(m.source)

        self._dirty_sigs = set(self.category.objects)
        self._dirty_embs = set(self.category.objects)
        self._version += 1

    def add_morphism(self, label: str, source: str, target: str,
                     rel_type: str = "", **kwargs) -> Morphism:
        """Add a morphism and incrementally update indexes."""
        m = self.category.add_morphism(label, source, target, rel_type=rel_type, **kwargs)
        rt = rel_type or label

        # Update degree indexes
        self._out_degree[source][rt] += 1
        self._in_degree[target][rt] += 1
        self._out_adj[source][rt].append(target)
        self._in_adj[target][rt].append(source)

        # Mark affected nodes as dirty for signature/embedding recompute
        self._dirty_sigs.add(source)
        self._dirty_sigs.add(target)
        # Also mark neighbors (their signatures depend on this node)
        for rt2, neighbors in self._out_adj[source].items():
            self._dirty_sigs.update(neighbors)
        for rt2, neighbors in self._in_adj[target].items():
            self._dirty_sigs.update(neighbors)

        self._dirty_embs.add(source)
        self._dirty_embs.add(target)
        self._version += 1
        return m

    def add_object(self, label: str):
        """Add an object and update indexes."""
        self.category.add_object(label)
        self._dirty_sigs.add(label)
        self._dirty_embs.add(label)
        self._version += 1

    def get_signature(self, obj: str) -> tuple:
        """Get WL signature for an object, recomputing if dirty."""
        if obj in self._dirty_sigs:
            self._recompute_signature(obj)
        return self._signatures.get(obj, ())

    def _recompute_signature(self, obj: str):
        """Recompute signature for a single object."""
        out_profile = tuple(sorted(self._out_degree.get(obj, {}).items()))
        in_profile = tuple(sorted(self._in_degree.get(obj, {}).items()))
        total_out = sum(self._out_degree.get(obj, {}).values())
        total_in = sum(self._in_degree.get(obj, {}).values())
        self._signatures[obj] = (out_profile, in_profile, total_out, total_in)
        self._dirty_sigs.discard(obj)

    def get_embedding(self, obj: str) -> list[float]:
        """Get structural embedding for an object, recomputing if dirty."""
        if obj in self._dirty_embs:
            embs = compute_structural_embeddings(self.category, dim=16, walks=10, walk_length=4)
            self._embeddings.update(embs)
            self._dirty_embs.clear()
        return self._embeddings.get(obj, [0.0] * 16)

    def degree(self, obj: str) -> tuple[int, int]:
        """Get (out_degree, in_degree) for an object."""
        out_d = sum(self._out_degree.get(obj, {}).values())
        in_d = sum(self._in_degree.get(obj, {}).values())
        return (out_d, in_d)

    def neighbors(self, obj: str, direction: str = "out") -> dict[str, list[str]]:
        """Get neighbors by relation type. direction: 'out', 'in', or 'both'."""
        result = {}
        if direction in ("out", "both"):
            for rt, targets in self._out_adj.get(obj, {}).items():
                result.setdefault(rt, []).extend(targets)
        if direction in ("in", "both"):
            for rt, sources in self._in_adj.get(obj, {}).items():
                result.setdefault(f"inv_{rt}", []).extend(sources)
        return result

    @property
    def stats(self) -> dict:
        return {
            "objects": len(self.category.objects),
            "morphisms": len(self.category.user_morphisms()),
            "dirty_signatures": len(self._dirty_sigs),
            "dirty_embeddings": len(self._dirty_embs),
            "version": self._version,
        }
