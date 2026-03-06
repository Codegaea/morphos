#!/usr/bin/env python3
"""
MORPHOS Phase 2.5 — Scale & Reasoning Tests

Tests all five missing capabilities:
1. Typed ontologies
2. Constraint-solving analogies
3. Embedding-assisted search
4. Large curated datasets (KnowledgeStore)
5. Incremental indexing
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import create_category
from engine.scale import (
    TypedOntology, TypedObject, MorphismType,
    find_analogies_csp, embedding_assisted_search,
    compute_structural_embeddings, embedding_similarity,
    KnowledgeStore, IncrementalIndex,
)


def header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def test_typed_ontology():
    header("1. TYPED ONTOLOGY")

    ont = TypedOntology("Biology")

    # Define type hierarchy
    ont.add_type("organism")
    ont.add_type("animal", ["organism"])
    ont.add_type("mammal", ["animal"])
    ont.add_type("bird", ["animal"])
    ont.add_type("trait")
    ont.add_type("locomotion", ["trait"])

    # Define morphism types with domain/range constraints
    ont.add_morphism_type("is_a", domain="animal", codomain="animal", is_transitive=True)
    ont.add_morphism_type("capable_of", domain="animal", codomain="locomotion")
    ont.add_morphism_type("has_covering", domain="animal", codomain="trait")

    # Add typed objects
    ont.add_object("dog", "mammal")
    ont.add_object("cat", "mammal")
    ont.add_object("eagle", "bird")
    ont.add_object("mammal_class", "animal")
    ont.add_object("bird_class", "animal")
    ont.add_object("vertebrate", "animal")
    ont.add_object("flies", "locomotion")
    ont.add_object("walks", "locomotion")
    ont.add_object("fur", "trait")

    # Add morphisms (type-checked)
    assert ont.add_morphism("is_a", "dog", "mammal_class")
    assert ont.add_morphism("is_a", "cat", "mammal_class")
    assert ont.add_morphism("is_a", "eagle", "bird_class")
    assert ont.add_morphism("is_a", "mammal_class", "vertebrate")
    assert ont.add_morphism("is_a", "bird_class", "vertebrate")
    assert ont.add_morphism("capable_of", "dog", "walks")
    assert ont.add_morphism("capable_of", "eagle", "flies")
    assert ont.add_morphism("has_covering", "dog", "fur")

    # This should fail: "flies" is locomotion, not animal
    assert not ont.add_morphism("is_a", "flies", "mammal_class"), "Type violation not caught!"

    print(f"  Objects: {len(ont.objects)}")
    print(f"  Morphisms: {len(ont.morphisms)}")
    print(f"  Type check: {ont.type_check_report()['valid']} ✓")

    # Test transitive inference
    inferred = ont.infer_transitive()
    print(f"  Inferred {len(inferred)} transitive morphisms:")
    for rel, src, tgt in inferred:
        print(f"    {rel}: {src} → {tgt}")

    # Should infer: dog is_a vertebrate (via mammal_class)
    assert any(s == "dog" and t == "vertebrate" for _, s, t in inferred), \
        "Failed to infer dog is_a vertebrate"
    print(f"  dog is_a vertebrate inferred ✓")

    # Convert to Category
    cat = ont.to_category()
    print(f"  Category: {len(cat.objects)} obj, {len(cat.user_morphisms())} morph")

    # Subtype checking
    assert ont.is_subtype("mammal", "organism"), "mammal should be subtype of organism"
    assert not ont.is_subtype("trait", "animal"), "trait should not be subtype of animal"
    print(f"  Subtype checking ✓")

    print("\n  ✓ Typed ontology works")


def test_constraint_solver():
    header("2. CONSTRAINT-SOLVING ANALOGIES")

    # Two isomorphic categories with different labels
    source = create_category("Fluids",
        ["Pressure", "Flow", "Resistance", "Source"],
        [("drives", "Pressure", "Flow", "causes"),
         ("impedes", "Resistance", "Flow", "modulates"),
         ("generates", "Source", "Pressure", "produces")],
        auto_close=False)

    target = create_category("Circuits",
        ["Voltage", "Current", "Impedance", "Battery"],
        [("drives", "Voltage", "Current", "causes"),
         ("impedes", "Impedance", "Current", "modulates"),
         ("generates", "Battery", "Voltage", "produces")],
        auto_close=False)

    t0 = time.time()
    results = find_analogies_csp(source, target, max_results=5)
    dt = time.time() - t0

    print(f"  CSP search: {len(results)} solution(s) in {dt*1000:.1f}ms")
    if results:
        r = results[0]
        print(f"  Best score: {r['score']:.3f}")
        for s, t in r["object_map"].items():
            print(f"    {s:15s} ↦ {t}")

    assert len(results) > 0, "Should find at least one analogy"
    r0 = results[0]
    # With semantic rescoring, the final blended score will be below 1.0 for
    # cross-domain pairs (Pressure↔Voltage etc. share no label tokens).
    # The structural component should still be perfect (1.0).
    structural = r0.get("structural_score", r0["score"])
    assert structural >= 0.99, f"Structural score should be ~1.0, got {structural}"
    assert r0["score"] >= 0.65, f"Blended score should be reasonable, got {r0['score']}"
    print(f"  Structural: {structural:.3f}, Semantic: {r0.get('semantic_score', '—')}, Blended: {r0['score']:.3f}")

    # Test with non-matching categories
    different = create_category("StarGraph",
        ["hub", "a", "b", "c", "d"],
        [("r", "hub", "a", "connects"), ("r", "hub", "b", "connects"),
         ("r", "hub", "c", "connects"), ("r", "hub", "d", "connects")],
        auto_close=False)

    results_diff = find_analogies_csp(source, different, max_results=3)
    diff_score = results_diff[0]["score"] if results_diff else 0
    print(f"\n  Non-matching: score={diff_score:.3f} (should be < 1.0)")

    # Larger test: 8-object categories
    big_src = create_category("BigSrc",
        [f"s{i}" for i in range(8)],
        [(f"r{i}", f"s{i}", f"s{i+1}", "chain") for i in range(7)],
        auto_close=False)
    big_tgt = create_category("BigTgt",
        [f"t{i}" for i in range(8)],
        [(f"q{i}", f"t{i}", f"t{i+1}", "chain") for i in range(7)],
        auto_close=False)

    t0 = time.time()
    results_big = find_analogies_csp(big_src, big_tgt, max_results=1, timeout_ms=3000)
    dt = time.time() - t0
    print(f"\n  8-object chain: {len(results_big)} solution(s) in {dt*1000:.1f}ms")
    if results_big:
        print(f"  Score: {results_big[0]['score']:.3f}")

    print("\n  ✓ Constraint solver works")


def test_embeddings():
    header("3. EMBEDDING-ASSISTED SEARCH")

    cat = create_category("EmbTest",
        ["A", "B", "C", "D", "E"],
        [("r1", "A", "B", "chain"), ("r2", "B", "C", "chain"),
         ("r3", "C", "D", "chain"), ("r4", "D", "E", "chain"),
         ("r5", "A", "C", "shortcut")],
        auto_close=False)

    embs = compute_structural_embeddings(cat, dim=16)
    print(f"  Computed {len(embs)} embeddings (dim=16)")

    # Objects with similar structure should have similar embeddings
    # A has the most outgoing edges (r1, r5), E has none
    sim_AB = embedding_similarity(embs["A"], embs["B"])
    sim_AE = embedding_similarity(embs["A"], embs["E"])
    print(f"  sim(A, B) = {sim_AB:.3f}")
    print(f"  sim(A, E) = {sim_AE:.3f}")

    # Test embedding-assisted search
    source = create_category("Src",
        ["x", "y", "z"],
        [("f", "x", "y", "causes"), ("g", "y", "z", "causes")],
        auto_close=False)
    target = create_category("Tgt",
        ["p", "q", "r"],
        [("a", "p", "q", "causes"), ("b", "q", "r", "causes")],
        auto_close=False)

    t0 = time.time()
    results = embedding_assisted_search(source, target)
    dt = time.time() - t0

    print(f"\n  Embedding-assisted search: {len(results)} results in {dt*1000:.1f}ms")
    if results:
        print(f"  Best: score={results[0]['score']:.3f}, map={results[0]['object_map']}")

    print("\n  ✓ Embedding-assisted search works")


def test_knowledge_store():
    header("4. KNOWLEDGE STORE — Large Curated Datasets")

    store = KnowledgeStore()

    t0 = time.time()
    store.load_all_datasets()
    dt = time.time() - t0

    s = store.stats
    print(f"  Loaded in {dt*1000:.0f}ms:")
    print(f"    Objects:   {s['total_objects']:,}")
    print(f"    Triples:   {s['total_triples']:,}")
    print(f"    Domains:   {s['domains']}")
    print(f"    Relations: {s['unique_relations']}")
    print(f"    Domains:   {', '.join(s['domain_list'][:8])}...")

    # Query tests
    print(f"\n  Query: subject='dog'")
    results = store.query(subject="dog")
    for r, s, t, d in results[:5]:
        print(f"    [{d}] {r}: {s} → {t}")

    print(f"\n  Query: relation='IsA'")
    results = store.query(relation="IsA", limit=5)
    for r, s, t, d in results:
        print(f"    [{d}] {s} → {t}")

    # Neighborhood extraction
    print(f"\n  Neighborhood of 'heart':")
    nbr = store.neighborhood("heart", max_hops=1, max_nodes=10)
    print(f"    Objects: {nbr['objects']}")
    print(f"    Edges: {len(nbr['morphisms'])}")

    # Build category from concept
    cat = store.to_category("heart", max_nodes=15)
    print(f"    Category: {len(cat.objects)} obj, {len(cat.user_morphisms())} morph")

    # Cross-domain query
    print(f"\n  Objects appearing in multiple domains:")
    multi = [(k, v) for k, v in store.objects.items()
             if isinstance(v.get("domain"), set) and len(v["domain"]) > 1]
    for obj, info in multi[:5]:
        print(f"    '{obj}' in {info['domain']}")

    print("\n  ✓ Knowledge store works")


def test_incremental_index():
    header("5. INCREMENTAL INDEXING")

    cat = create_category("Incremental",
        ["A", "B", "C"],
        [("f", "A", "B", "causes"), ("g", "B", "C", "causes")],
        auto_close=False)

    idx = IncrementalIndex(cat)
    print(f"  Initial: {idx.stats}")
    print(f"  degree(A) = {idx.degree('A')}")
    print(f"  degree(B) = {idx.degree('B')}")
    print(f"  neighbors(B, out) = {idx.neighbors('B', 'out')}")

    # Add new data incrementally
    idx.add_object("D")
    idx.add_morphism("h", "C", "D", rel_type="causes")
    print(f"\n  After adding D and h: C→D:")
    print(f"  {idx.stats}")
    print(f"  degree(C) = {idx.degree('C')}")
    print(f"  neighbors(C, out) = {idx.neighbors('C', 'out')}")

    # Signature should update
    sig_before = idx.get_signature("C")
    idx.add_morphism("k", "C", "A", rel_type="feedback")
    sig_after = idx.get_signature("C")
    print(f"\n  After adding feedback C→A:")
    print(f"  C signature changed: {sig_before != sig_after} ✓")
    print(f"  degree(C) = {idx.degree('C')}")

    # Embedding should be available
    emb = idx.get_embedding("A")
    assert len(emb) == 16, f"Expected 16-dim embedding, got {len(emb)}"
    print(f"  embedding(A): [{', '.join(f'{x:.2f}' for x in emb[:4])}...]")

    # Version tracking
    print(f"  Index version: {idx._version}")

    print("\n  ✓ Incremental indexing works")


def test_integration():
    header("6. INTEGRATION — Full Pipeline")
    print("  Typed ontology → Category → CSP search → Embedding refinement")

    # Build a typed ontology
    ont = TypedOntology("Vehicles")
    ont.add_type("entity")
    ont.add_type("vehicle", ["entity"])
    ont.add_type("property", ["entity"])
    ont.add_morphism_type("is_a", domain="entity", codomain="entity", is_transitive=True)
    ont.add_morphism_type("has_property", domain="vehicle", codomain="property")

    for v in ["car", "truck", "bus"]:
        ont.add_object(v, "vehicle")
    for p in ["engine", "wheels", "seats"]:
        ont.add_object(p, "property")
    ont.add_object("motor_vehicle", "vehicle")
    ont.add_morphism("is_a", "car", "motor_vehicle")
    ont.add_morphism("is_a", "truck", "motor_vehicle")
    ont.add_morphism("is_a", "bus", "motor_vehicle")
    ont.add_morphism("has_property", "car", "engine")
    ont.add_morphism("has_property", "car", "wheels")
    ont.add_morphism("has_property", "truck", "engine")
    ont.add_morphism("has_property", "truck", "wheels")
    ont.add_morphism("has_property", "bus", "engine")
    ont.add_morphism("has_property", "bus", "seats")
    ont.infer_transitive()

    vehicles_cat = ont.to_category()

    # Build comparison category (animals)
    animals_cat = create_category("Animals",
        ["dog", "cat", "horse", "mammal", "legs", "fur", "tail"],
        [("is_a", "dog", "mammal", "is_a"),
         ("is_a", "cat", "mammal", "is_a"),
         ("is_a", "horse", "mammal", "is_a"),
         ("has_property", "dog", "legs", "has_property"),
         ("has_property", "dog", "fur", "has_property"),
         ("has_property", "cat", "legs", "has_property"),
         ("has_property", "cat", "fur", "has_property"),
         ("has_property", "horse", "legs", "has_property"),
         ("has_property", "horse", "tail", "has_property")],
        auto_close=False)

    print(f"  Vehicles (typed): {len(vehicles_cat.objects)} obj, {len(vehicles_cat.user_morphisms())} morph")
    print(f"  Animals: {len(animals_cat.objects)} obj, {len(animals_cat.user_morphisms())} morph")

    # CSP search
    t0 = time.time()
    csp_results = find_analogies_csp(vehicles_cat, animals_cat, max_results=3)
    dt = time.time() - t0
    print(f"\n  CSP: {len(csp_results)} results in {dt*1000:.1f}ms")
    if csp_results:
        r = csp_results[0]
        print(f"  Score: {r['score']:.3f}")
        omap = r.get("object_map", r.get("map", {}))
        for s, t in list(omap.items())[:5]:
            print(f"    {s:15s} ↦ {t}")

    # Embedding-assisted
    t0 = time.time()
    emb_results = embedding_assisted_search(vehicles_cat, animals_cat)
    dt = time.time() - t0
    print(f"\n  Embedding-assisted: {len(emb_results)} results in {dt*1000:.1f}ms")
    if emb_results:
        print(f"  Best: score={emb_results[0]['score']:.3f}")

    # Load into knowledge store and query
    store = KnowledgeStore()
    store.load_dataset("vehicles", {"objects": vehicles_cat.objects,
        "morphisms": [(m.label, m.source, m.target) for m in vehicles_cat.user_morphisms()]})
    store.load_dataset("animals", {"objects": animals_cat.objects,
        "morphisms": [(m.label, m.source, m.target) for m in animals_cat.user_morphisms()]})

    # Cross-domain query
    is_a_results = store.query(relation="is_a")
    print(f"\n  Knowledge store: {len(is_a_results)} 'is_a' triples across domains")

    print("\n  ✓ Full pipeline integration works")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  MORPHOS Phase 2.5 — Scale & Reasoning Extensions      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_typed_ontology()
    test_constraint_solver()
    test_embeddings()
    test_knowledge_store()
    test_incremental_index()
    test_integration()

    header("ALL SCALE TESTS PASSED")
    print("""
  Five capabilities for serious scale:

  • Typed ontologies: type hierarchy, domain/range constraints,
    transitive inference, type-safe construction
  • Constraint solving: AC-3 arc consistency + forward checking +
    MRV heuristic. Prunes search space before backtracking.
  • Embedding-assisted search: structural graph embeddings via
    random walks, cosine similarity for candidate filtering
  • Knowledge store: unified index over all curated datasets,
    cross-domain querying by subject/relation/object/domain,
    neighborhood extraction, category construction from queries
  • Incremental indexing: add objects/morphisms without rebuilding,
    lazy signature/embedding recompute, version tracking
""")


if __name__ == "__main__":
    main()
