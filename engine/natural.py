"""
MORPHOS Natural Transformations & Category Operations — Phase 2

Natural transformations are morphisms between functors. If F and G are
both functors C → D, a natural transformation η: F ⇒ G assigns to
each object A in C a morphism η_A: F(A) → G(A) in D, such that for
every morphism f: A → B in C, the "naturality square" commutes:

    F(A) --η_A--> G(A)
     |              |
    F(f)          G(f)
     |              |
     v              v
    F(B) --η_B--> G(B)

    G(f) ∘ η_A = η_B ∘ F(f)

Category operations:
- Product C × D: objects are pairs, morphisms are pairs
- Coproduct C + D: disjoint union of objects and morphisms
- Functor category [C, D]: objects are functors, morphisms are natural transformations
- Opposite category C^op: reverse all arrows
- Slice category C/X: objects over a fixed object X

Source: Mac Lane (Categories for the Working Mathematician),
        Awodey (Category Theory), Leinster (Basic Category Theory)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid

from .categories import Category, Morphism, create_category
from .functors import Functor, find_functors
from .epistemic import Definite, Probable, EpistemicStatus
from .topos import TruthValue, compose_truth, actual, probable


# ══════════════════════════════════════════════════════════════
# NATURAL TRANSFORMATION
# ══════════════════════════════════════════════════════════════

@dataclass
class NaturalTransformation:
    """
    A natural transformation η: F ⇒ G between functors F, G: C → D.

    Components: for each object A in C, a morphism η_A: F(A) → G(A) in D.
    Naturality: for each f: A → B in C, G(f) ∘ η_A = η_B ∘ F(f).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_functor_id: str = ""     # F
    target_functor_id: str = ""     # G
    components: dict[str, str] = field(default_factory=dict)
    # components maps: source_object_label → morphism_id in target category
    # η_A = components[A], which is a morphism F(A) → G(A) in D
    is_natural: bool = False
    naturality_score: float = 0.0   # fraction of squares that commute
    is_isomorphism: bool = False    # all components are isos

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_functor": self.source_functor_id,
            "target_functor": self.target_functor_id,
            "components": dict(self.components),
            "is_natural": self.is_natural,
            "naturality_score": round(self.naturality_score, 4),
            "is_isomorphism": self.is_isomorphism,
        }


def find_natural_transformation(
    F: Functor,
    G: Functor,
    source_cat: Category,
    target_cat: Category,
) -> Optional[NaturalTransformation]:
    """
    Attempt to construct a natural transformation η: F ⇒ G.

    For each object A in source_cat, we need a morphism η_A: F(A) → G(A)
    in target_cat. Then we verify the naturality condition.
    """
    components = {}
    component_morphisms = {}

    # For each object in the source category, find η_A: F(A) → G(A)
    for obj in source_cat.objects:
        fa = F.object_map.get(obj)
        ga = G.object_map.get(obj)
        if fa is None or ga is None:
            continue

        if fa == ga:
            # Identity component — F and G agree on this object
            id_morph = target_cat.identity_for(fa)
            if id_morph:
                components[obj] = id_morph.id
                component_morphisms[obj] = id_morph
            continue

        # Look for a morphism F(A) → G(A) in target_cat
        candidates = target_cat.hom(fa, ga)
        if not candidates:
            return None  # No component exists, no natural transformation

        # Use first available (could be improved with scoring)
        components[obj] = candidates[0].id
        component_morphisms[obj] = candidates[0]

    if not components:
        return None

    # Verify naturality: for each f: A → B in source_cat,
    # check G(f) ∘ η_A = η_B ∘ F(f)
    checks = 0
    commuting = 0

    for f in source_cat.user_morphisms():
        a = f.source
        b = f.target

        if a not in components or b not in components:
            continue

        eta_a = components[a]       # η_A: F(A) → G(A)
        eta_b = components[b]       # η_B: F(B) → G(B)
        f_f = F.morphism_map.get(f.id)   # F(f): F(A) → F(B)
        g_f = G.morphism_map.get(f.id)   # G(f): G(A) → G(B)

        if not (f_f and g_f):
            continue

        checks += 1

        # Check: G(f) ∘ η_A = η_B ∘ F(f)
        # Left side: compose η_A then G(f) → (η_A, g_f) in compositions
        left = target_cat.compositions.get((eta_a, g_f))
        # Right side: compose F(f) then η_B → (f_f, η_B) in compositions
        right = target_cat.compositions.get((f_f, eta_b))

        if left is not None and right is not None and left == right:
            commuting += 1

    naturality_score = commuting / checks if checks > 0 else 1.0

    # Check if all components are isomorphisms
    is_iso = True
    for obj, mid in components.items():
        m = component_morphisms.get(obj)
        if m and not m.is_identity:
            fa = F.object_map.get(obj)
            ga = G.object_map.get(obj)
            # Check if there's an inverse G(A) → F(A)
            inverse = target_cat.hom(ga, fa) if fa and ga else []
            if not inverse:
                is_iso = False
                break

    return NaturalTransformation(
        name=f"η: {F.name} ⇒ {G.name}",
        source_functor_id=F.id,
        target_functor_id=G.id,
        components=components,
        is_natural=naturality_score >= 0.99,
        naturality_score=naturality_score,
        is_isomorphism=is_iso,
    )


