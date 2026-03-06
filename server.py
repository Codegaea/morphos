"""
MORPHOS Reasoning OS — API Server

Every endpoint uses the persistent SQLite kernel. Knowledge survives sessions.
Tasks are first-class. Programs are versioned. Evidence is tracked.

Run: uvicorn server:app --reload --port 8000
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

from engine import (
    create_category, find_functors, find_functors_scalable,
    find_paths, composition_report,
    speculate_morphisms, speculation_report,
    Category,
)
from engine.kernel import ReasoningStore, TaskScheduler
from engine.scale import find_analogies_csp, embedding_assisted_search, KnowledgeStore
from engine.learning import AnalogyMemory, learn_and_search, suggest_explorations
from engine.natural import product_category, coproduct_category, opposite_category

DB_PATH = os.environ.get("MORPHOS_DB", "morphos.db")
store = ReasoningStore(DB_PATH)
scheduler = TaskScheduler(store)
memory = AnalogyMemory(store=store)  # Persistent: analogies survive restarts
knowledge_store = KnowledgeStore()
try:
    knowledge_store.load_all_datasets()
except Exception:
    pass

app = FastAPI(title="MORPHOS Reasoning OS", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Models ────────────────────────────────────────────

class MorphismIn(BaseModel):
    label: str; source: str; target: str; rel_type: str = ""; value: Optional[float] = None
    truth_degree: float = 1.0; truth_modality: str = "ACTUAL"

class DomainIn(BaseModel):
    name: str; description: str = ""

class ImportIn(BaseModel):
    name: str; objects: list[str]; morphisms: list[list]

class EvidenceIn(BaseModel):
    morphism_id: str; label: str; direction: str = "supports"; strength: float = 0.8; source: str = ""

class SearchIn(BaseModel):
    source_domain: str; target_domain: str; method: str = "csp"; max_results: int = 5

class TaskIn(BaseModel):
    task_type: str; params: dict = {}; priority: int = 0

class ProgramIn(BaseModel):
    name: str; source_domain: str; target_domain: str; object_map: dict
    morphism_map: dict = {}; score: float = 0.0; classification: str = "functor"

class ProgramTestIn(BaseModel):
    test_type: str; input_data: dict; expected_output: dict

class QueryIn(BaseModel):
    subject: Optional[str] = None; relation: Optional[str] = None
    object: Optional[str] = None; domain: Optional[str] = None; limit: int = 50

# ── System ────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "MORPHOS Reasoning OS", "version": "2.0.0", "store": store.stats, "knowledge_store": knowledge_store.stats}

@app.get("/health")
def health():
    return {"status": "operational", "db": DB_PATH, "store": store.stats}

# ── Domains ───────────────────────────────────────────

@app.post("/api/domains")
def create_domain(data: DomainIn):
    return {"domain_id": store.create_domain(data.name, data.description), "name": data.name}

@app.get("/api/domains")
def list_domains():
    return {"domains": store.list_domains()}

@app.get("/api/domains/{name}")
def get_domain(name: str):
    d = store.get_domain(name)
    if not d: raise HTTPException(404, f"Domain '{name}' not found")
    return d

@app.post("/api/domains/{domain_id}/snapshot")
def snapshot_domain(domain_id: str):
    return {"snapshot_id": store.snapshot_domain(domain_id)}

@app.post("/api/domains/{domain_id}/export")
def export_domain(domain_id: str):
    return store.export_category(domain_id).to_dict()

# ── Import ────────────────────────────────────────────

@app.post("/api/import")
def import_data(data: ImportIn):
    morphs = [(m[0], m[1], m[2], m[3] if len(m)>3 else "", m[4] if len(m)>4 else None) for m in data.morphisms]
    cat = create_category(data.name, data.objects, morphs, auto_close=False)
    did = store.import_category(cat)
    return {"domain_id": did, "name": data.name, "objects": len(data.objects), "morphisms": len(data.morphisms)}

@app.post("/api/import/dataset/{name}")
def import_curated_dataset(name: str):
    from engine.datasets import ALL_DATASETS
    from engine.knowledge_base import ALL_EXTENDED_DATASETS
    from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
    all_ds = {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}
    if name not in all_ds: raise HTTPException(404, f"Dataset '{name}' not found. Available: {list(all_ds.keys())}")
    data = all_ds[name]()
    cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
    did = store.import_category(cat, domain_name=name)
    return {"domain_id": did, "name": name, "objects": len(data["objects"]), "morphisms": len(data["morphisms"])}

@app.get("/api/datasets")
def list_datasets():
    from engine.datasets import ALL_DATASETS
    from engine.knowledge_base import ALL_EXTENDED_DATASETS
    from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
    return {"datasets": {n: {"objects": len(fn()["objects"]), "morphisms": len(fn()["morphisms"])} for n, fn in {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}.items()}}

# ── Morphisms & Concepts ──────────────────────────────

@app.post("/api/domains/{domain_id}/morphisms")
def add_morphism(domain_id: str, data: MorphismIn):
    return {"morphism_id": store.add_morphism(domain_id, data.label, data.source, data.target, rel_type=data.rel_type, value=data.value, truth_degree=data.truth_degree, truth_modality=data.truth_modality)}

@app.get("/api/domains/{domain_id}/morphisms")
def get_morphisms(domain_id: str, source: str = None, target: str = None, rel_type: str = None):
    return {"morphisms": store.get_morphisms(domain_id, source, target, rel_type)}

@app.get("/api/domains/{domain_id}/concepts")
def get_concepts(domain_id: str):
    return {"concepts": store.get_concepts(domain_id)}

@app.post("/api/domains/{domain_id}/derive")
def derive(domain_id: str, label: str, source: str, target: str, rel_type: str = "", rule: str = "user", premises: str = ""):
    pl = [p.strip() for p in premises.split(",") if p.strip()] if premises else []
    return {"morphism_id": store.add_derived_morphism(domain_id, label, source, target, rel_type, rule, pl)}

# ── Evidence ──────────────────────────────────────────

@app.post("/api/evidence")
def add_evidence(data: EvidenceIn):
    return {"evidence_id": store.add_evidence(data.morphism_id, data.label, data.direction, data.strength, data.source)}

@app.get("/api/evidence/{morphism_id}")
def get_evidence(morphism_id: str):
    return {"evidence": store.get_evidence(morphism_id)}

# ── Search ────────────────────────────────────────────

@app.post("/api/search")
def search(data: SearchIn):
    src = store.get_domain(data.source_domain)
    tgt = store.get_domain(data.target_domain)
    if not src: raise HTTPException(404, f"Domain '{data.source_domain}' not found")
    if not tgt: raise HTTPException(404, f"Domain '{data.target_domain}' not found")
    sc = store.export_category(src["id"]); tc = store.export_category(tgt["id"])
    if data.method == "csp": results = find_analogies_csp(sc, tc, max_results=data.max_results, knowledge_store=knowledge_store)
    elif data.method == "embedding": results = embedding_assisted_search(sc, tc, top_k=data.max_results)
    elif data.method == "scalable":
        ms = find_functors_scalable(sc, tc, min_score=0.0)
        results = [{"object_map": m.object_map, "score": m.overall_score} for m in ms]
    elif data.method == "exact":
        fs = find_functors(sc, tc, mode="exact", max_results=data.max_results)
        results = [{"object_map": f.object_map, "score": 1.0, "classification": f.classification()} for f in fs]
    else: raise HTTPException(400, f"Unknown method: {data.method}")
    if results and results[0].get("score", 0) > 0:
        store.register_program(f"{data.source_domain}→{data.target_domain}", data.source_domain, data.target_domain, results[0]["object_map"], score=results[0].get("score", 0))
    return {"results": results, "method": data.method, "count": len(results)}

@app.get("/api/memory")
def get_memory():
    """Return AnalogyMemory stats and all stored analogies."""
    analogies = [a.to_dict() for a in memory.all_analogies()]
    return {
        **memory.stats,
        "analogies": analogies,
    }

@app.post("/api/search/learn")
def search_learn(data: SearchIn):
    src = store.get_domain(data.source_domain); tgt = store.get_domain(data.target_domain)
    if not src or not tgt: raise HTTPException(404, "Domain not found")
    sc = store.export_category(src["id"]); tc = store.export_category(tgt["id"])
    results = learn_and_search(sc, tc, memory, min_score=0.0)
    return {"results": [a.to_dict() for a in results], "memory_stats": memory.stats}

@app.get("/api/search/suggest")
def search_suggest():
    cats = {}
    for d in store.list_domains():
        try: cats[d["name"]] = store.export_category(d["id"])
        except Exception: pass
    return {"suggestions": [{"source": s, "target": t, "score": sc, "reason": r} for s, t, sc, r in suggest_explorations(memory, cats, max_suggestions=10)]}

# ── Programs ──────────────────────────────────────────

@app.post("/api/programs")
def register_program(data: ProgramIn):
    return {"program_id": store.register_program(data.name, data.source_domain, data.target_domain, data.object_map, data.morphism_map, data.score, data.classification)}

@app.get("/api/programs")
def list_programs():
    return {"programs": store.list_programs()}

@app.get("/api/programs/{name}")
def get_program(name: str, version: int = None):
    p = store.get_program(name, version)
    if not p: raise HTTPException(404, f"Program '{name}' not found")
    return p

@app.post("/api/programs/{pid}/test")
def add_test(pid: str, data: ProgramTestIn):
    return {"test_id": store.add_program_test(pid, data.test_type, data.input_data, data.expected_output)}

@app.post("/api/programs/{pid}/run-tests")
def run_tests(pid: str):
    return store.run_program_tests(pid)

@app.post("/api/programs/{pid}/reinforce")
def reinforce(pid: str):
    store.reinforce_program(pid); return {"reinforced": True}

# ── Tasks ─────────────────────────────────────────────

@app.post("/api/tasks")
def submit_task(data: TaskIn):
    return {"task_id": scheduler.submit(data.task_type, data.params, data.priority)}

@app.post("/api/tasks/{tid}/execute")
def execute_task(tid: str):
    return scheduler.execute(tid)

@app.post("/api/tasks/run-next")
def run_next():
    r = scheduler.run_next()
    return r if r else {"message": "No pending tasks"}

@app.post("/api/tasks/run-all")
def run_all():
    rs = scheduler.run_all_pending()
    return {"executed": len(rs), "results": rs}

@app.get("/api/tasks")
def list_tasks(status: str = None):
    return {"tasks": scheduler.list_tasks(status)}

# ── Knowledge Store ───────────────────────────────────

@app.post("/api/query")
def query(data: QueryIn):
    rs = knowledge_store.query(data.subject, data.relation, data.object, data.domain, data.limit)
    return {"results": [{"relation": r, "subject": s, "object": t, "domain": d} for r, s, t, d in rs]}

@app.get("/api/query/neighborhood/{concept}")
def neighborhood(concept: str, max_hops: int = 1, max_nodes: int = 30):
    return knowledge_store.neighborhood(concept, max_hops, max_nodes)

# ── Category Operations ───────────────────────────────

@app.post("/api/operations/product")
def op_product(a: str, b: str):
    da = store.get_domain(a); db = store.get_domain(b)
    if not da or not db: raise HTTPException(404, "Domain not found")
    p = product_category(store.export_category(da["id"]), store.export_category(db["id"]))
    return {"domain_id": store.import_category(p, f"{a}×{b}"), "objects": len(p.objects), "morphisms": len(p.user_morphisms())}

@app.post("/api/operations/coproduct")
def op_coproduct(a: str, b: str):
    da = store.get_domain(a); db = store.get_domain(b)
    if not da or not db: raise HTTPException(404, "Domain not found")
    c = coproduct_category(store.export_category(da["id"]), store.export_category(db["id"]))
    return {"domain_id": store.import_category(c, f"{a}+{b}"), "objects": len(c.objects), "morphisms": len(c.user_morphisms())}

@app.post("/api/operations/opposite")
def op_opposite(name: str):
    d = store.get_domain(name)
    if not d: raise HTTPException(404, "Domain not found")
    o = opposite_category(store.export_category(d["id"]))
    return {"domain_id": store.import_category(o, f"{name}_op"), "objects": len(o.objects), "morphisms": len(o.user_morphisms())}

@app.post("/api/compose/{domain_id}")
def compose(domain_id: str):
    cat = store.export_category(domain_id); new = cat.auto_compose()
    return {"new_compositions": len(new), "total_morphisms": len(cat.morphisms)}

# ── Query Language ────────────────────────────────────

class CompileIn(BaseModel):
    query: str

@app.post("/api/compile")
def compile_query_endpoint(data: CompileIn):
    """Compile a natural language query into a structured command."""
    from engine.query_lang import compile_query
    known = set(d["name"] for d in store.list_domains())
    result = compile_query(data.query, known_domains=known)
    return {
        "action": result.action,
        "params": result.params,
        "confidence": result.confidence,
        "task": result.to_task(),
    }

@app.post("/api/compile/execute")
def compile_and_execute(data: CompileIn):
    """Compile a natural language query and execute it."""
    from engine.query_lang import compile_query
    known = set(d["name"] for d in store.list_domains())
    cmd = compile_query(data.query, known_domains=known)
    task = cmd.to_task()
    if task:
        tid = scheduler.submit(task["task_type"], task["params"])
        result = scheduler.execute(tid)
        return {"action": cmd.action, "params": cmd.params, "confidence": cmd.confidence, "result": result}
    return {"action": cmd.action, "params": cmd.params, "confidence": cmd.confidence, "result": None}


# ── Explain / Proof Traces ─────────────────────────────

@app.get("/api/explain/{morphism_id}")
def explain_morphism(morphism_id: str, max_depth: int = 10):
    """Return a full proof explanation tree for a morphism."""
    node = store.explain_morphism(morphism_id, max_depth=max_depth)
    if "error" in node:
        raise HTTPException(404, node["error"])
    return node


@app.get("/api/explain/{domain_name}/path")
def explain_path(domain_name: str, source: str, target: str):
    """Explain all morphisms from source→target in a domain."""
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    nodes = store.explain_path(source, target, d["id"])
    return {"source": source, "target": target, "domain": domain_name, "explanations": nodes}


# ── Inference & Composition ────────────────────────────

class DomainOpIn(BaseModel):
    domain_name: str

class InferIn(BaseModel):
    domain_name: str
    rule: str = "transitivity"

@app.post("/api/domains/{domain_name}/compose")
def compose_domain(domain_name: str):
    """Run auto-composition on a domain and persist new morphisms."""
    tid = scheduler.submit("compose", {"domain_name": domain_name})
    return scheduler.execute(tid)

@app.post("/api/domains/{domain_name}/infer")
def infer_domain(domain_name: str, rule: str = "transitivity"):
    """Run typed inference on a domain (default: transitivity)."""
    tid = scheduler.submit("infer", {"domain_name": domain_name, "rule": rule})
    return scheduler.execute(tid)

@app.post("/api/domains/{domain_name}/speculate")
def speculate_domain(domain_name: str):
    """Generate speculative morphisms for a domain."""
    tid = scheduler.submit("speculate", {"domain_name": domain_name})
    return scheduler.execute(tid)


# ── Belief Revision ────────────────────────────────────

class BeliefRevisionIn(BaseModel):
    morphism_id: str
    label: str
    direction: str = "supports"
    strength: float = 0.8
    source: str = ""
    show_propagation: bool = True

@app.post("/api/belief/update")
def belief_update(data: BeliefRevisionIn):
    """
    Add evidence to a morphism and propagate belief changes through the
    derivation graph.

    Returns the updated morphism and a list of derived morphisms whose
    truth values changed as a result (belief revision report).
    """
    # Snapshot truth values before
    def _get_all_truths():
        rows = store.conn.execute(
            "SELECT id, label, source_label, target_label, truth_degree, truth_modality, is_inferred "
            "FROM morphisms WHERE is_identity=0").fetchall()
        return {r["id"]: (r["truth_degree"], r["truth_modality"]) for r in rows}

    before = _get_all_truths()

    eid = store.add_evidence(
        data.morphism_id, data.label, data.direction, data.strength, data.source)

    after = _get_all_truths()

    changed = []
    for mid, (new_deg, new_mod) in after.items():
        old_deg, old_mod = before.get(mid, (new_deg, new_mod))
        if abs(new_deg - old_deg) > 1e-6 or new_mod != old_mod:
            row = store.conn.execute(
                "SELECT label, source_label, target_label, is_inferred FROM morphisms WHERE id=?",
                (mid,)).fetchone()
            if row:
                changed.append({
                    "morphism_id": mid,
                    "label": row["label"],
                    "source": row["source_label"],
                    "target": row["target_label"],
                    "is_inferred": bool(row["is_inferred"]),
                    "truth_before": f"{old_mod}({old_deg:.3f})",
                    "truth_after": f"{new_mod}({new_deg:.3f})",
                    "delta": new_deg - old_deg,
                })

    updated_morph = store.conn.execute(
        "SELECT label, source_label, target_label, truth_degree, truth_modality "
        "FROM morphisms WHERE id=?", (data.morphism_id,)).fetchone()

    return {
        "evidence_id": eid,
        "morphism": dict(updated_morph) if updated_morph else None,
        "propagated_changes": changed if data.show_propagation else [],
        "total_affected": len(changed),
    }


# ── Pipeline (canonical 7-step workflow) ─────────────

class PipelineIn(BaseModel):
    source_domain: str
    target_domain: str
    method: str = "csp"

@app.post("/api/pipeline")
def run_pipeline(data: PipelineIn):
    """
    Execute the canonical 7-step MORPHOS reasoning workflow:

    1. Import check (domains must exist)
    2. Evidence audit (count evidenced morphisms)
    3. Auto-compose source domain
    4. Analogy search (CSP/embedding/scalable)
    5. Store best mapping as versioned program
    6. Run program tests
    7. Inspect derivations and flag weak beliefs

    Returns a full audit trail of all steps.
    """
    import time
    steps = {}
    overall_t0 = time.time()

    def record(step_num: int, name: str, result: dict, ok: bool = True):
        steps[f"step_{step_num}_{name}"] = {**result, "ok": ok}

    # 1. Import check
    src = store.get_domain(data.source_domain)
    tgt = store.get_domain(data.target_domain)
    if not src:
        raise HTTPException(404, f"Source domain '{data.source_domain}' not found")
    if not tgt:
        raise HTTPException(404, f"Target domain '{data.target_domain}' not found")
    src_concepts = store.get_concepts(src["id"])
    tgt_concepts = store.get_concepts(tgt["id"])
    record(1, "import", {
        "source": data.source_domain,
        "target": data.target_domain,
        "source_objects": len(src_concepts),
        "target_objects": len(tgt_concepts),
    })

    # 2. Evidence audit
    src_morphs = store.get_morphisms(src["id"])
    tgt_morphs = store.get_morphisms(tgt["id"])
    src_evidenced = sum(1 for m in src_morphs if m["evidence_ids"] != "[]")
    tgt_evidenced = sum(1 for m in tgt_morphs if m["evidence_ids"] != "[]")
    record(2, "evidence_audit", {
        "source_evidenced": src_evidenced,
        "source_total": len(src_morphs),
        "target_evidenced": tgt_evidenced,
        "target_total": len(tgt_morphs),
    })

    # 3. Composition
    compose_tid = scheduler.submit("compose", {"domain_name": data.source_domain})
    compose_result = scheduler.execute(compose_tid)
    record(3, "compose", compose_result)

    # 4. Analogy search
    t0 = time.time()
    sc = store.export_category(src["id"])
    tc = store.export_category(tgt["id"])
    if data.method == "csp":
        results = find_analogies_csp(sc, tc, max_results=5, knowledge_store=knowledge_store)
    elif data.method == "embedding":
        results = embedding_assisted_search(sc, tc, top_k=5)
    else:
        from engine import find_functors_scalable
        ms = find_functors_scalable(sc, tc, min_score=0.0)
        results = [{"object_map": m.object_map, "score": m.overall_score} for m in ms]
    dt_ms = (time.time() - t0) * 1000
    best = results[0] if results and results[0].get("score", 0) > 0 else None
    record(4, "search", {
        "method": data.method,
        "results_count": len(results),
        "best_score": best["score"] if best else 0.0,
        "structural_score": best.get("structural_score") if best else None,
        "semantic_score": best.get("semantic_score") if best else None,
        "partial": best.get("partial", False) if best else False,
        "object_map": best["object_map"] if best else {},
        "duration_ms": dt_ms,
    }, ok=best is not None)

    # 5. Store program
    pid = None
    if best:
        prog_name = f"{data.source_domain}→{data.target_domain}"
        pid = store.register_program(prog_name, data.source_domain, data.target_domain,
                                     best["object_map"], score=best["score"])
        record(5, "store_program", {"program_id": pid, "program_name": prog_name,
                                     "score": best["score"]})
    else:
        record(5, "store_program", {"program_id": None, "message": "No mapping to store"}, ok=False)

    # 6. Program tests
    if pid:
        test_result = store.run_program_tests(pid)
        record(6, "program_tests", test_result)
    else:
        record(6, "program_tests", {"skipped": True, "message": "No program created"}, ok=False)

    # 7. Derivation inspection
    all_morphs = store.get_morphisms(src["id"]) + store.get_morphisms(tgt["id"])
    inferred = [m for m in all_morphs if m["is_inferred"]]
    weak = [
        {"id": m["id"], "label": m["label"], "source": m["source_label"],
         "target": m["target_label"], "truth": m["truth_degree"]}
        for m in all_morphs if m["truth_degree"] < 0.7
    ]
    record(7, "derivations", {
        "inferred_morphisms": len(inferred),
        "weak_morphisms": len(weak),
        "weak_details": weak[:10],
    })

    total_ms = (time.time() - overall_t0) * 1000
    steps_ok = sum(1 for v in steps.values() if v.get("ok", True))

    return {
        "source_domain": data.source_domain,
        "target_domain": data.target_domain,
        "method": data.method,
        "steps": steps,
        "steps_completed": steps_ok,
        "total_steps": len(steps),
        "program_id": pid,
        "total_duration_ms": total_ms,
        "summary": {
            "analogy_found": best is not None,
            "best_score": best["score"] if best else 0.0,
            "inferred_morphisms": len(inferred),
            "programs_registered": 1 if pid else 0,
        }
    }


@app.post("/api/speculate/{domain_id}")
def speculate(domain_id: str):
    cat = store.export_category(domain_id)
    candidates = speculate_morphisms(cat)
    return {"speculated": len(candidates), "report": speculation_report(cat)}


# ══════════════════════════════════════════════════════════════════════
# Proof System Endpoints (Session 4)
# ══════════════════════════════════════════════════════════════════════

# ── Proof verification ────────────────────────────────
@app.get("/api/proof/{morphism_id}/check")
def check_proof(morphism_id: str):
    """
    Verify that a morphism's proof is structurally valid.

    Checks all premises exist, chain is unbroken for transitivity,
    endpoints match the conclusion, and truth degree is consistent.
    Returns {valid, rule, premises, conclusion, truth_degree, errors}.
    """
    return store.check_proof(morphism_id)


@app.get("/api/proof/{morphism_id}/normalize")
def normalize_proof(morphism_id: str):
    """
    Return the canonical (beta-normal) proof term for a morphism.

    The canonical form is associativity-invariant: two derivations of
    the same morphism via different associativity groupings produce the
    same string. Suitable as a proof deduplication key.
    """
    morph = store.conn.execute("SELECT id FROM morphisms WHERE id=?", (morphism_id,)).fetchone()
    if not morph:
        raise HTTPException(404, f"Morphism {morphism_id} not found")
    canonical = store.normalize_proof_term(morphism_id)
    return {"morphism_id": morphism_id, "canonical": canonical}


# ── Dependency index ──────────────────────────────────
@app.get("/api/morphisms/{morphism_id}/dependents")
def get_dependents(morphism_id: str, recursive: bool = False):
    """
    Return all morphisms derived from this one.
    recursive=true returns the full transitive closure.

    This is the forward-chaining view: 'what does this morphism support?'
    Complements explain_morphism (backward: 'what supports this?').
    """
    morph = store.conn.execute(
        "SELECT label, source_label, target_label FROM morphisms WHERE id=?",
        (morphism_id,)).fetchone()
    if not morph:
        raise HTTPException(404, f"Morphism {morphism_id} not found")
    dep_ids = store.get_dependents(morphism_id, recursive=recursive)
    dependents = []
    for did in dep_ids:
        row = store.conn.execute(
            "SELECT id, label, source_label, target_label, truth_degree, truth_modality, is_inferred "
            "FROM morphisms WHERE id=?", (did,)).fetchone()
        if row:
            dependents.append(dict(row))
    return {
        "morphism_id": morphism_id,
        "morphism_label": morph["label"],
        "source": morph["source_label"],
        "target": morph["target_label"],
        "dependents": dependents,
        "count": len(dependents),
        "recursive": recursive,
    }


# ── Structure extraction ──────────────────────────────
class ExtractCoreIn(BaseModel):
    source_domain: str
    target_domain: str
    object_map: dict
    new_domain_name: str = ""


@app.post("/api/extract/common-core")
def extract_common_core(data: ExtractCoreIn):
    """
    Extract the categorical common core of two domains under an analogy.

    Given an object_map F: source_objects → target_objects (a functor),
    finds all morphisms preserved by F (i.e. s→t in source with F(s)→F(t)
    existing in target) and stores them as a new domain.

    This is the categorical pullback of source ×_F target — the abstract
    structure shared by both domains, independent of domain-specific labels.

    Feeds directly into structure discovery: run analogy search, pass the
    best object_map here, get back a new domain representing the discovered
    mathematical structure.
    """
    src = store.get_domain(data.source_domain)
    tgt = store.get_domain(data.target_domain)
    if not src:
        raise HTTPException(404, f"Source domain '{data.source_domain}' not found")
    if not tgt:
        raise HTTPException(404, f"Target domain '{data.target_domain}' not found")

    name = data.new_domain_name or f"core_{data.source_domain}∩{data.target_domain}"
    core_id = store.extract_common_core(src["id"], tgt["id"], data.object_map, name)

    if core_id is None:
        return {
            "extracted": False,
            "message": "No morphisms are preserved under this object_map — no common core exists.",
            "object_map_size": len(data.object_map),
        }

    core_morphs = store.get_morphisms(core_id)
    core_domain = store.conn.execute(
        "SELECT name, description FROM domains WHERE id=?", (core_id,)).fetchone()
    return {
        "extracted": True,
        "core_domain_id": core_id,
        "core_domain_name": core_domain["name"],
        "description": core_domain["description"],
        "invariant_morphisms": len(core_morphs),
        "morphisms": [
            {
                "label": m["label"],
                "source": m["source_label"],
                "target": m["target_label"],
                "truth_degree": m["truth_degree"],
                "rel_type": m["rel_type"],
            }
            for m in core_morphs
        ],
        "note": "This domain represents the abstract structure shared by both input domains.",
    }


# ── Bulk proof audit ──────────────────────────────────
@app.get("/api/proof/audit/{domain_name}")
def audit_domain_proofs(domain_name: str):
    """
    Run check_proof on all derived morphisms in a domain.

    Returns a summary of valid vs invalid proofs, plus details of any
    invalid ones. Useful after belief revision to detect drift.
    """
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    morphisms = store.conn.execute(
        "SELECT id, label, source_label, target_label FROM morphisms "
        "WHERE domain_id=? AND is_inferred=1 AND is_identity=0",
        (d["id"],)).fetchall()
    valid_count = 0
    invalid = []
    for m in morphisms:
        result = store.check_proof(m["id"])
        if result["valid"]:
            valid_count += 1
        else:
            invalid.append({
                "morphism_id": m["id"],
                "label": m["label"],
                "conclusion": f"{m['source_label']}→{m['target_label']}",
                "rule": result.get("rule"),
                "errors": result["errors"],
            })
    return {
        "domain": domain_name,
        "total_derived": len(morphisms),
        "valid": valid_count,
        "invalid": len(invalid),
        "invalid_details": invalid,
        "proof_integrity": valid_count / len(morphisms) if morphisms else 1.0,
    }


# ══════════════════════════════════════════════════════════════
# TOPOLOGY ENDPOINTS
# ══════════════════════════════════════════════════════════════

from engine.topology import (
    CategorySnapshot, IsomorphismEngine, FunctorClassifier,
    AdjunctionDetector, LimitsColimits, YonedaEmbedding,
    NerveComplex, HomologyEngine, PersistentHomologyEngine,
    FundamentalGroupoid, MetricEnrichment, HomotopyClassifier,
    compute_topology_report, compare_domains,
)


class TopologyRequest(BaseModel):
    domain_name: str
    max_dim: int = 3
    t_norm: str = "godel"
    min_persistence: float = 0.0


class CompareRequest(BaseModel):
    domain1: str
    domain2: str
    max_dim: int = 2


class FunctorClassifyRequest(BaseModel):
    source_domain: str
    target_domain: str
    object_map: dict


class AdjunctionRequest(BaseModel):
    source_domain: str
    target_domain: str
    F_map: dict   # source → target (left adjoint F: C→D)
    G_map: dict   # target → source (right adjoint G: D→C)
    F_name: str = "F"
    G_name: str = "G"


class HomotopyClassifyRequest(BaseModel):
    source_domain: str
    target_domain: str
    threshold: float = 0.7


@app.post("/api/topology/report")
def topology_report(req: TopologyRequest):
    """
    Full categorical topology report for a domain.
    Computes: isomorphisms, limits, Yoneda, nerve, homology,
    persistent homology, fundamental groupoid, metric enrichment.
    """
    d = store.get_domain(req.domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{req.domain_name}' not found")
    try:
        return compute_topology_report(
            store, req.domain_name,
            max_dim=min(req.max_dim, 4),
            t_norm=req.t_norm,
            min_persistence=req.min_persistence,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/topology/{domain_name}/isomorphisms")
def domain_isomorphisms(domain_name: str, threshold: float = 0.8):
    """
    Find all isomorphisms and isomorphism classes in a domain.
    threshold: minimum iso_degree to include (0=all, 0.99=strict only)
    """
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    eng = IsomorphismEngine(snap)
    isos = eng.find_isomorphisms()
    classes = eng.isomorphism_classes(threshold=threshold)
    return {
        "domain": domain_name,
        "threshold": threshold,
        "isomorphisms": [
            {"morphism_id": r.morphism_id, "source": r.source,
             "target": r.target, "inverse_id": r.inverse_id,
             "iso_degree": r.iso_degree, "iso_type": r.iso_type}
            for r in isos if r.iso_degree >= threshold
        ],
        "isomorphism_classes": classes,
        "n_classes": len(classes),
    }


@app.get("/api/topology/{domain_name}/homology")
def domain_homology(domain_name: str, max_dim: int = 3):
    """Compute Betti numbers and Euler characteristic of the nerve."""
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    nerve = NerveComplex(snap, max_dim=min(max_dim, 4))
    eng = HomologyEngine(nerve)
    betti = eng.betti_numbers(max_dim=min(max_dim, 4))
    euler = eng.euler_characteristic()
    nerve_summary = nerve.summary()
    return {
        "domain": domain_name,
        "betti_numbers": betti,
        "euler_characteristic": euler,
        "nerve": nerve_summary,
        "is_connected": eng.is_connected(),
    }


@app.post("/api/topology/persistent-homology")
def persistent_homology(req: TopologyRequest):
    """
    Compute the filtered persistence diagram of the nerve.
    Returns birth-death pairs, Betti numbers, and topological interpretation.
    """
    d = store.get_domain(req.domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{req.domain_name}' not found")
    snap = CategorySnapshot.from_store(store, req.domain_name)
    nerve = NerveComplex(snap, max_dim=min(req.max_dim, 4))
    eng = PersistentHomologyEngine(nerve)
    diag = eng.compute(min_persistence=req.min_persistence)
    return eng.to_dict(diag)


@app.post("/api/topology/compare")
def topology_compare(req: CompareRequest):
    """
    Compare two domains via bottleneck distance of their persistence diagrams.
    Uses stability theorem: small truth-degree changes → small diagram changes.
    """
    for name in [req.domain1, req.domain2]:
        if not store.get_domain(name):
            raise HTTPException(404, f"Domain '{name}' not found")
    snap1 = CategorySnapshot.from_store(store, req.domain1)
    snap2 = CategorySnapshot.from_store(store, req.domain2)
    return compare_domains(snap1, snap2, max_dim=min(req.max_dim, 3))


@app.get("/api/topology/{domain_name}/fundamental-groupoid")
def fundamental_groupoid(domain_name: str):
    """
    Compute π₀ (connected components) and π₁ rank of the category.
    Also returns graded components at multiple truth thresholds.
    """
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    fg = FundamentalGroupoid(snap)
    result = fg.compute()
    return {
        "domain": domain_name,
        "pi0": result.pi0,
        "n_components": result.n_components,
        "is_connected": result.is_connected,
        "pi1_rank": result.pi1_rank,
        "homotopy_type": result.homotopy_type,
        "graded_components": {str(k): v for k, v in result.graded_components.items()},
    }


@app.get("/api/topology/{domain_name}/metric-enrichment")
def metric_enrichment(domain_name: str, t_norm: str = "godel"):
    """
    View the category as a Lawvere metric space.
    Verifies enrichment axioms and reports any violations.
    t_norm: 'godel' | 'product' | 'lukasiewicz'
    """
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    metric = MetricEnrichment(snap, t_norm=t_norm)
    return metric.verify_enrichment_axioms()


@app.get("/api/topology/{domain_name}/yoneda")
def yoneda_embedding(domain_name: str, object_label: Optional[str] = None):
    """
    Compute Yoneda embedding for a domain.
    If object_label given, returns the representable presheaf at that object.
    Otherwise returns the full Yoneda matrix and its rank.
    """
    import numpy as np
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    yoneda = YonedaEmbedding(snap)
    if object_label:
        psh = yoneda.representable_presheaf(object_label)
        return {
            "object": object_label,
            "presheaf": psh,
            "description": f"y({object_label})(X) = hom_degree(X, {object_label})",
        }
    Y = yoneda.yoneda_matrix()
    rank = int(np.linalg.matrix_rank(Y))
    return {
        "domain": domain_name,
        "n_objects": snap.n_objects,
        "matrix_rank": rank,
        "is_full_rank": rank == snap.n_objects,
        "objects": snap.objects,
        "matrix": Y.tolist(),
        "row_norms": {snap.objects[i]: round(float(np.linalg.norm(Y[i])), 4)
                     for i in range(snap.n_objects)},
    }


@app.get("/api/topology/{domain_name}/limits")
def domain_limits(domain_name: str):
    """
    Compute categorical limits and colimits in the domain.
    Returns terminal, initial objects and sample products/coproducts.
    """
    d = store.get_domain(domain_name)
    if not d:
        raise HTTPException(404, f"Domain '{domain_name}' not found")
    snap = CategorySnapshot.from_store(store, domain_name)
    lim = LimitsColimits(snap)
    objs = snap.objects

    result = {
        "domain": domain_name,
        "terminal_object": {"apex": lim.terminal_object().apex,
                            "degree": lim.terminal_object().degree,
                            "exists": lim.terminal_object().exists},
        "initial_object": {"apex": lim.initial_object().apex,
                           "degree": lim.initial_object().degree,
                           "exists": lim.initial_object().exists},
        "products": [],
        "coproducts": [],
    }
    pairs = [(objs[i], objs[j]) for i in range(min(4, len(objs)))
             for j in range(i+1, min(5, len(objs)))]
    for a, b in pairs[:6]:
        r = lim.product(a, b)
        result["products"].append({"a": a, "b": b, "apex": r.apex, "degree": r.degree})
        r2 = lim.coproduct(a, b)
        result["coproducts"].append({"a": a, "b": b, "apex": r2.apex, "degree": r2.degree})

    return result


@app.post("/api/topology/classify-functor")
def classify_functor(req: FunctorClassifyRequest):
    """
    Classify an analogy (functor) as full, faithful, equivalence, etc.
    """
    for name in [req.source_domain, req.target_domain]:
        if not store.get_domain(name):
            raise HTTPException(404, f"Domain '{name}' not found")
    src = CategorySnapshot.from_store(store, req.source_domain)
    tgt = CategorySnapshot.from_store(store, req.target_domain)
    clf = FunctorClassifier(src, tgt, req.object_map)
    r = clf.classify(program_name=f"{req.source_domain}→{req.target_domain}")
    return {
        "source_domain": r.source_domain,
        "target_domain": r.target_domain,
        "homomorphism_type": r.homomorphism_type,
        "is_faithful": r.is_faithful, "faithful_degree": r.faithful_degree,
        "is_full": r.is_full, "full_degree": r.full_degree,
        "is_essentially_surjective": r.is_essentially_surjective,
        "ess_surjective_degree": r.ess_surjective_degree,
        "is_equivalence": r.is_equivalence, "equivalence_degree": r.equivalence_degree,
        "is_injective_on_objects": r.is_injective_on_objects,
        "is_surjective_on_objects": r.is_surjective_on_objects,
    }


@app.post("/api/topology/check-adjunction")
def check_adjunction(req: AdjunctionRequest):
    """
    Check whether two functors F: C→D, G: D→C form an adjoint pair F ⊣ G.
    """
    for name in [req.source_domain, req.target_domain]:
        if not store.get_domain(name):
            raise HTTPException(404, f"Domain '{name}' not found")
    src = CategorySnapshot.from_store(store, req.source_domain)
    tgt = CategorySnapshot.from_store(store, req.target_domain)
    detector = AdjunctionDetector(src, tgt)
    result = detector.check_adjunction(req.F_name, req.F_map, req.G_name, req.G_map)
    return {
        "F": req.F_name, "G": req.G_name,
        "is_adjunction": result.is_adjunction,
        "adjunction_degree": result.adjunction_degree,
        "hom_iso_degree": result.hom_iso_degree,
        "evidence": result.evidence,
        "interpretation": (
            f"F ⊣ G holds to degree {result.adjunction_degree:.3f}. "
            + ("Adjoint pair confirmed." if result.is_adjunction
               else "Not a strong adjoint pair.")
        ),
    }


@app.post("/api/topology/homotopy-classes")
def homotopy_classes(req: HomotopyClassifyRequest):
    """
    Group stored analogy programs between two domains into homotopy classes.
    Two programs are homotopic if they are naturally isomorphic (connected by
    a natural transformation whose components are isomorphisms).
    """
    for name in [req.source_domain, req.target_domain]:
        if not store.get_domain(name):
            raise HTTPException(404, f"Domain '{name}' not found")

    programs = store.conn.execute(
        "SELECT id, name, object_map, score FROM programs "
        "WHERE source_domain=? AND target_domain=?",
        (req.source_domain, req.target_domain)
    ).fetchall()

    if not programs:
        return {"classes": [], "message": "No programs found between these domains"}

    prog_list = []
    for p in programs:
        om = p["object_map"]
        if isinstance(om, str):
            try:
                om = json.loads(om)
            except Exception:
                om = {}
        prog_list.append({"name": p["name"], "object_map": om, "score": p["score"]})

    src = CategorySnapshot.from_store(store, req.source_domain)
    tgt = CategorySnapshot.from_store(store, req.target_domain)
    clf = HomotopyClassifier(src, tgt)
    classes = clf.classify(prog_list, threshold=req.threshold)

    return {
        "source_domain": req.source_domain,
        "target_domain": req.target_domain,
        "n_programs": len(prog_list),
        "n_homotopy_classes": len(classes),
        "threshold": req.threshold,
        "classes": [
            {"representative": c.representative, "members": c.members,
             "class_size": c.class_size, "nat_iso_degree": c.nat_iso_degree}
            for c in classes
        ],
        "interpretation": (
            f"{len(classes)} genuinely distinct analogy interpretation(s) "
            f"among {len(prog_list)} stored programs."
        ),
    }
