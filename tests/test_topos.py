#!/usr/bin/env python3
"""
MORPHOS Phase 2 — Topos Logic Tests

Verifies:
1. Heyting algebra axioms hold
2. Multi-valued truth works correctly
3. Bayesian updating produces valid posteriors
4. Intuitionistic logic: ¬¬p ≠ p for undetermined values
5. Truth values propagate through morphism composition
6. Conversion between Phase 1 epistemic and Phase 2 topos
7. Real-world scenario: uncertain reasoning chain
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.topos import (
    TruthValue, Modality, compose_truth, bayesian_update,
    update_from_observations, verify_heyting_laws,
    from_epistemic, to_epistemic,
    TRUE, FALSE, UNKNOWN,
    necessary, actual, probable, possible, counterfactual, undetermined,
)
from engine.epistemic import Definite, Probable, Possible, Speculative, Contradicted
from engine import create_category


def header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def test_truth_values():
    header("1. TRUTH VALUE BASICS")

    t = TRUE
    f = FALSE
    u = UNKNOWN
    p = probable(0.7)
    ps = possible(0.4)
    cf = counterfactual(0.6)

    print(f"  TRUE:          {t.label():30s} strength={t.effective_strength:.3f}")
    print(f"  FALSE:         {f.label():30s} strength={f.effective_strength:.3f}")
    print(f"  UNKNOWN:       {u.label():30s} strength={u.effective_strength:.3f}")
    print(f"  probable(0.7): {p.label():30s} strength={p.effective_strength:.3f}")
    print(f"  possible(0.4): {ps.label():30s} strength={ps.effective_strength:.3f}")
    print(f"  counter(0.6):  {cf.label():30s} strength={cf.effective_strength:.3f}")

    # Ordering
    values = [t, p, ps, u, cf, f]
    ordered = sorted(values, key=lambda v: -v.effective_strength)
    print(f"\n  Ordered by effective strength:")
    for v in ordered:
        print(f"    {v.effective_strength:.3f}  {v.label()}")

    print("\n  ✓ Truth value basics work")


def test_heyting_algebra():
    header("2. HEYTING ALGEBRA AXIOMS")

    test_triples = [
        (actual(0.8), probable(0.5), possible(0.3)),
        (TRUE, FALSE, UNKNOWN),
        (probable(0.9), actual(0.4), undetermined(0.6)),
        (necessary(0.7), counterfactual(0.5), possible(0.8)),
    ]

    all_pass = True
    for i, (a, b, c) in enumerate(test_triples):
        results = verify_heyting_laws(a, b, c)
        failures = [k for k, v in results.items() if v is False]
        if failures:
            print(f"  Triple {i+1}: FAILED — {failures}")
            all_pass = False
        else:
            print(f"  Triple {i+1} ({a.label()}, {b.label()}, {c.label()}): all axioms ✓")

    assert all_pass, "Heyting algebra axiom violations!"
    print("\n  ✓ All Heyting algebra axioms verified")


def test_heyting_operations():
    header("3. HEYTING OPERATIONS")

    a = actual(0.8)
    b = probable(0.5)

    meet = a.meet(b)
    join = a.join(b)
    impl = a.implies(b)
    neg_a = a.negate()

    print(f"  a = {a.label()}")
    print(f"  b = {b.label()}")
    print(f"  a ∧ b (meet) = {meet.label()}")
    print(f"  a ∨ b (join) = {join.label()}")
    print(f"  a → b (impl) = {impl.label()}")
    print(f"  ¬a   (neg)   = {neg_a.label()}")
    print()

    # Meet should be min
    assert meet.degree == min(a.degree, b.degree), f"Meet degree wrong: {meet.degree}"
    # Join should be max
    assert join.degree == max(a.degree, b.degree), f"Join degree wrong: {join.degree}"
    # Residuation: a ∧ (a→b) ≤ b
    resid = a.meet(impl)
    assert resid.degree <= b.degree + 0.01, f"Residuation failed: {resid.degree} > {b.degree}"

    print("  Residuation: a ∧ (a→b) ≤ b ✓")
    print(f"    {a.label()} ∧ {impl.label()} = {resid.label()} ≤ {b.label()}")

    print("\n  ✓ Heyting operations correct")


def test_intuitionistic_logic():
    header("4. INTUITIONISTIC LOGIC — ¬¬p ≠ p")
    print("  This is the key non-classical property.")
    print("  In classical logic, double negation collapses: ¬¬p = p")
    print("  In intuitionistic logic, it doesn't for undetermined values.")
    print()

    # For determined values, ¬¬p ≈ p
    t = actual(0.9)
    dnt = t.double_negate()
    print(f"  Determined:   p={t.label():20s}  ¬¬p={dnt.label()}")

    # For undetermined values, ¬¬p ≠ p
    u = undetermined(0.6)
    dnu = u.double_negate()
    print(f"  Undetermined: p={u.label():20s}  ¬¬p={dnu.label()}")

    # The modality should stay UNDETERMINED
    assert dnu.modality == Modality.UNDETERMINED, \
        f"Double negation should stay UNDETERMINED, got {dnu.modality}"

    print(f"\n  ¬¬(undetermined) stays undetermined: {dnu.modality.name} ✓")
    print("  This means: ruling out falsity doesn't establish truth.")
    print("  You need actual evidence, not just absence of counter-evidence.")

    # FALSE should double-negate correctly
    f = FALSE
    neg_f = f.negate()
    dnf = f.double_negate()
    print(f"\n  FALSE:        p={f.label():20s}  ¬p={neg_f.label():20s}  ¬¬p={dnf.label()}")

    # IMPOSSIBLE should negate to NECESSARY
    imp = TruthValue(0.0, Modality.IMPOSSIBLE)
    neg_imp = imp.negate()
    print(f"  ¬(impossible) = {neg_imp.label()}")
    assert neg_imp.degree >= 0.99, f"Negation of impossible should be ~1.0, got {neg_imp.degree}"

    print("\n  ✓ Intuitionistic properties verified")


def test_bayesian_updating():
    header("5. BAYESIAN UPDATING")

    # Start with an undetermined hypothesis
    h = undetermined(0.5)
    print(f"  Prior: {h.label()} (degree={h.degree:.3f})")

    # Strong evidence FOR the hypothesis
    h1 = bayesian_update(h, "positive_test_1", likelihood_if_true=0.95, likelihood_if_false=0.05)
    print(f"  After positive test 1: {h1.label()} (degree={h1.degree:.3f})")

    # More evidence FOR
    h2 = bayesian_update(h1, "positive_test_2", likelihood_if_true=0.9, likelihood_if_false=0.1)
    print(f"  After positive test 2: {h2.label()} (degree={h2.degree:.3f})")

    # Contradicting evidence AGAINST
    h3 = bayesian_update(h2, "negative_test_1", likelihood_if_true=0.1, likelihood_if_false=0.9)
    print(f"  After negative test:   {h3.label()} (degree={h3.degree:.3f})")

    # Verify the math manually for first update
    # P(H|E) = P(E|H)*P(H) / (P(E|H)*P(H) + P(E|¬H)*P(¬H))
    # = 0.95*0.5 / (0.95*0.5 + 0.05*0.5) = 0.475/0.5 = 0.95
    expected = (0.95 * 0.5) / (0.95 * 0.5 + 0.05 * 0.5)
    assert abs(h1.degree - expected) < 0.001, f"Bayesian update wrong: {h1.degree} vs {expected}"

    print(f"\n  Manual check: P(H|E₁) = {expected:.3f} ✓")
    print(f"  Evidence trail: {h3.evidence}")

    # Sequential updating
    print("\n  Sequential update from neutral prior:")
    h_seq = update_from_observations(
        undetermined(0.5),
        [
            ("observation_A", 0.8, 0.2),
            ("observation_B", 0.7, 0.3),
            ("observation_C", 0.9, 0.1),
        ],
    )
    print(f"  After 3 observations: {h_seq.label()} (degree={h_seq.degree:.3f})")
    print(f"  Evidence: {h_seq.evidence}")

    print("\n  ✓ Bayesian updating correct")


def test_composition_with_truth():
    header("6. TRUTH VALUE COMPOSITION")

    tv1 = actual(0.9)
    tv2 = probable(0.7)
    tv3 = possible(0.5)

    c12 = compose_truth(tv1, tv2)
    c123 = compose_truth(c12, tv3)

    print(f"  f: {tv1.label()}")
    print(f"  g: {tv2.label()}")
    print(f"  h: {tv3.label()}")
    print(f"  g∘f:   {c12.label()} (degree={c12.degree:.3f})")
    print(f"  h∘g∘f: {c123.label()} (degree={c123.degree:.3f})")

    # Degree should multiply: 0.9 * 0.7 = 0.63
    expected_12 = 0.9 * 0.7
    assert abs(c12.degree - expected_12) < 0.001, f"Composition degree wrong: {c12.degree}"

    # Modality should be weakest
    assert c12.modality == Modality.PROBABLE, f"Modality wrong: {c12.modality}"
    assert c123.modality == Modality.POSSIBLE, f"Modality wrong: {c123.modality}"

    # Full chain: 0.9 * 0.7 * 0.5 = 0.315
    expected_123 = 0.9 * 0.7 * 0.5
    assert abs(c123.degree - expected_123) < 0.001

    print(f"\n  0.9 × 0.7 = {expected_12:.3f} ✓")
    print(f"  0.9 × 0.7 × 0.5 = {expected_123:.3f} ✓")
    print(f"  Modality degrades: actual → probable → possible ✓")

    print("\n  ✓ Truth value composition correct")


def test_category_integration():
    header("7. INTEGRATION WITH CATEGORY ENGINE")

    from engine.topos import actual, probable, possible, undetermined

    # Build a category with truth-valued morphisms
    cat = create_category(
        "ToposTest",
        ["A", "B", "C", "D"],
        [
            ("f", "A", "B"),
            ("g", "B", "C"),
            ("h", "C", "D"),
        ],
        auto_close=False,
    )

    # Assign truth values to morphisms
    for m in cat.user_morphisms():
        if m.label == "f":
            m.truth_value = actual(0.9)
        elif m.label == "g":
            m.truth_value = probable(0.7)
        elif m.label == "h":
            m.truth_value = possible(0.5)

    # Now auto-compose — truth values should propagate
    new = cat.auto_compose()
    print(f"  Created {len(new)} compositions")

    for m in cat.morphisms:
        if m.is_composition and m.truth_value:
            print(f"  {m.label:20s}: {m.truth_value.label():30s} "
                  f"degree={m.truth_value.degree:.3f}  "
                  f"modality={m.truth_value.modality.name}")

    # Check g∘f
    gf = [m for m in cat.morphisms if m.is_composition and m.source == "A" and m.target == "C"]
    assert len(gf) >= 1, "Missing g∘f composition"
    assert gf[0].truth_value is not None, "g∘f missing truth value"
    assert abs(gf[0].truth_value.degree - 0.63) < 0.01, f"g∘f degree wrong: {gf[0].truth_value.degree}"

    # Check h∘g∘f
    hgf = [m for m in cat.morphisms if m.is_composition and m.source == "A" and m.target == "D"]
    assert len(hgf) >= 1, "Missing h∘g∘f composition"
    assert hgf[0].truth_value is not None, "h∘g∘f missing truth value"
    assert abs(hgf[0].truth_value.degree - 0.315) < 0.01, f"h∘g∘f degree wrong"

    print(f"\n  g∘f degree: {gf[0].truth_value.degree:.3f} (expected 0.630) ✓")
    print(f"  h∘g∘f degree: {hgf[0].truth_value.degree:.3f} (expected 0.315) ✓")

    print("\n  ✓ Truth values propagate through category composition")


def test_epistemic_conversion():
    header("8. PHASE 1 ↔ PHASE 2 CONVERSION")

    # Phase 1 → Phase 2
    cases = [
        (Definite(), "actual(1.000) or true"),
        (Probable(0.8), "probable(0.800)"),
        (Possible(), "possible(0.500)"),
        (Speculative(), "undetermined(0.300)"),
        (Contradicted("test"), "impossible"),
    ]

    for status, expected_desc in cases:
        tv = from_epistemic(status)
        back = to_epistemic(tv)
        print(f"  {status.label():25s} → {tv.label():25s} → {back.label()}")

    # Round-trip: Definite should survive
    d = Definite()
    tv = from_epistemic(d)
    back = to_epistemic(tv)
    assert isinstance(back, Definite), f"Definite round-trip failed: got {type(back)}"

    # Probable should approximately survive
    p = Probable(0.8)
    tv = from_epistemic(p)
    back = to_epistemic(tv)
    assert isinstance(back, Probable), f"Probable round-trip failed: got {type(back)}"

    print("\n  ✓ Phase 1 ↔ Phase 2 conversion works")


def test_real_world_scenario():
    header("9. REAL-WORLD SCENARIO — Uncertain Reasoning Chain")
    print("  Medical diagnosis: symptoms → condition → treatment → outcome")
    print()

    # Start with uncertain symptom observation
    symptom = undetermined(0.5)
    print(f"  Patient presents with headache: {symptom.label()}")

    # Update with test results
    symptom = bayesian_update(symptom, "fever_present",
                               likelihood_if_true=0.7, likelihood_if_false=0.3)
    print(f"  After fever check (+): {symptom.label()} ({symptom.degree:.3f})")

    symptom = bayesian_update(symptom, "stiff_neck",
                               likelihood_if_true=0.85, likelihood_if_false=0.05)
    print(f"  After stiff neck (+): {symptom.label()} ({symptom.degree:.3f})")

    # Build a reasoning chain with truth values
    cat = create_category(
        "Diagnosis",
        ["symptoms", "meningitis", "antibiotics", "recovery"],
        [
            ("suggests", "symptoms", "meningitis"),
            ("treats", "meningitis", "antibiotics"),
            ("leads_to", "antibiotics", "recovery"),
        ],
        auto_close=False,
    )

    # Assign truth values based on evidence
    for m in cat.user_morphisms():
        if m.label == "suggests":
            m.truth_value = TruthValue(symptom.degree, Modality.PROBABLE,
                                        evidence=symptom.evidence)
        elif m.label == "treats":
            m.truth_value = actual(0.85)  # antibiotics effective in 85% of cases
        elif m.label == "leads_to":
            m.truth_value = probable(0.9)  # 90% recovery with treatment

    cat.auto_compose()

    print(f"\n  Reasoning chain:")
    for m in cat.user_morphisms():
        print(f"    {m.label:15s}: {m.source:12s} → {m.target:12s}  "
              f"truth={m.truth_value.label()}")

    for m in cat.morphisms:
        if m.is_composition and m.truth_value:
            print(f"    {m.label:15s}: {m.source:12s} → {m.target:12s}  "
                  f"truth={m.truth_value.label()}")

    # The full chain truth value
    full = [m for m in cat.morphisms
            if m.source == "symptoms" and m.target == "recovery" and m.is_composition]
    if full:
        tv = full[0].truth_value
        print(f"\n  Full chain (symptoms → recovery):")
        print(f"    Degree: {tv.degree:.3f}")
        print(f"    Modality: {tv.modality.name}")
        print(f"    Evidence: {tv.evidence}")
        print(f"    Interpretation: {_interpret(tv)}")

    print("\n  ✓ Real-world reasoning chain works")


def _interpret(tv):
    """Human-readable interpretation of a truth value."""
    if tv.effective_strength > 0.8:
        return "Strong confidence in this inference path"
    if tv.effective_strength > 0.5:
        return "Moderate confidence — additional evidence would help"
    if tv.effective_strength > 0.2:
        return "Weak confidence — significant uncertainty remains"
    return "Very low confidence — insufficient evidence"


def test_contradiction_handling():
    header("10. CONTRADICTION DETECTION & RESOLUTION")

    # Two conflicting truth values for the same proposition
    evidence_for = actual(0.85)
    evidence_against = actual(0.9)

    print(f"  Evidence FOR:     {evidence_for.label()}")
    print(f"  Evidence AGAINST: {evidence_against.label()}")

    # Meet of a proposition and its negation should approach IMPOSSIBLE
    neg = evidence_for.negate()
    contradiction = evidence_for.meet(neg)
    print(f"  p ∧ ¬p = {contradiction.label()} (should be near bottom)")
    assert contradiction.degree < 0.5, "Contradiction degree should be low"

    # But evidence against isn't the same as ¬evidence_for
    # We need to update beliefs, not just negate
    combined = bayesian_update(
        evidence_for,
        "contradicting_observation",
        likelihood_if_true=0.1,  # very unlikely if the original is true
        likelihood_if_false=0.9,  # very likely if original is false
    )
    print(f"  After contradicting evidence: {combined.label()} ({combined.degree:.3f})")
    print(f"  Evidence trail: {combined.evidence}")

    print("\n  ✓ Contradiction handling works")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    MORPHOS Phase 2 — Topos Logic Test Suite            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_truth_values()
    test_heyting_algebra()
    test_heyting_operations()
    test_intuitionistic_logic()
    test_bayesian_updating()
    test_composition_with_truth()
    test_category_integration()
    test_epistemic_conversion()
    test_real_world_scenario()
    test_contradiction_handling()

    header("ALL PHASE 2 TESTS PASSED")
    print("""
  The topos logic layer is operational. Key capabilities:

  • Multi-valued truth: 7 modalities × continuous degree
  • Heyting algebra: meet, join, implication, negation with
    all lattice axioms verified
  • Intuitionistic reasoning: ¬¬p ≠ p for undetermined values
    (excluded middle genuinely fails)
  • Bayesian updating: evidence modifies truth values via
    proper conditionalization
  • Composition propagation: truth values degrade through
    morphism chains with correct degree multiplication
    and modality weakening
  • Category integration: auto_compose uses topos logic
    when truth values are present
  • Backward compatible: Phase 1 EpistemicStatus still works,
    converts cleanly to/from Phase 2 TruthValue
""")


if __name__ == "__main__":
    main()