def find_all_natural_transformations(
    functors: list[Functor],
    source_cat: Category,
    target_cat: Category,
) -> list[NaturalTransformation]:
    """Find natural transformations between all pairs of functors."""
    results = []
    for i, F in enumerate(functors):
        for G in functors[i + 1:]:
            nt = find_natural_transformation(F, G, source_cat, target_cat)
            if nt:
                results.append(nt)
            # Also try G ⇒ F
            nt_rev = find_natural_transformation(G, F, source_cat, target_cat)
            if nt_rev:
                results.append(nt_rev)
    return results


# ══════════════════════════════════════════════════════════════
# CATEGORY OPERATIONS
# ══════════════════════════════════════════════════════════════

def product_category(C: Category, D: Category) -> Category:
    """
    Product category C × D.

    Objects: pairs (c, d) for c in C, d in D
    Morphisms: pairs (f, g) for f in C, g in D
               (f, g): (c₁, d₁) → (c₂, d₂) iff f: c₁→c₂ and g: d₁→d₂

    The product captures "simultaneous structure" — how two domains
    interact when both are active at the same time.
    """
    objects = []
    for c in C.objects:
        for d in D.objects:
            objects.append(f"{c}×{d}")

    morphisms = []
    c_morphs = C.user_morphisms()
    d_morphs = D.user_morphisms()

    for f in c_morphs:
        for g in d_morphs:
            src = f"{f.source}×{g.source}"
            tgt = f"{f.target}×{g.target}"
            label = f"{f.label}×{g.label}"
            morphisms.append((label, src, tgt, "product", None))

    # Also include "hold one component fixed" morphisms
    for f in c_morphs:
        for d in D.objects:
            src = f"{f.source}×{d}"
            tgt = f"{f.target}×{d}"
            label = f"{f.label}×id_{d}"
            morphisms.append((label, src, tgt, "product_left", None))

    for c in C.objects:
        for g in d_morphs:
            src = f"{c}×{g.source}"
            tgt = f"{c}×{g.target}"
            label = f"id_{c}×{g.label}"
            morphisms.append((label, src, tgt, "product_right", None))

    return create_category(
        f"{C.name}×{D.name}",
        objects,
        morphisms,
        auto_close=False,
    )


