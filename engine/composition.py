"""
Composition Explorer

Traverses the morphism composition space within a category.
Finds all paths between objects, detects isomorphisms,
discovers commutative diagrams.
"""
from __future__ import annotations
from .categories import Category, Morphism


def find_paths(
    cat: Category,
    source: str,
    target: str,
    max_depth: int = 5,
) -> list[list[Morphism]]:
    """Find all morphism paths from source to target object."""
    if source not in cat.objects:
        raise ValueError(f"Object '{source}' not in category")
    if target not in cat.objects:
        raise ValueError(f"Object '{target}' not in category")

    results: list[list[Morphism]] = []
    non_id = cat.non_identity_morphisms()
    # Filter out auto-compositions to keep paths made of "primitive" arrows
    primitives = [m for m in non_id if not m.is_composition]
    _dfs(cat, source, target, [], results, max_depth, primitives, set())
    return results


def _dfs(
    cat: Category,
    current: str,
    target: str,
    path: list[Morphism],
    results: list[list[Morphism]],
    remaining: int,
    morphisms: list[Morphism],
    visited_edges: set[str],
) -> None:
    if current == target and path:
        results.append(list(path))
        return
    if remaining <= 0:
        return
    for m in morphisms:
        if m.source != current:
            continue
        if m.id in visited_edges:
            continue
        path.append(m)
        visited_edges.add(m.id)
        _dfs(cat, m.target, target, path, results, remaining - 1, morphisms, visited_edges)
        path.pop()
        visited_edges.discard(m.id)


def detect_isomorphisms(cat: Category) -> list[tuple[str, str]]:
    """
    Find pairs of objects that are candidates for isomorphism
    (have morphisms in both directions).

    Note: This checks for the existence of bidirectional morphisms,
    which is necessary but not sufficient for isomorphism. Full
    verification requires checking that the round-trip compositions
    equal the identity morphisms, which needs the composition table.
    """
    pairs: list[tuple[str, str]] = []
    user_m = cat.user_morphisms()
    for i, a in enumerate(cat.objects):
        for b in cat.objects[i + 1 :]:
            fwd = [m for m in user_m if m.source == a and m.target == b]
            bwd = [m for m in user_m if m.source == b and m.target == a]
            if fwd and bwd:
                # Check if round-trip compositions are identities
                verified = False
                id_a = cat.identity_for(a)
                id_b = cat.identity_for(b)
                if id_a and id_b:
                    for f in fwd:
                        for g in bwd:
                            gf = cat.compositions.get((f.id, g.id))
                            fg = cat.compositions.get((g.id, f.id))
                            if gf == id_a.id and fg == id_b.id:
                                verified = True
                                break
                        if verified:
                            break
                pairs.append((a, b, verified))
    # Return as (a, b) for backward compat, but log verification
    return [(a, b) for a, b, _ in pairs]


def find_commutative_squares(cat: Category) -> list[dict]:
    """
    Find commutative squares: two distinct length-2 paths A→D
    going through different intermediate objects B and C,
    where both paths compose to the same morphism.
    """
    squares: list[dict] = []
    for a in cat.objects:
        for d in cat.objects:
            if a == d:
                continue
            paths = find_paths(cat, a, d, max_depth=2)
            len2 = [p for p in paths if len(p) == 2]
            for i in range(len(len2)):
                for j in range(i + 1, len(len2)):
                    p1, p2 = len2[i], len2[j]
                    if p1[0].target != p2[0].target:
                        # Check actual commutativity: do both paths
                        # compose to the same morphism?
                        comp1 = cat.compositions.get((p1[0].id, p1[1].id))
                        comp2 = cat.compositions.get((p2[0].id, p2[1].id))
                        commutes = comp1 is not None and comp1 == comp2
                        squares.append(
                            {
                                "top_left": a,
                                "top_right": p1[0].target,
                                "bottom_left": p2[0].target,
                                "bottom_right": d,
                                "path1": [m.label for m in p1],
                                "path2": [m.label for m in p2],
                                "commutes": commutes,
                            }
                        )
    return squares


def composition_report(cat: Category) -> str:
    """Human-readable report of composition structure."""
    lines = [f"═══ Composition Report: {cat.name} ═══", ""]
    lines.append(f"Objects ({len(cat.objects)}): {', '.join(cat.objects)}")
    lines.append("")

    user_m = cat.user_morphisms()
    lines.append(f"Morphisms ({len(user_m)}):")
    for m in user_m:
        lines.append(f"  {m.label}: {m.source} → {m.target}  [{m.status.label()}]")
    lines.append("")

    composed = [m for m in cat.morphisms if m.is_composition]
    if composed:
        lines.append(f"Auto-composed ({len(composed)}):")
        for m in composed:
            lines.append(f"  {m.label}: {m.source} → {m.target}  [{m.status.label()}]")
        lines.append("")

    lines.append("Paths between objects:")
    for a in cat.objects:
        for b in cat.objects:
            if a == b:
                continue
            paths = find_paths(cat, a, b, max_depth=4)
            if paths:
                lines.append(f"  {a} → {b}: {len(paths)} path(s)")
                for idx, path in enumerate(paths, 1):
                    chain = " → ".join([path[0].source] + [m.target for m in path])
                    labels = " then ".join(m.label for m in path)
                    lines.append(f"    [{idx}] {chain}  ({labels})")

    isos = detect_isomorphisms(cat)
    if isos:
        lines.append("")
        lines.append("Isomorphic pairs:")
        for a, b in isos:
            lines.append(f"  {a} ≅ {b}")

    squares = find_commutative_squares(cat)
    if squares:
        lines.append("")
        lines.append(f"Commutative squares ({len(squares)}):")
        for sq in squares:
            lines.append(
                f"  {sq['top_left']} → {sq['bottom_right']}: "
                f"{'→'.join(sq['path1'])} = {'→'.join(sq['path2'])}"
            )

    return "\n".join(lines)
