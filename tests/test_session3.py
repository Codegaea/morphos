"""
Session 3 Tests: Pipeline, Belief Revision, DSL Extensions, Explain API

Tests cover:
1. Belief propagation through derivation chains
2. explain_morphism / explain_path  
3. New task handlers: compose, infer, speculate
4. Pipeline workflow (all 7 steps)
5. Query language new parsers
"""
import pytest
import json
import tempfile
import os

from engine.kernel import ReasoningStore, TaskScheduler
from engine.categories import create_category
from engine.topos import TruthValue, Modality, compose_truth
from engine.query_lang import compile_query


# ── Fixtures ──────────────────────────────────────────

def _make_store():
    return ReasoningStore(":memory:")


def _linear_chain(store, n=4):
    """Import a linear chain: a→b→c→d with isa rel_type."""
    labels = [chr(ord('a') + i) for i in range(n)]
    morphs = [(f"r{i}", labels[i], labels[i+1], "isa") for i in range(n-1)]
    cat = create_category("Chain", labels, morphs, auto_close=False)
    did = store.import_category(cat, domain_name="Chain")
    return did


# ── 1. Belief Propagation ─────────────────────────────

def test_belief_propagation_updates_derived():
    """Evidence on a premise morphism propagates to derived morphisms via dependency index."""
    store = _make_store()
    did = store.create_domain("Test")
    m1_id = store.add_morphism(did, "r1", "a", "b", "isa",
                               truth_degree=0.9, truth_modality="PROBABLE")
    m2_id = store.add_morphism(did, "r2", "b", "c", "isa",
                               truth_degree=0.85, truth_modality="PROBABLE")
    # Use add_derived_morphism to populate dependency index
    t1 = TruthValue(0.9, Modality["PROBABLE"])
    t2 = TruthValue(0.85, Modality["PROBABLE"])
    td = compose_truth(t1, t2)
    xz_id = store.add_derived_morphism(
        did, "r1∘r2", "a", "c", "isa", "transitivity", [m1_id, m2_id],
        truth_degree=td.degree, truth_modality=td.modality.name)

    before_xz = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (xz_id,)).fetchone()["truth_degree"]

    store.add_evidence(m1_id, "observation_contradicts", "contradicts", 0.9, "lab")

    after_m1 = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (m1_id,)).fetchone()
    assert after_m1["truth_degree"] < 0.9, f"Expected a→b to decrease, got {after_m1['truth_degree']}"

    after_xz = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (xz_id,)).fetchone()["truth_degree"]
    assert after_xz < before_xz, f"Expected derived a→c to decrease from {before_xz}, got {after_xz}"


def test_belief_propagation_supporting_evidence():
    """Supporting evidence propagates forward through dependency index."""
    store = _make_store()
    did = store.create_domain("Test")
    m1_id = store.add_morphism(did, "r1", "x", "y", "isa",
                               truth_degree=0.5, truth_modality="PROBABLE")
    m2_id = store.add_morphism(did, "r2", "y", "z", "isa",
                               truth_degree=0.5, truth_modality="PROBABLE")
    t = compose_truth(TruthValue(0.5, Modality["PROBABLE"]), TruthValue(0.5, Modality["PROBABLE"]))
    xz_id = store.add_derived_morphism(
        did, "r1∘r2", "x", "z", "isa", "transitivity", [m1_id, m2_id],
        truth_degree=t.degree, truth_modality=t.modality.name)

    before = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (xz_id,)).fetchone()["truth_degree"]
    store.add_evidence(m1_id, "strong_support", "supports", 0.9, "experiment")
    after = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (xz_id,)).fetchone()["truth_degree"]
    assert after > before, f"Expected derived x→z to increase, got {after} from {before}"


# ── 2. Explain API ────────────────────────────────────

def test_explain_morphism_axiom():
    """explain_morphism on a user morphism returns an axiom node."""
    store = _make_store()
    did = _linear_chain(store)
    morphs = store.get_morphisms(did)
    assert morphs, "Expected morphisms in chain"
    node = store.explain_morphism(morphs[0]["id"])
    assert "id" in node
    assert "label" in node
    assert "truth" in node
    assert node["is_inferred"] is False
    assert node["premises"] == []