def coproduct_category(C: Category, D: Category) -> Category:
    """
    Coproduct (disjoint union) C + D.

    Objects: tagged union of objects from C and D
    Morphisms: morphisms from C stay in C, morphisms from D stay in D,
               no cross-domain morphisms (those come from functors)

    The coproduct captures "either-or" — choosing between two domains.
    """
    objects = []
    for c in C.objects:
        objects.append(f"L.{c}")  # Left injection
    for d in D.objects:
        objects.append(f"R.{d}")  # Right injection

    morphisms = []
    for m in C.user_morphisms():
        morphisms.append((
            f"L.{m.label}", f"L.{m.source}", f"L.{m.target}",
            m.rel_type, m.value,
        ))
    for m in D.user_morphisms():
        morphisms.append((
            f"R.{m.label}", f"R.{m.source}", f"R.{m.target}",
            m.rel_type, m.value,
        ))

    return create_category(
        f"{C.name}+{D.name}",
        objects,
        morphisms,
        auto_close=False,
    )


def opposite_category(C: Category) -> Category:
    """
    Opposite category C^op.

    Same objects as C, but all arrows reversed.
    f: A → B in C becomes f^op: B → A in C^op.

    The opposite captures "duality" — every theorem about C
    has a dual theorem about C^op with all arrows reversed.
    """
    morphisms = []
    for m in C.user_morphisms():
        morphisms.append((
            f"{m.label}_op", m.target, m.source,  # reversed!
            m.rel_type, m.value,
        ))

    return create_category(
        f"{C.name}_op",
        list(C.objects),
        morphisms,
        auto_close=False,
    )


def slice_category(C: Category, over: str) -> Category:
    """
    Slice category C/X (category of objects over X).

    Objects: morphisms f: A → X in C (for any A)
    Morphisms: commuting triangles — h: (f: A→X) → (g: B→X)
               is a morphism h: A → B in C such that g ∘ h = f.

    The slice captures "everything pointing at X" — useful for
    studying how different entities relate to a fixed reference.
    """
    if over not in C.objects:
        raise ValueError(f"Object '{over}' not in category '{C.name}'")

    # Objects = morphisms targeting 'over'
    arrows_to_x = [m for m in C.user_morphisms() if m.target == over]
    if not arrows_to_x:
        return create_category(f"{C.name}/{over}", [], [])

    objects = [f"{m.source}→{over}[{m.label}]" for m in arrows_to_x]

    # Morphisms = commuting triangles
    morphisms = []
    for i, f in enumerate(arrows_to_x):
        for j, g in enumerate(arrows_to_x):
            if i == j:
                continue
            # Look for h: f.source → g.source in C such that g ∘ h = f
            for h in C.user_morphisms():
                if h.source == f.source and h.target == g.source:
                    # Check commutativity: g ∘ h should equal f
                    gh_comp = C.compositions.get((h.id, g.id))
                    if gh_comp == f.id or g.source == f.source:
                        src_obj = f"{f.source}→{over}[{f.label}]"
                        tgt_obj = f"{g.source}→{over}[{g.label}]"
                        if src_obj in objects and tgt_obj in objects:
                            morphisms.append((
                                f"△{h.label}",
                                src_obj, tgt_obj,
                                "slice", None,
                            ))

    # Deduplicate
    seen = set()
    unique = []
    for m in morphisms:
        key = (m[0], m[1], m[2])
        if key not in seen:
            seen.add(key)
            unique.append(m)

    return create_category(
        f"{C.name}/{over}",
        objects,
        unique,
        auto_close=False,
    )


