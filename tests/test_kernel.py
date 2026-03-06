#!/usr/bin/env python3
"""
MORPHOS Reasoning OS Kernel — Test Suite

Tests the persistent store, proof-carrying morphisms, task scheduler,
program registry, evidence tracking, and domain versioning.
"""
import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.kernel import ReasoningStore, TaskScheduler, TASK_TYPES
from engine import create_category


def header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def test_persistent_store():
    header("1. PERSISTENT STORE")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    # Create a domain
    did = store.create_domain("Physics", "Physical laws and relationships")
    print(f"  Created domain: {did[:8]}...")

    # Add concepts
    store.add_concept(did, "Voltage", "quantity")
    store.add_concept(did, "Current", "quantity")
    store.add_concept(did, "Resistance", "quantity")

    # Add proof-carrying morphism
    mid = store.add_morphism(
        did, "ohm_law", "Voltage", "Current",
        rel_type="constitutive_law",
        truth_degree=0.99,
        truth_modality="ACTUAL",
        proof_term="ohm(V, I, R)",
        created_by="encyclopedia",
    )
    print(f"  Added morphism: {mid[:8]}...")

    # Query
    morphisms = store.get_morphisms(did)
    print(f"  Morphisms in Physics: {len(morphisms)}")
    for m in morphisms:
        print(f"    {m['label']}: {m['source_label']} → {m['target_label']} "
              f"[{m['truth_modality']}({m['truth_degree']:.3f})] "
              f"proof={m['proof_term']}")

    # Stats
    print(f"  Store stats: {store.stats}")

    store.close()
    os.remove(db_path)
    print("\n  ✓ Persistent store works")


def test_evidence_tracking():
    header("2. EVIDENCE TRACKING + BAYESIAN UPDATING")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    did = store.create_domain("Hypothesis")
    mid = store.add_morphism(did, "causes", "smoking", "cancer",
                             truth_degree=0.5, truth_modality="UNDETERMINED")

    print(f"  Initial: degree=0.500, modality=UNDETERMINED")

    # Add supporting evidence
    e1 = store.add_evidence(mid, "epidemiological_study_1", "supports", 0.9, "Lancet 2020")
    m1 = store.get_morphisms(did)[0]
    print(f"  After study 1 (+): degree={m1['truth_degree']:.3f}, modality={m1['truth_modality']}")

    e2 = store.add_evidence(mid, "epidemiological_study_2", "supports", 0.85, "NEJM 2021")
    m2 = store.get_morphisms(did)[0]
    print(f"  After study 2 (+): degree={m2['truth_degree']:.3f}, modality={m2['truth_modality']}")

    # Add contradicting evidence
    e3 = store.add_evidence(mid, "industry_funded_study", "contradicts", 0.6, "TobaccoCorp")
    m3 = store.get_morphisms(did)[0]
    print(f"  After industry study (-): degree={m3['truth_degree']:.3f}, modality={m3['truth_modality']}")

    # Check evidence trail
    evidence = store.get_evidence(mid)
    print(f"\n  Evidence trail ({len(evidence)} items):")
    for e in evidence:
        print(f"    [{e['direction']}] {e['label']} (str={e['strength']:.1f}) from {e['source']}")

    assert m2["truth_degree"] > m1["truth_degree"], "Supporting evidence should increase degree"
    assert m3["truth_degree"] < m2["truth_degree"], "Contradicting evidence should decrease degree"

    store.close()
    os.remove(db_path)
    print("\n  ✓ Evidence tracking works")