def test_explain_morphism_inferred():
    """explain_morphism on an inferred morphism returns a rule and premises."""
    store = _make_store()
    sched = TaskScheduler(store)
    did = _linear_chain(store, n=3)  # a→b→c

    tid = sched.submit("infer", {"domain_name": "Chain", "rule": "transitivity"})
    r = sched.execute(tid)
    assert r.get("new_inferences", 0) > 0, "Expected at least 1 transitivity inference"

    morphs = store.get_morphisms(did)
    inferred = [m for m in morphs if m["is_inferred"]]
    assert inferred, "Expected at least one inferred morphism"

    node = store.explain_morphism(inferred[0]["id"])
    assert node["is_inferred"] is True
    assert node.get("rule") == "transitivity"
    assert len(node["premises"]) == 2, f"Expected 2 premises, got {node['premises']}"


def test_explain_path():
    """explain_path returns explanation nodes for morphisms on a path."""
    store = _make_store()
    did = _linear_chain(store, n=3)
    nodes = store.explain_path("a", "b", did)
    assert len(nodes) >= 1
    assert nodes[0]["source"] == "a"
    assert nodes[0]["target"] == "b"


def test_explain_missing_morphism():
    """explain_morphism returns error dict for unknown IDs."""
    store = _make_store()
    node = store.explain_morphism("nonexistent-id-xyz")
    assert "error" in node


# ── 3. New Task Handlers ──────────────────────────────

def test_compose_task():
    """compose task auto-generates compositions and persists them."""
    from engine.datasets import ALL_DATASETS
    store = _make_store()
    sched = TaskScheduler(store)
    data = ALL_DATASETS["process_chains"]()
    cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
    store.import_category(cat, domain_name="process_chains")

    tid = sched.submit("compose", {"domain_name": "process_chains"})
    result = sched.execute(tid)
    assert "new_compositions" in result
    assert "stored_to_kernel" in result
    assert result["new_compositions"] > 0


def test_infer_task_with_ids_in_derivations():
    """infer task stores morphism IDs in derivation premises for belief propagation."""
    store = _make_store()
    sched = TaskScheduler(store)
    did = _linear_chain(store, n=3)  # a→b→c

    tid = sched.submit("infer", {"domain_name": "Chain", "rule": "transitivity"})
    result = sched.execute(tid)
    assert result.get("new_inferences", 0) >= 1

    # Check that derivation records use morphism IDs (UUIDs), not labels
    derivations = store.conn.execute("SELECT premises FROM derivations").fetchall()
    assert derivations, "Expected derivation records"
    for d in derivations:
        premises = json.loads(d["premises"])
        assert len(premises) >= 1, "Expected at least 1 premise"
        # Each premise should be a UUID-format string
        for p in premises:
            assert len(p) >= 20, f"Premise '{p}' looks like a label, not a UUID"


def test_speculate_task():
    """speculate task returns a report."""
    from engine.datasets import ALL_DATASETS
    store = _make_store()
    sched = TaskScheduler(store)
    data = ALL_DATASETS["mathematical_structures"]()
    cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
    store.import_category(cat, domain_name="mathematical_structures")

    tid = sched.submit("speculate", {"domain_name": "mathematical_structures"})
    result = sched.execute(tid)
    assert "speculated" in result
    assert "report" in result


def test_infer_task_belief_propagation_chain():
    """Belief propagation works through transitivity-inferred morphisms."""
    store = _make_store()
    sched = TaskScheduler(store)

    # Create domain with sub-1.0 truths
    did = store.create_domain("BelTest")
    m1 = store.add_morphism(did, "r1", "a", "b", "isa", truth_degree=0.9, truth_modality="PROBABLE")
    m2 = store.add_morphism(did, "r2", "b", "c", "isa", truth_degree=0.85, truth_modality="PROBABLE")

    tid = sched.submit("infer", {"domain_name": "BelTest", "rule": "transitivity"})
    r = sched.execute(tid)
    assert r["new_inferences"] == 1

    morphs = store.get_morphisms(did)
    derived = next((m for m in morphs if m["is_inferred"]), None)
    assert derived is not None
    before = derived["truth_degree"]

    # Weaken a→b; derived a→c should update
    store.add_evidence(m1, "test_contradiction", "contradicts", 0.9, "test")

    after = store.conn.execute(
        "SELECT truth_degree FROM morphisms WHERE id=?", (derived["id"],)).fetchone()["truth_degree"]
    assert after < before, f"Expected derived a→c to weaken from {before}, got {after}"


# ── 4. Pipeline Workflow ──────────────────────────────

