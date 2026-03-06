"""
Scalable Functor Search

The brute-force backtracking search in functors.py is exact but exponential:
O(n^n) in the number of objects. It times out above ~10 objects.

This module provides polynomial-time approximate functor search using
graph signatures inspired by the Weisfeiler-Lehman graph isomorphism
heuristic. The idea:

1. Compute a structural "fingerprint" for each object based on its
   local neighborhood: what relationship types go in/out, how many
   of each, and recursively what its neighbors look like.

2. Match objects across categories by fingerprint compatibility.

3. Use the Hungarian algorithm (optimal assignment) to find the
   best overall object mapping that maximizes structural similarity.

4. Score the mapping by checking how well it preserves morphism
   structure and composition.

This runs in O(n^2 * m) time where n = objects and m = morphisms,
making it practical for categories with hundreds or thousands of nodes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional
import uuid

from .categories import Category, Morphism
from .epistemic import Definite, Probable


@dataclass
class SignatureMatch:
    """Result of a scalable functor search."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_name: str = ""
    target_name: str = ""
    object_map: dict[str, str] = field(default_factory=dict)
    morphism_map: dict[str, str] = field(default_factory=dict)
    structural_score: float = 0.0      # 0-1: how well objects match by signature
    morphism_score: float = 0.0        # 0-1: fraction of morphisms that map correctly
    composition_score: float = 0.0     # 0-1: fraction of compositions preserved
    overall_score: float = 0.0         # weighted combination
    coverage: float = 1.0
    unmapped_source: list[str] = field(default_factory=list)
    unmapped_target: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "match_id": self.id,
            "name": self.name,
            "source_category": self.source_name,
            "target_category": self.target_name,
            "object_map": dict(self.object_map),
            "structural_score": round(self.structural_score, 4),
            "morphism_score": round(self.morphism_score, 4),
            "composition_score": round(self.composition_score, 4),
            "overall_score": round(self.overall_score, 4),
            "coverage": round(self.coverage, 4),
            "unmapped_source": self.unmapped_source,
            "unmapped_target": self.unmapped_target,
        }


# ── Object Fingerprinting ────────────────────────────────────

def _compute_signatures(cat: Category, depth: int = 2) -> dict[str, tuple]:
    """
    Compute a structural signature for each object in a category.

    Uses relationship types (not just labels) for matching, quantitative
    values for weighting, and temporal order for sequence awareness.

    Level 0: (out_by_reltype, in_by_reltype, total_out, total_in, avg_value, has_temporal)
    Level k: recursive refinement using neighbor signatures
    """
    morphisms = cat.user_morphisms()

    # Level 0: degree profile by relationship type + quantitative features
    sigs: dict[str, tuple] = {}
    for obj in cat.objects:
        out_types = Counter()
        in_types = Counter()
        values_out: list[float] = []
        values_in: list[float] = []
        temporal_positions: list[int] = []

        for m in morphisms:
            rtype = m.rel_type or m.label
            if m.source == obj:
                out_types[rtype] += 1
                if m.value is not None:
                    values_out.append(m.value)
                if m.temporal_order is not None:
                    temporal_positions.append(m.temporal_order)
            if m.target == obj:
                in_types[rtype] += 1
                if m.value is not None:
                    values_in.append(m.value)

        avg_val_out = sum(values_out) / len(values_out) if values_out else 0.0
        avg_val_in = sum(values_in) / len(values_in) if values_in else 0.0
        has_temporal = 1 if temporal_positions else 0
        avg_temporal = sum(temporal_positions) / len(temporal_positions) if temporal_positions else 0

        sigs[obj] = (
            tuple(sorted(out_types.items())),
            tuple(sorted(in_types.items())),
            sum(out_types.values()),
            sum(in_types.values()),
            round(avg_val_out, 3),
            round(avg_val_in, 3),
            has_temporal,
            round(avg_temporal, 1),
        )

    # Refine signatures using neighbor signatures (WL-style)
    for _ in range(depth):
        new_sigs = {}
        for obj in cat.objects:
            out_neighbor_sigs = []
            in_neighbor_sigs = []
            for m in morphisms:
                rtype = m.rel_type or m.label
                val = m.value or 0.0
                if m.source == obj:
                    out_neighbor_sigs.append((rtype, round(val, 2), sigs.get(m.target, ())))
                if m.target == obj:
                    in_neighbor_sigs.append((rtype, round(val, 2), sigs.get(m.source, ())))
            new_sigs[obj] = (
                sigs[obj],
                tuple(sorted(out_neighbor_sigs)),
                tuple(sorted(in_neighbor_sigs)),
            )
        sigs = new_sigs

    return sigs