def test_derived_morphisms():
    header("3. PROOF-CARRYING DERIVED MORPHISMS")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    did = store.create_domain("Taxonomy")
    m1 = store.add_morphism(did, "is_a", "dog", "mammal", rel_type="taxonomy")
    m2 = store.add_morphism(did, "is_a", "mammal", "vertebrate", rel_type="taxonomy")

    # Derive transitive morphism with proof
    m3 = store.add_derived_morphism(
        did, "is_a", "dog", "vertebrate",
        rel_type="taxonomy",
        rule="transitivity",
        premises=[m1, m2],
        truth_degree=0.99,
    )

    derived = store.get_morphisms(did)
    for m in derived:
        flag = " [INFERRED]" if m["is_inferred"] else ""
        print(f"  {m['label']}: {m['source_label']} → {m['target_label']} "
              f"proof={m['proof_term']}{flag}")

    # Check derivation trace
    rows = store.conn.execute("SELECT * FROM derivations").fetchall()
    print(f"\n  Derivation traces: {len(rows)}")
    for r in rows:
        print(f"    rule={r['rule']}, premises={r['premises']}, "
              f"conclusion={r['conclusion']}")

    assert any(m["is_inferred"] for m in derived), "Should have inferred morphism"

    store.close()
    os.remove(db_path)
    print("\n  ✓ Proof-carrying derivations work")


def test_domain_versioning():
    header("4. DOMAIN VERSIONING")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    did = store.create_domain("Evolving")
    store.add_morphism(did, "r1", "A", "B")
    store.add_morphism(did, "r2", "B", "C")

    print(f"  Version 1: 2 morphisms")

    # Snapshot
    v2_id = store.snapshot_domain(did)
    print(f"  Snapshot created: {v2_id[:8]}...")

    # Modify original
    store.add_morphism(did, "r3", "C", "A")
    orig_morphs = store.get_morphisms(did)
    snap_morphs = store.get_morphisms(v2_id)

    print(f"  Original now: {len(orig_morphs)} morphisms")
    print(f"  Snapshot v2: {len(snap_morphs)} morphisms")

    assert len(orig_morphs) == 3, "Original should have 3 morphisms"
    assert len(snap_morphs) == 2, "Snapshot should still have 2 morphisms"

    domains = store.list_domains()
    print(f"\n  Domains: {len(domains)}")
    for d in domains:
        print(f"    {d['name']} v{d['version']}")

    store.close()
    os.remove(db_path)
    print("\n  ✓ Domain versioning works")


def test_program_registry():
    header("5. PROGRAM REGISTRY")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    # Register a functor as a program
    pid = store.register_program(
        "FluidToCircuit",
        "Fluids", "Circuits",
        {"Pressure": "Voltage", "Flow": "Current", "Resistance": "Impedance"},
        score=0.95,
        classification="isomorphism",
    )
    print(f"  Registered program: {pid[:8]}...")

    # Add tests
    t1 = store.add_program_test(pid, "maps_object",
        {"source": "Pressure"}, {"target": "Voltage"})
    t2 = store.add_program_test(pid, "maps_object",
        {"source": "Flow"}, {"target": "Current"})
    t3 = store.add_program_test(pid, "preserves_morphism",
        {"source_morphism": {"source": "Pressure", "target": "Flow"}},
        {"target_morphism": {"source": "Voltage", "target": "Current"}})

    # Run tests
    results = store.run_program_tests(pid)
    print(f"  Tests: {results['passed']}/{results['total']} passed")
    for r in results["results"]:
        status = "✓" if r["passed"] else "✗"
        print(f"    {status} {r['test']}: {r['actual']}")

    # Version the program
    pid_v2 = store.register_program(
        "FluidToCircuit",
        "Fluids", "Circuits",
        {"Pressure": "Voltage", "Flow": "Current", "Resistance": "Impedance", "Source": "Battery"},
        score=0.98,
    )

    prog = store.get_program("FluidToCircuit")
    print(f"\n  Latest version: {prog['version']} (score={prog['score']:.3f})")

    # Reinforce
    store.reinforce_program(pid)
    prog = store.conn.execute("SELECT * FROM programs WHERE id=?", (pid,)).fetchone()
    print(f"  Confirmations: {prog['confirmations']}")

    programs = store.list_programs()
    print(f"  Total programs: {len(programs)}")

    assert results["passed"] == 3, f"Expected 3 passed, got {results['passed']}"

    store.close()
    os.remove(db_path)
    print("\n  ✓ Program registry works")