def test_pipeline_e2e():
    """Full pipeline: import → compose → search → store program → inspect."""
    from engine.datasets import ALL_DATASETS
    from engine.scale import find_analogies_csp, KnowledgeStore, embedding_assisted_search
    from engine.speculation import speculate_morphisms, speculation_report
    import time

    store = _make_store()
    sched = TaskScheduler(store)
    knowledge_store = KnowledgeStore()

    for name in ["process_chains", "mathematical_structures"]:
        data = ALL_DATASETS[name]()
        cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
        store.import_category(cat, domain_name=name)

    # Steps 1-2: domain checks
    src = store.get_domain("process_chains")
    tgt = store.get_domain("mathematical_structures")
    assert src and tgt

    # Step 3: compose
    tid = sched.submit("compose", {"domain_name": "process_chains"})
    cr = sched.execute(tid)
    assert cr.get("new_compositions", 0) > 0

    # Step 4: search
    sc = store.export_category(src["id"])
    tc = store.export_category(tgt["id"])
    results = find_analogies_csp(sc, tc, max_results=3)
    assert len(results) > 0

    # Step 5: register program
    best = results[0]
    pid = store.register_program("proc→math", "process_chains", "mathematical_structures",
                                  best["object_map"], score=best["score"])
    assert pid

    # Step 6: test program
    test_r = store.run_program_tests(pid)
    assert "passed" in test_r

    # Step 7: derivation inspection
    all_m = store.get_morphisms(src["id"]) + store.get_morphisms(tgt["id"])
    inferred = [m for m in all_m if m["is_inferred"]]
    assert len(inferred) > 0  # auto-compose produced inferred morphisms


# ── 5. Query Language DSL ─────────────────────────────

def test_qls_new_parsers():
    """All new DSL parsers produce correct action/params."""
    cases = [
        ("explain abc-123", "explain", {"morphism_id": "abc-123"}),
        ("explain path x → y in grammar", "explain_path", {"source": "x", "target": "y", "domain": "grammar"}),
        ("compose grammar", "compose", {"domain": "grammar"}),
        ("infer grammar", "infer", {"domain": "grammar", "rule": "transitivity"}),
        ("infer grammar rule=transitivity", "infer", {"domain": "grammar", "rule": "transitivity"}),
        ("pipeline music math", "pipeline", {"source": "musical_theory", "target": "mathematical_structures"}),
        ("pipeline music → math", "pipeline", {"source": "musical_theory", "target": "mathematical_structures"}),
        ("save program mp music math", "save_program",
         {"name": "mp", "source": "musical_theory", "target": "mathematical_structures"}),
        ("test program myprogram", "test_program", {"program_name": "myprogram"}),
        ("reinforce program myprogram", "reinforce_program", {"program_name": "myprogram"}),
        ("memory", "memory", {}),
        ("beliefs", "memory", {}),
    ]
    for query, expected_action, expected_params in cases:
        cmd = compile_query(query)
        assert cmd.action == expected_action, f"'{query}': expected action={expected_action!r}, got {cmd.action!r}"
        for k, v in expected_params.items():
            assert cmd.params.get(k) == v, f"'{query}': expected params[{k!r}]={v!r}, got {cmd.params.get(k)!r}"


def test_qls_to_task_new_types():
    """New DSL actions correctly produce kernel task dicts."""
    task_cases = [
        ("compose grammar", "compose"),
        ("infer grammar", "infer"),
        ("pipeline music math", "pipeline"),
    ]
    for query, expected_task_type in task_cases:
        cmd = compile_query(query)
        task = cmd.to_task()
        assert task is not None, f"'{query}' should produce a task"
        assert task["task_type"] == expected_task_type, \
            f"'{query}': expected task_type={expected_task_type!r}, got {task['task_type']!r}"


def test_qls_old_parsers_still_work():
    """Existing parsers remain intact after additions."""
    cases = [
        ("search music and math", "search"),
        ("what is dog", "query"),
        ("info grammar", "info"),
        ("import all", "import"),
        ("speculate on grammar", "speculate"),
        ("snapshot grammar", "snapshot"),
        ("evidence abc-123", "evidence"),
        ("domains", "domains"),
        ("programs", "programs"),
        ("suggest", "suggest"),
        ("stats", "stats"),
    ]
    for query, expected_action in cases:
        cmd = compile_query(query)
        assert cmd.action == expected_action, \
            f"'{query}': expected action={expected_action!r}, got {cmd.action!r}"
