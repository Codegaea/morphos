"""
Functor Matcher — Analogy Discovery Engine

Searches for structure-preserving mappings (functors) between categories.

A functor F: C → D maps:
- Objects of C to objects of D
- Morphisms of C to morphisms of D

While preserving:
- Composition: F(g∘f) = F(g) ∘ F(f)
- Identity: F(id_A) = id_{F(A)}

Modes:
- exact:  perfect structure preservation
- partial: allows unmapped objects (substructure analogy)
- approximate: relaxed composition (returns confidence score)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import permutations, combinations
from typing import Optional
import uuid

from .categories import Category, Morphism
from .epistemic import Definite, Probable, EpistemicStatus


@dataclass
class Functor:
    """A functor between two MORPHOS categories."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_name: str = ""
    target_name: str = ""
    object_map: dict[str, str] = field(default_factory=dict)
    morphism_map: dict[str, str] = field(default_factory=dict)
    is_faithful: bool = False
    is_full: bool = False
    is_essentially_surjective: bool = False
    composition_score: float = 0.0
    coverage: float = 1.0  # fraction of source objects mapped (for partial)
    status: EpistemicStatus = field(default_factory=Definite)
    discovered_by: str = "system"

    def classification(self) -> str:
        labels = []
        injective_on_objects = len(set(self.object_map.values())) == len(self.object_map)
        if (
            self.is_faithful
            and self.is_full
            and injective_on_objects
            and self.is_essentially_surjective
        ):
            return "isomorphism"
        if self.is_faithful and self.is_full and self.is_essentially_surjective:
            return "equivalence"
        if self.is_faithful:
            labels.append("faithful")
        if self.is_full:
            labels.append("full")
        if self.is_essentially_surjective:
            labels.append("essentially surjective")
        return ", ".join(labels) if labels else "functor"

    def to_dict(self) -> dict:
        return {
            "functor_id": self.id,
            "name": self.name,
            "source_category": self.source_name,
            "target_category": self.target_name,
            "object_map": dict(self.object_map),
            "morphism_map": dict(self.morphism_map),
            "morphism_map_labels": {},  # filled by find_functors
            "is_faithful": self.is_faithful,
            "is_full": self.is_full,
            "is_essentially_surjective": self.is_essentially_surjective,
            "composition_score": self.composition_score,
            "coverage": self.coverage,
            "classification": self.classification(),
            "epistemic_status": self.status.label(),
            "discovered_by": self.discovered_by,
        }


def find_functors(
    source: Category,
    target: Category,
    mode: str = "exact",
    max_results: int = 10,
) -> list[Functor]:
    """
    Search for functors from source to target category.

    Args:
        source: source category
        target: target category
        mode: "exact", "partial", or "approximate"
        max_results: max number of results
    """
    if mode == "exact":
        results = _find_exact(source, target, max_results)
    elif mode == "partial":
        results = _find_partial(source, target, max_results)
    elif mode == "approximate":
        results = _find_approximate(source, target, max_results)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    results.sort(key=lambda f: (-f.composition_score, -f.coverage))
    return results[:max_results]


def _find_exact(source: Category, target: Category, max_results: int) -> list[Functor]:
    """Find exact functors via backtracking with degree-based pruning."""
    results: list[Functor] = []
    src_objs = source.objects
    tgt_objs = target.objects

    # Degree filter: for each source object, compute (out_degree, in_degree)
    # excluding identities
    def degrees(cat: Category, obj: str) -> tuple[int, int]:
        out_d = len([m for m in cat.non_identity_morphisms() if m.source == obj and not m.is_composition])
        in_d = len([m for m in cat.non_identity_morphisms() if m.target == obj and not m.is_composition])
        return (out_d, in_d)

    src_degrees = {obj: degrees(source, obj) for obj in src_objs}
    tgt_degrees = {obj: degrees(target, obj) for obj in tgt_objs}

    # Compatible targets for each source object
    compatible: dict[str, list[str]] = {}
    for s_obj in src_objs:
        s_out, s_in = src_degrees[s_obj]
        compatible[s_obj] = [
            t_obj
            for t_obj in tgt_objs
            if tgt_degrees[t_obj][0] >= s_out and tgt_degrees[t_obj][1] >= s_in
        ]

    _backtrack(results, source, target, compatible, src_objs, {}, 0, max_results)
    return results


def _backtrack(
    results: list[Functor],
    source: Category,
    target: Category,
    compatible: dict[str, list[str]],
    src_objs: list[str],
    current_map: dict[str, str],
    depth: int,
    max_results: int,
) -> None:
    """Recursive backtracking over object mappings."""
    if len(results) >= max_results:
        return

    if depth == len(src_objs):
        # Complete mapping — try to build morphism mapping
        functor = _try_build_functor(source, target, dict(current_map))
        if functor:
            results.append(functor)
        return

    s_obj = src_objs[depth]
    for t_obj in compatible[s_obj]:
        current_map[s_obj] = t_obj
        if _is_partial_consistent(source, target, current_map):
            _backtrack(
                results, source, target, compatible, src_objs, current_map, depth + 1, max_results
            )
        del current_map[s_obj]


def _is_partial_consistent(source: Category, target: Category, partial_map: dict[str, str]) -> bool:
    """Check if partial object mapping is consistent with morphism structure."""
    mapped = set(partial_map.keys())
    for m in source.user_morphisms():
        if m.source in mapped and m.target in mapped:
            img_src = partial_map[m.source]
            img_tgt = partial_map[m.target]
            if not any(
                tm.source == img_src and tm.target == img_tgt
                for tm in target.non_identity_morphisms()
            ):
                return False
    return True