def _signature_distance(sig1: tuple, sig2: tuple) -> float:
    """
    Compute distance between two signatures.
    Returns 0.0 for identical signatures, higher for more different.
    Uses a simple structural comparison.
    """
    if sig1 == sig2:
        return 0.0

    # Compare the base components
    s1 = str(sig1)
    s2 = str(sig2)

    # Extract degree info from the base signature
    def extract_degrees(sig):
        """Pull out numeric degree information from nested signature."""
        nums = []
        if isinstance(sig, tuple):
            for item in sig:
                if isinstance(item, int):
                    nums.append(item)
                elif isinstance(item, tuple):
                    nums.extend(extract_degrees(item))
        return nums

    d1 = extract_degrees(sig1)
    d2 = extract_degrees(sig2)

    # Pad to same length
    max_len = max(len(d1), len(d2), 1)
    d1.extend([0] * (max_len - len(d1)))
    d2.extend([0] * (max_len - len(d2)))

    # Euclidean distance on degree vectors, normalized
    dist = sum((a - b) ** 2 for a, b in zip(d1, d2)) ** 0.5
    max_dist = sum(max(a, b) ** 2 for a, b in zip(d1, d2)) ** 0.5

    if max_dist == 0:
        # Fall back to string comparison
        common = sum(1 for a, b in zip(s1, s2) if a == b)
        return 1.0 - common / max(len(s1), len(s2), 1)

    return dist / max_dist


# ── Hungarian-style Optimal Assignment ────────────────────────

def _compute_cost_matrix(
    src_objs: list[str],
    tgt_objs: list[str],
    src_sigs: dict[str, tuple],
    tgt_sigs: dict[str, tuple],
) -> list[list[float]]:
    """
    Build a cost matrix where cost[i][j] = distance between
    signature of src_objs[i] and tgt_objs[j].
    """
    n = len(src_objs)
    m = len(tgt_objs)
    cost = [[0.0] * m for _ in range(n)]
    for i, s_obj in enumerate(src_objs):
        for j, t_obj in enumerate(tgt_objs):
            cost[i][j] = _signature_distance(
                src_sigs.get(s_obj, ()),
                tgt_sigs.get(t_obj, ()),
            )
    return cost


def _hungarian_minimize(cost: list[list[float]]) -> list[tuple[int, int]]:
    """
    Simple greedy assignment (not full Hungarian, but O(n^2) and
    good enough for our purposes). Assigns each source to its
    best available target.

    For exact optimal assignment on larger problems, replace with
    scipy.optimize.linear_sum_assignment.
    """
    n = len(cost)
    m = len(cost[0]) if cost else 0
    if n == 0 or m == 0:
        return []

    # Build preference lists
    assignments: list[tuple[int, int]] = []
    used_targets: set[int] = set()

    # Sort source objects by "pickiness" — those with few good options go first
    src_order = list(range(n))
    src_order.sort(key=lambda i: min(cost[i]) if cost[i] else float("inf"))

    for i in src_order:
        # Find best available target
        best_j = -1
        best_cost = float("inf")
        for j in range(m):
            if j not in used_targets and cost[i][j] < best_cost:
                best_cost = cost[i][j]
                best_j = j
        if best_j >= 0:
            assignments.append((i, best_j))
            used_targets.add(best_j)

    return assignments


# ── Morphism Mapping ──────────────────────────────────────────

def _build_morphism_map(
    source: Category,
    target: Category,
    obj_map: dict[str, str],
) -> tuple[dict[str, str], float, float]:
    """
    Given an object mapping, find the best morphism mapping.
    Returns (morphism_map, morphism_score, value_score).

    Prefers matching relationship types. Scores quantitative
    value similarity when both morphisms carry values.
    """
    morph_map: dict[str, str] = {}
    mapped = 0
    total = 0
    value_diffs: list[float] = []

    for sm in source.morphisms:
        if sm.is_identity:
            img_obj = obj_map.get(sm.source)
            if img_obj:
                tid = target.identity_for(img_obj)
                if tid:
                    morph_map[sm.id] = tid.id
            continue

        total += 1
        img_src = obj_map.get(sm.source)
        img_tgt = obj_map.get(sm.target)

        if not img_src or not img_tgt:
            continue

        candidates = [
            tm for tm in target.morphisms
            if tm.source == img_src and tm.target == img_tgt and not tm.is_identity
        ]

        if candidates:
            # Prefer matching relationship type
            src_rtype = sm.rel_type or sm.label
            type_match = [c for c in candidates if (c.rel_type or c.label) == src_rtype]
            chosen = type_match[0] if type_match else candidates[0]
            morph_map[sm.id] = chosen.id
            mapped += 1

            # Track value similarity
            if sm.value is not None and chosen.value is not None:
                max_val = max(abs(sm.value), abs(chosen.value), 1e-10)
                value_diffs.append(abs(sm.value - chosen.value) / max_val)

    morph_score = mapped / total if total > 0 else 0.0
    value_score = 1.0 - (sum(value_diffs) / len(value_diffs)) if value_diffs else 1.0
    return morph_map, morph_score, value_score


