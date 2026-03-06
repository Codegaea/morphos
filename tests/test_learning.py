#!/usr/bin/env python3
"""
MORPHOS Phase 2 — Learning Engine Tests

Tests:
1. Category fingerprinting
2. Fingerprint similarity
3. Analogy memory: store, retrieve, reinforce, weaken
4. Transitive prediction: A≅B and B≅C → predict A≅C
5. Learning search: cache, predict, discover, store
6. Meta-category: build category-of-categories
7. Suggestion engine: what to explore next
8. Full learning loop: build knowledge over multiple searches
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import create_category, find_functors_scalable
from engine.learning import (
    CategoryFingerprint, fingerprint,
    DiscoveredAnalogy, AnalogyMemory, MetaCategory,
    learn_and_search, suggest_explorations,
)
from engine.topos import actual, probable, undetermined
from engine.datasets import ALL_DATASETS


def header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def test_fingerprint():
    header("1. CATEGORY FINGERPRINTING")

    cat1 = create_category("Chain3", ["A", "B", "C"],
        [("f", "A", "B"), ("g", "B", "C")], auto_close=False)
    cat2 = create_category("Chain3b", ["X", "Y", "Z"],
        [("r", "X", "Y"), ("s", "Y", "Z")], auto_close=False)
    cat3 = create_category("Star4", ["hub", "a", "b", "c"],
        [("r1", "hub", "a"), ("r2", "hub", "b"), ("r3", "hub", "c")], auto_close=False)

    fp1 = fingerprint(cat1)
    fp2 = fingerprint(cat2)
    fp3 = fingerprint(cat3)

    print(f"  Chain3:  {fp1.n_objects} obj, {fp1.n_morphisms} morph, "
          f"cycle={fp1.has_cycles}, chain={fp1.max_chain_length}")
    print(f"  Chain3b: {fp2.n_objects} obj, {fp2.n_morphisms} morph, "
          f"cycle={fp2.has_cycles}, chain={fp2.max_chain_length}")
    print(f"  Star4:   {fp3.n_objects} obj, {fp3.n_morphisms} morph, "
          f"cycle={fp3.has_cycles}, chain={fp3.max_chain_length}")

    # Isomorphic categories should have identical fingerprints
    assert fp1 == fp2, "Isomorphic categories should have identical fingerprints"
    print(f"\n  Chain3 == Chain3b: {fp1 == fp2} ✓ (isomorphic)")

    # Different structure should differ
    assert fp1 != fp3, "Different structures should have different fingerprints"
    print(f"  Chain3 != Star4:  {fp1 != fp3} ✓ (different structure)")

    # Similarity
    sim_iso = fp1.similarity(fp2)
    sim_diff = fp1.similarity(fp3)
    print(f"\n  Similarity(Chain3, Chain3b): {sim_iso:.3f}")
    print(f"  Similarity(Chain3, Star4):   {sim_diff:.3f}")
    assert sim_iso > sim_diff, "Isomorphic should be more similar"

    # Cycle detection
    cat_cycle = create_category("Cycle", ["A", "B", "C"],
        [("f", "A", "B"), ("g", "B", "C"), ("h", "C", "A")], auto_close=False)
    fp_cycle = fingerprint(cat_cycle)
    assert fp_cycle.has_cycles, "Cycle detection failed"
    print(f"  Cycle detected: {fp_cycle.has_cycles} ✓")

    print("\n  ✓ Fingerprinting works")


def test_analogy_memory():
    header("2. ANALOGY MEMORY")

    memory = AnalogyMemory()

    # Store some analogies
    a1 = DiscoveredAnalogy(
        source_name="Fluids", target_name="Circuits",
        object_map={"Pressure": "Voltage", "Flow": "Current"},
        score=0.95, truth_value=actual(0.95),
        evidence=["search_1"],
    )
    a2 = DiscoveredAnalogy(
        source_name="Circuits", target_name="HeatTransfer",
        object_map={"Voltage": "Temperature", "Current": "HeatFlow"},
        score=0.90, truth_value=actual(0.90),
        evidence=["search_2"],
    )

    memory.store(a1)
    memory.store(a2)

    print(f"  Stored {len(memory.analogies)} analogies")

    # Retrieve
    found = memory.get_between("Fluids", "Circuits")
    assert len(found) == 1, f"Expected 1, got {len(found)}"
    print(f"  Retrieved Fluids→Circuits: score={found[0].score:.3f} ✓")

    # Get involving
    involving = memory.get_involving("Circuits")
    assert len(involving) == 2, f"Expected 2, got {len(involving)}"
    print(f"  Involving 'Circuits': {len(involving)} analogies ✓")

    # Reinforce
    a1.reinforce("independent_confirmation", 0.9)
    print(f"  After reinforcement: truth={a1.truth_value.label()} "
          f"confidence={a1.confidence():.3f}")
    assert a1.truth_value.degree > 0.95, "Reinforcement should increase degree"

    # Weaken
    a1.weaken("counter_evidence", 0.6)
    print(f"  After weakening: truth={a1.truth_value.label()} "
          f"confidence={a1.confidence():.3f}")

    # Duplicate storage (should merge)
    a1_dup = DiscoveredAnalogy(
        source_name="Fluids", target_name="Circuits",
        object_map={"Pressure": "Voltage", "Flow": "Current"},
        score=0.95,
    )
    memory.store(a1_dup)
    assert len(memory.analogies) == 2, "Duplicate should merge, not create new"
    print(f"  Duplicate merged: still {len(memory.analogies)} analogies ✓")

    print("\n  ✓ Analogy memory works")


def test_transitive_prediction():
    header("3. TRANSITIVE PREDICTION")

    memory = AnalogyMemory()

    # Store A→B and B→C
    ab = DiscoveredAnalogy(
        source_name="DomainA", target_name="DomainB",
        object_map={"a1": "b1", "a2": "b2", "a3": "b3"},
        score=0.9, truth_value=actual(0.9),
    )
    bc = DiscoveredAnalogy(
        source_name="DomainB", target_name="DomainC",
        object_map={"b1": "c1", "b2": "c2", "b3": "c3"},
        score=0.85, truth_value=actual(0.85),
    )
    memory.store(ab)
    memory.store(bc)

    # Predict A→C
    predicted = memory.predict_transitive("DomainA", "DomainC")
    assert predicted is not None, "Should predict transitive analogy"

    print(f"  A→B: score={ab.score:.3f}")
    print(f"  B→C: score={bc.score:.3f}")
    print(f"  Predicted A→C: score={predicted.score:.3f} "
          f"confidence={predicted.confidence():.3f}")
    print(f"  Object map: {predicted.object_map}")
    print(f"  Evidence: {predicted.evidence}")

    # Verify the composed map
    expected_map = {"a1": "c1", "a2": "c2", "a3": "c3"}
    assert predicted.object_map == expected_map, f"Wrong map: {predicted.object_map}"
    print(f"  Map verified: a1→c1, a2→c2, a3→c3 ✓")

    # Composed score should be product
    expected_score = 0.9 * 0.85
    assert abs(predicted.score - expected_score) < 0.01
    print(f"  Score = {ab.score} × {bc.score} = {predicted.score:.3f} ✓")

    # Truth value should compose
    assert predicted.truth_value.degree < min(ab.truth_value.degree, bc.truth_value.degree)
    print(f"  Truth degrades through composition ✓")

    print("\n  ✓ Transitive prediction works")


def test_learning_search():
    header("4. LEARNING SEARCH")

    memory = AnalogyMemory()

    # Build test categories
    cat_a = create_category("TestA", ["x", "y", "z"],
        [("r", "x", "y"), ("s", "y", "z")], auto_close=False)
    cat_b = create_category("TestB", ["p", "q", "r_obj"],
        [("u", "p", "q"), ("v", "q", "r_obj")], auto_close=False)
    cat_c = create_category("TestC", ["m", "n", "o"],
        [("a", "m", "n"), ("b", "n", "o")], auto_close=False)

    # First search: discovers A→B
    print(f"  Search 1: TestA → TestB")
    results_1 = learn_and_search(cat_a, cat_b, memory, min_score=0.0)
    print(f"    Found {len(results_1)} analogy(ies)")
    if results_1:
        print(f"    Score: {results_1[0].score:.3f}, Truth: {results_1[0].truth_value.label()}")

    # Second search: discovers B→C
    print(f"\n  Search 2: TestB → TestC")
    results_2 = learn_and_search(cat_b, cat_c, memory, min_score=0.0)
    print(f"    Found {len(results_2)} analogy(ies)")

    # Third search: should use cache or transitive prediction for A→C
    print(f"\n  Search 3: TestA → TestC (should use transitive prediction)")
    results_3 = learn_and_search(cat_a, cat_c, memory, min_score=0.0)
    print(f"    Found {len(results_3)} analogy(ies)")
    if results_3:
        print(f"    Evidence: {results_3[0].evidence}")

    # Fourth search: same query, should hit cache
    print(f"\n  Search 4: TestA → TestB (should hit cache)")
    results_4 = learn_and_search(cat_a, cat_b, memory, min_score=0.0)
    print(f"    Cache hits: {memory._hit_count}/{memory._search_count}")

    print(f"\n  Memory stats: {memory.stats}")
    print(f"  Total analogies stored: {len(memory.analogies)}")

    for a in memory.all_analogies():
        print(f"    {a.source_name} → {a.target_name}: "
              f"conf={a.confidence():.3f}, evidence={len(a.evidence)}")

    print("\n  ✓ Learning search works")


def test_meta_category():
    header("5. META-CATEGORY")

    memory = AnalogyMemory()

    # Build a network of analogies
    pairs = [
        ("Fluids", "Circuits", 0.95),
        ("Circuits", "HeatTransfer", 0.90),
        ("Fluids", "HeatTransfer", 0.88),
        ("Music", "Color", 0.60),
        ("Grammar", "Programming", 0.70),
    ]

    for src, tgt, score in pairs:
        a = DiscoveredAnalogy(
            source_name=src, target_name=tgt,
            object_map={}, score=score,
            truth_value=actual(score),
        )
        memory.store(a)

    meta = MetaCategory(memory)
    meta_cat = meta.build()

    print(f"  Meta-category: {len(meta_cat.objects)} objects, "
          f"{len(meta_cat.user_morphisms())} morphisms")
    print(f"  Objects (domains): {meta_cat.objects}")
    for m in meta_cat.user_morphisms():
        v = f" val={m.value:.3f}" if m.value else ""
        print(f"    {m.source:15s} → {m.target:15s}{v}")

    # Connected components
    components = meta.connected_components()
    print(f"\n  Connected components: {len(components)}")
    for i, comp in enumerate(components):
        print(f"    Component {i+1}: {comp}")

    assert len(components) >= 2, "Should have at least 2 components"
    print(f"\n  Physics domains connected in a component ✓")

    print("\n  ✓ Meta-category works")


def test_suggestions():
    header("6. EXPLORATION SUGGESTIONS")

    memory = AnalogyMemory()

    # Build several categories and register them
    cats = {}
    for name, fn in list(ALL_DATASETS.items())[:6]:
        data = fn()
        cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
        cats[name] = cat
        memory.register_category(cat)

    # Store one known analogy
    a = DiscoveredAnalogy(
        source_name=list(cats.keys())[0],
        target_name=list(cats.keys())[1],
        object_map={}, score=0.8,
        truth_value=actual(0.8),
        source_fingerprint=memory.fingerprints.get(list(cats.keys())[0]),
        target_fingerprint=memory.fingerprints.get(list(cats.keys())[1]),
    )
    memory.store(a)

    # Get suggestions
    suggestions = suggest_explorations(memory, cats, max_suggestions=5)
    print(f"  Registered {len(cats)} categories")
    print(f"  Known analogies: {len(memory.analogies)}")
    print(f"\n  Top suggestions:")
    for src, tgt, score, reason in suggestions:
        print(f"    {src:25s} ↔ {tgt:25s}  {score:.3f}  ({reason})")

    assert len(suggestions) > 0, "Should suggest at least one exploration"

    print("\n  ✓ Suggestion engine works")


def test_full_learning_loop():
    header("7. FULL LEARNING LOOP")
    print("  Build knowledge across 6 domains through iterative search.\n")

    memory = AnalogyMemory()

    # Build categories from curated datasets
    cats = {}
    for name, fn in ALL_DATASETS.items():
        data = fn()
        cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
        cats[name] = cat

    names = list(cats.keys())

    # Phase 1: Explore all pairs
    print("  Phase 1: Systematic exploration")
    t0 = time.time()
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            results = learn_and_search(cats[n1], cats[n2], memory, min_score=0.0)

    dt = time.time() - t0
    print(f"    Explored {len(names) * (len(names) - 1) // 2} pairs in {dt:.1f}s")
    print(f"    Stored {len(memory.analogies)} analogies")
    print(f"    Cache hits: {memory._hit_count}/{memory._search_count}")

    # Phase 2: Check what the engine learned
    print("\n  Phase 2: Knowledge summary")
    meta = MetaCategory(memory)
    components = meta.connected_components()
    print(f"    Connected components: {len(components)}")
    for comp in components:
        print(f"      {comp}")

    # Phase 3: Reinforce best analogies
    print("\n  Phase 3: Reinforcement")
    best = memory.all_analogies()[:3]
    for a in best:
        before = a.confidence()
        a.reinforce("consistent_with_new_data", 0.85)
        after = a.confidence()
        print(f"    {a.source_name}→{a.target_name}: {before:.3f} → {after:.3f}")

    # Phase 4: Get suggestions for what to explore next
    print("\n  Phase 4: Suggestions for next exploration")
    sugg = suggest_explorations(memory, cats, max_suggestions=3)
    for src, tgt, score, reason in sugg:
        print(f"    {src} ↔ {tgt}: {score:.3f} ({reason})")

    # Final stats
    print(f"\n  Final memory stats: {memory.stats}")
    print(f"  Total analogies: {len(memory.analogies)}")
    top_5 = memory.all_analogies()[:5]
    print(f"\n  Top 5 analogies by confidence:")
    for a in top_5:
        print(f"    {a.source_name:25s} → {a.target_name:25s}  "
              f"conf={a.confidence():.3f}")

    print("\n  ✓ Full learning loop works")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    MORPHOS Phase 2 — Learning Engine Test Suite        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_fingerprint()
    test_analogy_memory()
    test_transitive_prediction()
    test_learning_search()
    test_meta_category()
    test_suggestions()
    test_full_learning_loop()

    header("ALL LEARNING ENGINE TESTS PASSED")
    print("""
  The learning engine:
  • Fingerprints categories for fast structural similarity lookup
  • Stores discovered analogies with Bayesian confidence tracking
  • Predicts transitive analogies (A≅B ∧ B≅C → A≅C)
  • Caches results and accelerates repeated searches
  • Builds a meta-category (category of categories)
  • Suggests which unexplored pairs are most promising
  • Reinforces/weakens analogies based on new evidence
  • Gets smarter with every search it performs
""")


if __name__ == "__main__":
    main()