def functor_category_summary(
    functors: list[Functor],
    nat_transforms: list[NaturalTransformation],
    source_name: str,
    target_name: str,
) -> Category:
    """
    Build a representation of the functor category [C, D].

    Objects = functors C → D
    Morphisms = natural transformations between those functors

    This is the category that collects all structural analogies
    between two domains into a single structure, where the
    morphisms tell you how different analogies relate to each other.
    """
    objects = [f.id for f in functors]
    obj_labels = {f.id: f.name or f"F_{i}" for i, f in enumerate(functors)}

    morphisms = []
    for nt in nat_transforms:
        if nt.source_functor_id in obj_labels and nt.target_functor_id in obj_labels:
            morphisms.append((
                nt.name or f"η_{nt.id[:8]}",
                nt.source_functor_id,
                nt.target_functor_id,
                "natural_transformation",
                nt.naturality_score,
            ))

    return create_category(
        f"[{source_name},{target_name}]",
        objects,
        morphisms,
        auto_close=False,
    )


# ══════════════════════════════════════════════════════════════
# LIMITS AND COLIMITS (simplified)
# ══════════════════════════════════════════════════════════════

def pullback(
    C: Category,
    f_label: str,
    g_label: str,
) -> Optional[dict]:
    """
    Compute the pullback of morphisms f: A → C and g: B → C.

    The pullback is the universal object P with projections
    π₁: P → A and π₂: P → B such that f ∘ π₁ = g ∘ π₂.

    In MORPHOS, the pullback represents "the commonality between
    two things that map to the same target" — the shared structure.

    Returns dict with pullback info, or None if morphisms not found.
    """
    f = C.get_morphism_by_label(f_label)
    g = C.get_morphism_by_label(g_label)

    if not f or not g:
        return None
    if f.target != g.target:
        return None  # Not a cospan

    target_obj = f.target

    # Find all objects that have morphisms to both f.source and g.source
    # and where the compositions agree
    pullback_candidates = []
    for obj in C.objects:
        morphs_to_a = [m for m in C.user_morphisms()
                       if m.source == obj and m.target == f.source]
        morphs_to_b = [m for m in C.user_morphisms()
                       if m.source == obj and m.target == g.source]

        for pi1 in morphs_to_a:
            for pi2 in morphs_to_b:
                # Check f ∘ π₁ = g ∘ π₂
                f_pi1 = C.compositions.get((pi1.id, f.id))
                g_pi2 = C.compositions.get((pi2.id, g.id))
                if f_pi1 and g_pi2 and f_pi1 == g_pi2:
                    pullback_candidates.append({
                        "object": obj,
                        "projection_1": pi1.label,
                        "projection_2": pi2.label,
                    })

    return {
        "f": f_label,
        "g": g_label,
        "target": target_obj,
        "source_f": f.source,
        "source_g": g.source,
        "pullback_candidates": pullback_candidates,
    }


def pushout(
    C: Category,
    f_label: str,
    g_label: str,
) -> Optional[dict]:
    """
    Compute the pushout of morphisms f: A → B and g: A → C (same source).

    The pushout is the universal object Q with injections
    ι₁: B → Q and ι₂: C → Q such that ι₁ ∘ f = ι₂ ∘ g.

    Dual of pullback — represents "merging two things that share a source."
    """
    f = C.get_morphism_by_label(f_label)
    g = C.get_morphism_by_label(g_label)

    if not f or not g:
        return None
    if f.source != g.source:
        return None  # Not a span

    source_obj = f.source

    pushout_candidates = []
    for obj in C.objects:
        morphs_from_b = [m for m in C.user_morphisms()
                        if m.source == f.target and m.target == obj]
        morphs_from_c = [m for m in C.user_morphisms()
                        if m.source == g.target and m.target == obj]

        for i1 in morphs_from_b:
            for i2 in morphs_from_c:
                f_i1 = C.compositions.get((f.id, i1.id))
                g_i2 = C.compositions.get((g.id, i2.id))
                if f_i1 and g_i2 and f_i1 == g_i2:
                    pushout_candidates.append({
                        "object": obj,
                        "injection_1": i1.label,
                        "injection_2": i2.label,
                    })

    return {
        "f": f_label,
        "g": g_label,
        "source": source_obj,
        "target_f": f.target,
        "target_g": g.target,
        "pushout_candidates": pushout_candidates,
    }
