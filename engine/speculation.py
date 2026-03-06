"""
Speculation Engine

Analyzes a category for structural "holes" — places where a morphism
would complete a pattern — and generates candidates tagged as Speculative.

Strategies:
1. Composition closure: missing composites for composable pairs
2. Symmetry: missing inverses
3. Diagram completion: missing sides of potential commutative diagrams
"""
from __future__ import annotations
import uuid
from .categories import Category, Morphism
from .epistemic import Speculative, compose_epistemic


def speculate_morphisms(cat: Category) -> list[dict]:
    """
    Analyze the category and return a list of speculative morphism candidates.
    Each candidate is a dict with label, source, target, type, and rationale.
    """
    candidates: list[dict] = []
    seen: set[tuple[str, str, str]] = set()  # (type, source, target)

    for c in _speculate_compositions(cat):
        key = (c["speculation_type"], c["source"], c["target"])
        if key not in seen:
            seen.add(key)
            candidates.append(c)

    for c in _speculate_symmetries(cat):
        key = (c["speculation_type"], c["source"], c["target"])
        if key not in seen:
            seen.add(key)
            candidates.append(c)

    for c in _speculate_diagram_completion(cat):
        key = (c["speculation_type"], c["source"], c["target"])
        if key not in seen:
            seen.add(key)
            candidates.append(c)

    return candidates


def _speculate_compositions(cat: Category) -> list[dict]:
    """Suggest morphisms that would close composition gaps."""
    candidates: list[dict] = []
    user_m = cat.user_morphisms()

    for f in user_m:
        for g in user_m:
            if f.target != g.source:
                continue
            if f.source == g.target:
                continue  # would be endo

            exists = any(
                m.source == f.source and m.target == g.target for m in cat.morphisms
            )
            if not exists:
                comp_status = compose_epistemic(f.status, g.status)
                candidates.append(
                    {
                        "id": str(uuid.uuid4()),
                        "label": f"{g.label}∘{f.label}?",
                        "source": f.source,
                        "target": g.target,
                        "epistemic_status": "speculative",
                        "speculation_type": "composition_closure",
                        "rationale": (
                            f"Composing {f.label}: {f.source}→{f.target} "
                            f"with {g.label}: {g.source}→{g.target} "
                            f"would yield a morphism {f.source}→{g.target}. "
                            f"Implied status: {comp_status.label()}"
                        ),
                    }
                )
    return candidates


def _speculate_symmetries(cat: Category) -> list[dict]:
    """Suggest inverse morphisms where none exist."""
    candidates: list[dict] = []
    user_m = cat.user_morphisms()

    for f in user_m:
        reverse_exists = any(
            m.source == f.target and m.target == f.source for m in user_m
        )
        if not reverse_exists:
            candidates.append(
                {
                    "id": str(uuid.uuid4()),
                    "label": f"{f.label}⁻¹?",
                    "source": f.target,
                    "target": f.source,
                    "epistemic_status": "speculative",
                    "speculation_type": "symmetry_inverse",
                    "rationale": f"Inverse of {f.label}: {f.source}→{f.target}",
                }
            )
    return candidates


def _speculate_diagram_completion(cat: Category) -> list[dict]:
    """Suggest morphisms that would complete commutative diagrams."""
    candidates: list[dict] = []
    user_m = cat.user_morphisms()

    for a in cat.objects:
        outgoing = [m for m in user_m if m.source == a]
        for i, f in enumerate(outgoing):
            for g in outgoing[i + 1 :]:
                b, c = f.target, g.target
                if b == c:
                    continue
                bc_exists = any(m.source == b and m.target == c for m in user_m)
                cb_exists = any(m.source == c and m.target == b for m in user_m)
                if not bc_exists:
                    candidates.append(
                        {
                            "id": str(uuid.uuid4()),
                            "label": f"{b}→{c}?",
                            "source": b,
                            "target": c,
                            "epistemic_status": "speculative",
                            "speculation_type": "diagram_completion",
                            "rationale": (
                                f"Would complete diagram: {a} →[{f.label}] {b}, "
                                f"{a} →[{g.label}] {c}, missing {b} → {c}"
                            ),
                        }
                    )
                if not cb_exists:
                    candidates.append(
                        {
                            "id": str(uuid.uuid4()),
                            "label": f"{c}→{b}?",
                            "source": c,
                            "target": b,
                            "epistemic_status": "speculative",
                            "speculation_type": "diagram_completion",
                            "rationale": (
                                f"Would complete diagram: {a} →[{f.label}] {b}, "
                                f"{a} →[{g.label}] {c}, missing {c} → {b}"
                            ),
                        }
                    )
    return candidates


def speculation_report(cat: Category) -> str:
    """Human-readable report of speculative possibilities."""
    candidates = speculate_morphisms(cat)
    if not candidates:
        return f"No speculative morphisms found for {cat.name} — category appears structurally complete."

    lines = [f"═══ Speculation Report: {cat.name} ═══", ""]

    by_type: dict[str, list[dict]] = {}
    for c in candidates:
        t = c["speculation_type"]
        by_type.setdefault(t, []).append(c)

    for spec_type, morphs in by_type.items():
        lines.append(f"[{spec_type}] — {len(morphs)} candidate(s):")
        for m in morphs:
            lines.append(f"  ◇ {m['label']}: {m['source']} → {m['target']}")
            if m.get("rationale"):
                lines.append(f"    └ {m['rationale']}")
        lines.append("")

    return "\n".join(lines)