def _check_composition_preservation(
    source: Category,
    target: Category,
    morph_map: dict[str, str],
) -> float:
    """
    Check what fraction of source compositions are preserved
    by the morphism mapping.
    """
    checks = 0
    preserved = 0

    for (f_id, g_id), comp_id in source.compositions.items():
        F_f = morph_map.get(f_id)
        F_g = morph_map.get(g_id)
        F_comp = morph_map.get(comp_id)

        if not (F_f and F_g and F_comp):
            continue

        checks += 1
        tgt_comp = target.compositions.get((F_f, F_g))
        if tgt_comp == F_comp:
            preserved += 1

    return preserved / checks if checks > 0 else 1.0


# ── Main Interface ────────────────────────────────────────────

def find_functors_scalable(
    source: Category,
    target: Category,
    min_score: float = 0.3,
    signature_depth: int = 2,
) -> list[SignatureMatch]:
    """
    Scalable functor search using graph signatures.

    Runs in O(n^2 * m) time instead of O(n^n), making it practical
    for categories with hundreds of nodes.

    Args:
        source: source category
        target: target category
        min_score: minimum overall score to report (0-1)
        signature_depth: WL refinement depth (higher = more precise but slower)

    Returns:
        List of SignatureMatch objects, sorted by overall score.
    """
    # Compute signatures
    src_sigs = _compute_signatures(source, depth=signature_depth)
    tgt_sigs = _compute_signatures(target, depth=signature_depth)

    src_objs = source.objects
    tgt_objs = target.objects

    # Build cost matrix and find optimal assignment
    cost = _compute_cost_matrix(src_objs, tgt_objs, src_sigs, tgt_sigs)
    assignments = _hungarian_minimize(cost)

    if not assignments:
        return []

    # Build object map from assignments
    obj_map = {}
    total_sig_distance = 0.0
    for i, j in assignments:
        obj_map[src_objs[i]] = tgt_objs[j]
        total_sig_distance += cost[i][j]

    avg_distance = total_sig_distance / len(assignments) if assignments else 1.0
    structural_score = max(0.0, 1.0 - avg_distance)

    # Build morphism mapping
    morph_map, morph_score, value_score = _build_morphism_map(source, target, obj_map)

    # Check composition preservation
    comp_score = _check_composition_preservation(source, target, morph_map)

    # Overall score: weighted combination including value similarity
    overall = (
        0.30 * structural_score
        + 0.30 * morph_score
        + 0.20 * comp_score
        + 0.20 * value_score
    )

    unmapped_src = [o for o in src_objs if o not in obj_map]
    unmapped_tgt = [o for o in tgt_objs if o not in set(obj_map.values())]
    coverage = len(obj_map) / len(src_objs) if src_objs else 0.0

    match = SignatureMatch(
        name=f"F~: {source.name} → {target.name}",
        source_name=source.name,
        target_name=target.name,
        object_map=obj_map,
        morphism_map=morph_map,
        structural_score=structural_score,
        morphism_score=morph_score,
        composition_score=comp_score,
        overall_score=overall,
        coverage=coverage,
        unmapped_source=unmapped_src,
        unmapped_target=unmapped_tgt,
    )

    if overall >= min_score:
        return [match]
    return []


def find_best_analogy(
    source: Category,
    targets: list[Category],
    min_score: float = 0.3,
) -> list[tuple[str, SignatureMatch]]:
    """
    Search for the best structural analogy between a source category
    and multiple target categories. Returns ranked results.
    """
    results = []
    for target in targets:
        matches = find_functors_scalable(source, target, min_score=min_score)
        for m in matches:
            results.append((target.name, m))

    results.sort(key=lambda x: -x[1].overall_score)
    return results