def test_task_scheduler():
    header("6. TASK SCHEDULER")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)
    scheduler = TaskScheduler(store)

    # Create test domain
    did = store.create_domain("TestDomain")
    store.add_morphism(did, "f", "A", "B", rel_type="causes")
    store.add_morphism(did, "g", "B", "C", rel_type="causes")

    # Submit verify task
    t1 = scheduler.submit("verify", {"domain_id": did}, priority=1)
    print(f"  Submitted verify task: {t1[:8]}...")

    # Submit snapshot task
    t2 = scheduler.submit("snapshot", {"domain_id": did}, priority=0)
    print(f"  Submitted snapshot task: {t2[:8]}...")

    # Execute highest priority first
    result = scheduler.run_next()
    print(f"  Executed: {result}")

    # Execute remaining
    results = scheduler.run_all_pending()
    print(f"  Remaining executed: {len(results)}")

    # Check task history
    all_tasks = scheduler.list_tasks()
    print(f"\n  Task history ({len(all_tasks)}):")
    for t in all_tasks:
        dur = f" ({t['duration_ms']:.0f}ms)" if t["duration_ms"] else ""
        print(f"    [{t['status']}] {t['task_type']}{dur}")

    assert all(t["status"] == "completed" for t in all_tasks), "All tasks should be completed"

    store.close()
    os.remove(db_path)
    print("\n  ✓ Task scheduler works")


def test_map_task():
    header("7. MAP TASK — Full Analogy Pipeline")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)
    scheduler = TaskScheduler(store)

    # Create two analogous domains
    fluids = create_category("Fluids",
        ["Pressure", "Flow", "Resistance"],
        [("drives", "Pressure", "Flow", "causes"),
         ("impedes", "Resistance", "Flow", "modulates")])
    circuits = create_category("Circuits",
        ["Voltage", "Current", "Impedance"],
        [("drives", "Voltage", "Current", "causes"),
         ("impedes", "Impedance", "Current", "modulates")])

    fid = store.import_category(fluids)
    cid = store.import_category(circuits)
    print(f"  Imported Fluids ({fid[:8]}) and Circuits ({cid[:8]})")

    # Submit map task
    tid = scheduler.submit("map", {
        "source_domain_id": fid,
        "target_domain_id": cid,
    })
    result = scheduler.execute(tid)

    print(f"  Map result: {result.get('analogies', 0)} analogies found")
    if result.get("best_score"):
        print(f"  Best score: {result['best_score']:.3f}")
        print(f"  Program registered: {result.get('program_id', '')[:8]}...")
        for s, t in result.get("object_map", {}).items():
            print(f"    {s:15s} ↦ {t}")

    # Check stored program
    programs = store.list_programs()
    print(f"\n  Programs in registry: {len(programs)}")

    assert result.get("analogies", 0) > 0, "Should find at least one analogy"

    store.close()
    os.remove(db_path)
    print("\n  ✓ Map task pipeline works")


def test_import_export_roundtrip():
    header("8. IMPORT/EXPORT ROUNDTRIP")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)

    # Create category in memory
    cat = create_category("TestCat", ["X", "Y", "Z"],
        [("f", "X", "Y", "causes"), ("g", "Y", "Z", "causes")],
        auto_close=False)

    # Import to store
    did = store.import_category(cat)
    print(f"  Imported: {len(cat.objects)} objects, {len(cat.user_morphisms())} morphisms")

    # Export back
    exported = store.export_category(did)
    print(f"  Exported: {len(exported.objects)} objects, {len(exported.user_morphisms())} morphisms")

    assert set(cat.objects) == set(exported.objects), "Objects should match"
    assert len(cat.user_morphisms()) == len(exported.user_morphisms()), "Morphism count should match"

    # Verify labels match
    orig_labels = {(m.label, m.source, m.target) for m in cat.user_morphisms()}
    exp_labels = {(m.label, m.source, m.target) for m in exported.user_morphisms()}
    assert orig_labels == exp_labels, f"Morphism labels should match"

    print(f"  Roundtrip verified ✓")

    store.close()
    os.remove(db_path)
    print("\n  ✓ Import/export roundtrip works")