def _try_build_functor(
    source: Category, target: Category, obj_map: dict[str, str]
) -> Optional[Functor]:
    """Given a complete object mapping, find morphism mapping and verify."""
    morph_map: dict[str, str] = {}

    for sm in source.morphisms:
        img_src = obj_map[sm.source]
        img_tgt = obj_map[sm.target]

        candidates = [
            tm for tm in target.morphisms if tm.source == img_src and tm.target == img_tgt
        ]
        if not candidates:
            return None

        # Prefer matching identity to identity, non-identity to non-identity
        if sm.is_identity:
            id_cands = [c for c in candidates if c.is_identity]
            morph_map[sm.id] = id_cands[0].id if id_cands else candidates[0].id
        else:
            non_id_cands = [c for c in candidates if not c.is_identity]
            if not non_id_cands:
                morph_map[sm.id] = candidates[0].id
            else:
                # Pure structural matching: pick first available (no label bias)
                morph_map[sm.id] = non_id_cands[0].id

    # Verify composition preservation
    violations = 0
    checks = 0
    for (f_id, g_id), comp_id in source.compositions.items():
        F_f = morph_map.get(f_id)
        F_g = morph_map.get(g_id)
        F_comp = morph_map.get(comp_id)
        if not (F_f and F_g and F_comp):
            continue
        checks += 1
        tgt_comp = target.compositions.get((F_f, F_g))
        if tgt_comp != F_comp:
            violations += 1

    score = 1.0 - (violations / checks) if checks > 0 else 1.0
    if score < 0.99:
        return None

    # Classify
    is_faithful = _check_faithful(source, morph_map)
    is_full = _check_full(source, target, obj_map, morph_map)
    is_ess_surj = len(set(obj_map.values())) == len(target.objects)

    return Functor(
        name=f"F: {source.name} → {target.name}",
        source_name=source.name,
        target_name=target.name,
        object_map=obj_map,
        morphism_map=morph_map,
        is_faithful=is_faithful,
        is_full=is_full,
        is_essentially_surjective=is_ess_surj,
        composition_score=score,
        status=Definite(),
        discovered_by="system",
    )


def _check_faithful(source: Category, morph_map: dict[str, str]) -> bool:
    """Injective on hom-sets?"""
    for a in source.objects:
        for b in source.objects:
            hom = source.hom(a, b)
            images = [morph_map[m.id] for m in hom if m.id in morph_map]
            if len(set(images)) < len(images):
                return False
    return True


def _check_full(
    source: Category,
    target: Category,
    obj_map: dict[str, str],
    morph_map: dict[str, str],
) -> bool:
    """Surjective on hom-sets between image objects?"""
    image_objs = set(obj_map.values())
    image_morphs = set(morph_map.values())
    for fa in image_objs:
        for fb in image_objs:
            for tm in target.hom(fa, fb):
                if tm.id not in image_morphs:
                    return False
    return True


def _find_partial(source: Category, target: Category, max_results: int) -> list[Functor]:
    """Find partial functors on subsets of source objects."""
    from .categories import create_category

    results: list[Functor] = []
    for k in range(len(source.objects), max(0, len(source.objects) - 3), -1):
        for subset in combinations(source.objects, k):
            subset_set = set(subset)
            subset_list = list(subset)
            sub_morphs = [
                (m.label, m.source, m.target)
                for m in source.user_morphisms()
                if m.source in subset_set and m.target in subset_set
            ]
            if not sub_morphs:
                continue

            sub_cat = create_category(f"{source.name}_sub", subset_list, sub_morphs)
            sub_results = _find_exact(sub_cat, target, max_results - len(results))
            coverage = len(subset_list) / len(source.objects)

            for f in sub_results:
                f.source_name = source.name
                f.coverage = coverage
                f.status = Probable(coverage)
                f.name = f"F: {source.name}[{','.join(subset_list)}] → {target.name}"
                results.append(f)

            if len(results) >= max_results:
                return results[:max_results]

    return results


def _find_approximate(source: Category, target: Category, max_results: int) -> list[Functor]:
    """Find approximate functors with relaxed composition preservation."""
    results: list[Functor] = []
    src_objs = source.objects
    tgt_objs = target.objects

    if len(src_objs) > len(tgt_objs):
        return results

    def degrees(cat, obj):
        out_d = len([m for m in cat.user_morphisms() if m.source == obj])
        in_d = len([m for m in cat.user_morphisms() if m.target == obj])
        return (out_d, in_d)

    src_degrees = {obj: degrees(source, obj) for obj in src_objs}
    tgt_degrees = {obj: degrees(target, obj) for obj in tgt_objs}

    for perm in permutations(tgt_objs, len(src_objs)):
        obj_map = dict(zip(src_objs, perm))
        morph_map: dict[str, str] = {}
        matched = 0
        total = 0

        for sm in source.morphisms:
            img_src = obj_map[sm.source]
            img_tgt = obj_map[sm.target]
            candidates = [
                tm for tm in target.morphisms
                if tm.source == img_src and tm.target == img_tgt
            ]
            total += 1
            if candidates:
                matched += 1
                if sm.is_identity:
                    id_c = [c for c in candidates if c.is_identity]
                    morph_map[sm.id] = id_c[0].id if id_c else candidates[0].id
                else:
                    non_id = [c for c in candidates if not c.is_identity]
                    morph_map[sm.id] = non_id[0].id if non_id else candidates[0].id

        score = matched / total if total > 0 else 0.0
        if score >= 0.5:
            results.append(
                Functor(
                    name=f"F~: {source.name} → {target.name}",
                    source_name=source.name,
                    target_name=target.name,
                    object_map=obj_map,
                    morphism_map=morph_map,
                    composition_score=score,
                    status=Probable(score),
                    discovered_by="system",
                )
            )
        if len(results) >= max_results:
            break

    return results[:max_results]
