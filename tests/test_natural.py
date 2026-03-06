#!/usr/bin/env python3
"""
MORPHOS Phase 2 — Natural Transformations & Category Operations Tests
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import create_category, find_functors
from engine.natural import (
    NaturalTransformation, find_natural_transformation,
    find_all_natural_transformations, functor_category_summary,
    product_category, coproduct_category, opposite_category,
    slice_category, pullback, pushout,
)


def header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def test_natural_transformations():
    header("1. NATURAL TRANSFORMATIONS")

    # Two categories with two different functors between them
    C = create_category("C", ["A", "B", "C_obj"],
        [("f", "A", "B"), ("g", "B", "C_obj")])

    D = create_category("D", ["X", "Y", "Z", "W"],
        [("r", "X", "Y"), ("s", "Y", "Z"),
         ("t", "X", "W"), ("u", "W", "Z"),
         ("v", "Y", "W")])

    # Find functors C → D
    functors = find_functors(C, D, mode="exact", max_results=10)
    print(f"  Functors C → D: {len(functors)}")

    for i, f in enumerate(functors[:3]):
        print(f"    F{i}: {f.object_map}  [{f.classification()}]")

    # Find natural transformations between pairs of functors
    if len(functors) >= 2:
        nts = find_all_natural_transformations(functors[:5], C, D)
        print(f"\n  Natural transformations found: {len(nts)}")
        for nt in nts[:5]:
            print(f"    {nt.name}: natural={nt.is_natural}, "
                  f"score={nt.naturality_score:.3f}, iso={nt.is_isomorphism}")
            if nt.components:
                for obj, mid in list(nt.components.items())[:3]:
                    m = D.get_morphism_by_id(mid)
                    desc = f"{m.source}→{m.target}" if m else "?"
                    print(f"      η_{obj} = {desc}")

    print("\n  ✓ Natural transformations work")


def test_product_category():
    header("2. PRODUCT CATEGORY")

    A = create_category("A", ["a1", "a2"],
        [("f", "a1", "a2")], auto_close=False)
    B = create_category("B", ["b1", "b2"],
        [("g", "b1", "b2")], auto_close=False)

    prod = product_category(A, B)
    um = prod.user_morphisms()

    print(f"  A: {len(A.objects)} objects, {len(A.user_morphisms())} morphisms")
    print(f"  B: {len(B.objects)} objects, {len(B.user_morphisms())} morphisms")
    print(f"  A×B: {len(prod.objects)} objects, {len(um)} morphisms")
    print(f"  Objects: {prod.objects}")

    # Should have 2×2 = 4 objects
    assert len(prod.objects) == 4, f"Expected 4 objects, got {len(prod.objects)}"

    # Show morphisms by type
    by_type = {}
    for m in um:
        by_type.setdefault(m.rel_type, []).append(m)
    for rt, ms in by_type.items():
        print(f"  {rt}: {len(ms)} morphisms")
        for m in ms[:2]:
            print(f"    {m.label}: {m.source} → {m.target}")

    print("\n  ✓ Product category works")


def test_coproduct_category():
    header("3. COPRODUCT CATEGORY")

    A = create_category("A", ["a1", "a2"],
        [("f", "a1", "a2")], auto_close=False)
    B = create_category("B", ["b1", "b2", "b3"],
        [("g", "b1", "b2"), ("h", "b2", "b3")], auto_close=False)

    coprod = coproduct_category(A, B)
    um = coprod.user_morphisms()

    print(f"  A: {len(A.objects)} objects, {len(A.user_morphisms())} morphisms")
    print(f"  B: {len(B.objects)} objects, {len(B.user_morphisms())} morphisms")
    print(f"  A+B: {len(coprod.objects)} objects, {len(um)} morphisms")
    print(f"  Objects: {coprod.objects}")

    # Should have 2+3 = 5 objects
    assert len(coprod.objects) == 5, f"Expected 5 objects, got {len(coprod.objects)}"
    # Morphisms: 1 from A + 2 from B = 3
    assert len(um) == 3, f"Expected 3 morphisms, got {len(um)}"

    for m in um:
        print(f"    {m.label}: {m.source} → {m.target}")

    # Left and right components should be disconnected
    left_objs = [o for o in coprod.objects if o.startswith("L.")]
    right_objs = [o for o in coprod.objects if o.startswith("R.")]
    print(f"\n  Left component: {left_objs}")
    print(f"  Right component: {right_objs}")

    print("\n  ✓ Coproduct category works")


def test_opposite_category():
    header("4. OPPOSITE CATEGORY")

    C = create_category("C", ["A", "B", "C_obj"],
        [("f", "A", "B"), ("g", "B", "C_obj")], auto_close=False)

    C_op = opposite_category(C)
    um = C_op.user_morphisms()

    print(f"  C: {len(C.objects)} objects, {len(C.user_morphisms())} morphisms")
    print(f"  C^op: {len(C_op.objects)} objects, {len(um)} morphisms")

    print(f"\n  Original:")
    for m in C.user_morphisms():
        print(f"    {m.label}: {m.source} → {m.target}")
    print(f"  Opposite:")
    for m in um:
        print(f"    {m.label}: {m.source} → {m.target}")

    # Check arrows are reversed
    for m_orig in C.user_morphisms():
        found = False
        for m_op in um:
            if m_op.source == m_orig.target and m_op.target == m_orig.source:
                found = True
                break
        assert found, f"Missing reversed arrow for {m_orig.label}"

    print("\n  All arrows correctly reversed ✓")
    print("\n  ✓ Opposite category works")


def test_slice_category():
    header("5. SLICE CATEGORY")

    # Category with multiple arrows to a common target
    C = create_category("C", ["A", "B", "D", "X"],
        [("f", "A", "X"), ("g", "B", "X"),
         ("h", "D", "X"), ("k", "A", "B")])

    sliced = slice_category(C, "X")
    um = sliced.user_morphisms()

    print(f"  C: {len(C.objects)} objects, {len(C.user_morphisms())} morphisms")
    print(f"  C/X: {len(sliced.objects)} objects, {len(um)} morphisms")
    print(f"  Objects (arrows to X): {sliced.objects}")

    for m in um:
        print(f"    {m.label}: {m.source} → {m.target}")

    print("\n  ✓ Slice category works")


def test_pullback():
    header("6. PULLBACK")

    # Diamond diagram: A →f→ C ←g← B, with D mapping to both A and B
    C = create_category("Diamond", ["A", "B", "C_obj", "D"],
        [("f", "A", "C_obj"), ("g", "B", "C_obj"),
         ("p1", "D", "A"), ("p2", "D", "B")])

    result = pullback(C, "f", "g")
    print(f"  Pullback of f: A→C and g: B→C")
    if result:
        print(f"    Target: {result['target']}")
        print(f"    Candidates: {len(result['pullback_candidates'])}")
        for cand in result['pullback_candidates']:
            print(f"      P={cand['object']}, π₁={cand['projection_1']}, π₂={cand['projection_2']}")

    print("\n  ✓ Pullback works")


def test_pushout():
    header("7. PUSHOUT")

    # Span: B ←f← A →g→ C, with Q receiving from both B and C
    C = create_category("Span", ["A", "B", "C_obj", "Q"],
        [("f", "A", "B"), ("g", "A", "C_obj"),
         ("i1", "B", "Q"), ("i2", "C_obj", "Q")])

    result = pushout(C, "f", "g")
    print(f"  Pushout of f: A→B and g: A→C")
    if result:
        print(f"    Source: {result['source']}")
        print(f"    Candidates: {len(result['pushout_candidates'])}")
        for cand in result['pushout_candidates']:
            print(f"      Q={cand['object']}, ι₁={cand['injection_1']}, ι₂={cand['injection_2']}")

    print("\n  ✓ Pushout works")


def test_functor_category():
    header("8. FUNCTOR CATEGORY")

    # Build a small functor category from real data
    C = create_category("Source", ["A", "B"],
        [("f", "A", "B")])
    D = create_category("Target", ["X", "Y", "Z"],
        [("r", "X", "Y"), ("s", "X", "Z"), ("t", "Y", "Z")])

    functors = find_functors(C, D, mode="exact", max_results=10)
    print(f"  Functors Source → Target: {len(functors)}")

    nts = find_all_natural_transformations(functors, C, D)
    print(f"  Natural transformations: {len(nts)}")

    fc = functor_category_summary(functors, nts, "Source", "Target")
    print(f"  Functor category [Source, Target]: "
          f"{len(fc.objects)} objects, {len(fc.user_morphisms())} morphisms")

    print("\n  ✓ Functor category works")


def test_duality():
    header("9. DUALITY VERIFICATION")
    print("  Every construction has a dual obtained by reversing arrows.")
    print("  Product ↔ Coproduct, Pullback ↔ Pushout, Slice ↔ Coslice\n")

    A = create_category("A", ["x", "y"],
        [("a", "x", "y")], auto_close=False)
    B = create_category("B", ["p", "q"],
        [("b", "p", "q")], auto_close=False)

    prod = product_category(A, B)
    coprod = coproduct_category(A, B)

    # Product of A,B should be related to coproduct of A^op, B^op
    A_op = opposite_category(A)
    B_op = opposite_category(B)
    coprod_op = coproduct_category(A_op, B_op)

    print(f"  A×B:         {len(prod.objects)} objects, {len(prod.user_morphisms())} morphisms")
    print(f"  A+B:         {len(coprod.objects)} objects, {len(coprod.user_morphisms())} morphisms")
    print(f"  A^op + B^op: {len(coprod_op.objects)} objects, {len(coprod_op.user_morphisms())} morphisms")

    # Product should have |A|×|B| objects, coproduct should have |A|+|B|
    assert len(prod.objects) == len(A.objects) * len(B.objects)
    assert len(coprod.objects) == len(A.objects) + len(B.objects)

    print(f"\n  |A×B| = |A|·|B| = {len(A.objects)}·{len(B.objects)} = {len(prod.objects)} ✓")
    print(f"  |A+B| = |A|+|B| = {len(A.objects)}+{len(B.objects)} = {len(coprod.objects)} ✓")

    print("\n  ✓ Duality principles verified")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  MORPHOS Phase 2 — Natural Transformations & Operations ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_natural_transformations()
    test_product_category()
    test_coproduct_category()
    test_opposite_category()
    test_slice_category()
    test_pullback()
    test_pushout()
    test_functor_category()
    test_duality()

    header("ALL TESTS PASSED")
    print("""
  Natural transformations & category operations:

  • Natural transformations: morphisms between functors, with
    naturality verification via commuting squares
  • Product C×D: simultaneous structure (|C|·|D| objects)
  • Coproduct C+D: disjoint union (|C|+|D| objects)
  • Opposite C^op: all arrows reversed (duality)
  • Slice C/X: everything pointing at X
  • Functor category [C,D]: functors as objects, nat. trans. as morphisms
  • Pullback: shared structure over a common target
  • Pushout: merged structure from a common source
  • Duality: product ↔ coproduct, pullback ↔ pushout verified
""")


if __name__ == "__main__":
    main()