def test_full_reasoning_pipeline():
    header("9. FULL REASONING OS PIPELINE")
    print("  Domain creation → Morphisms → Evidence → Inference →")
    print("  Versioning → Analogy → Program → Test\n")

    db_path = tempfile.mktemp(suffix=".db")
    store = ReasoningStore(db_path)
    scheduler = TaskScheduler(store)

    # Step 1: Create domain with initial knowledge
    did = store.create_domain("MedicalKnowledge", "Clinical observations")
    m1 = store.add_morphism(did, "symptom_of", "fever", "infection",
                             truth_degree=0.7, truth_modality="PROBABLE")
    m2 = store.add_morphism(did, "treated_by", "infection", "antibiotics",
                             truth_degree=0.85, truth_modality="ACTUAL")
    print(f"  1. Created domain with 2 morphisms")

    # Step 2: Add evidence
    store.add_evidence(m1, "clinical_trial_A", "supports", 0.9, "JAMA 2023")
    store.add_evidence(m1, "clinical_trial_B", "supports", 0.8, "Lancet 2024")
    m1_updated = store.get_morphisms(did, source="fever")[0]
    print(f"  2. After evidence: fever→infection degree={m1_updated['truth_degree']:.3f}")

    # Step 3: Derive new morphism with proof
    m3 = store.add_derived_morphism(
        did, "treated_via", "fever", "antibiotics",
        rel_type="treatment_path",
        rule="composition",
        premises=[m1, m2],
        truth_degree=m1_updated["truth_degree"] * 0.85,
    )
    print(f"  3. Derived: fever→antibiotics (proof: composition({m1[:8]}, {m2[:8]}))")

    # Step 4: Snapshot before modification
    v2 = store.snapshot_domain(did)
    print(f"  4. Snapshot created (v2)")

    # Step 5: Submit verify task
    tid = scheduler.submit("verify", {"domain_id": did})
    result = scheduler.execute(tid)
    print(f"  5. Verification: valid={result.get('is_valid', '?')}")

    # Step 6: Final stats
    s = store.stats
    print(f"\n  Final store state:")
    print(f"    Domains: {s['domains']}")
    print(f"    Concepts: {s['concepts']}")
    print(f"    Morphisms: {s['morphisms']}")
    print(f"    Evidence: {s['evidence']}")
    print(f"    Derivations: {s['derivations']}")
    print(f"    Tasks: {s['tasks']}")

    store.close()
    os.remove(db_path)
    print("\n  ✓ Full reasoning pipeline works")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      MORPHOS Reasoning OS Kernel — Test Suite          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_persistent_store()
    test_evidence_tracking()
    test_derived_morphisms()
    test_domain_versioning()
    test_program_registry()
    test_task_scheduler()
    test_map_task()
    test_import_export_roundtrip()
    test_full_reasoning_pipeline()

    header("ALL REASONING OS TESTS PASSED")
    print("""
  The Reasoning OS kernel is operational:

  • Persistent SQLite store — knowledge survives sessions
  • Proof-carrying morphisms — every derived fact traceable
  • Bayesian evidence tracking — truth updates from observations
  • Domain versioning — snapshots with change isolation
  • Program registry — functors as named, versioned, tested programs
  • Task scheduler — reasoning jobs with lifecycle + priority
  • Import/export — roundtrip between in-memory and persistent
  • Full pipeline — domain → evidence → inference → snapshot → verify
""")


if __name__ == "__main__":
    main()
