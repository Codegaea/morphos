# Refactor Plan: Kernel/Task Execution Boundary

**Status:** Proposal. Not yet implemented.  
**Scope:** Routing discipline only. No changes to mathematics, engine modules, or data model.  
**Estimated lines changed:** ~120 across 2 files (`server.py`, `engine/kernel.py`).

---

## The Problem

The current codebase has three distinct execution paths for computing things:

**Path 1 — Already correct:** endpoints like `/api/compose`, `/api/infer`, `/api/speculate`
```python
# ✓ Goes through scheduler
tid = scheduler.submit("compose", {"domain_name": domain_name})
return scheduler.execute(tid)
```

**Path 2 — Not yet correct:** endpoints like `/api/search`, `/api/topology/report`, `/api/evidence`
```python
# ✗ Calls engine directly — result is not stored as a task artifact
results = find_analogies_csp(sc, tc, max_results=data.max_results)
return {"results": results}
```

**Path 3 — Intentionally correct and stays:** pure reads
```python
# ✓ Direct reads are fine
return {"morphisms": store.get_morphisms(domain_id)}
```

The problem with Path 2: when `find_analogies_csp` is called directly, there is no task record, no timing, no status, no retry mechanism, and the result is not persisted to the `tasks` table before being returned. If the call fails partway through, nothing is recorded. If you want to audit what the system computed and when, Path 2 calls are invisible.

---

## The Rule

After this refactor, the rule is:

> **Any operation that computes, infers, mutates belief state, or creates derivations must enter as a task and leave as a stored artifact.**

> **Pure reads (get, list, fetch) remain direct.**

That's the entire rule. One sentence each.

---

## What Changes

### 1. Add three task types to `TASK_TYPES` in `engine/kernel.py`

**File:** `engine/kernel.py`  
**Location:** The `TASK_TYPES` dict, ~line 1260

```python
# BEFORE
TASK_TYPES = {
    "compose":  "Compute compositions in a domain",
    "speculate":"Generate candidate morphisms",
    "map":      "Find structural analogy between domains",
    "learn":    "Store and reinforce an analogy",
    "infer":    "Run typed inference (transitive closure, etc.)",
    "verify":   "Check categorical laws",
    "snapshot": "Create versioned snapshot of a domain",
    "test":     "Run program test suite",
}

# AFTER — add three entries
TASK_TYPES = {
    "compose":        "Compute compositions in a domain",
    "speculate":      "Generate candidate morphisms",
    "map":            "Find structural analogy between domains",
    "learn":          "Store and reinforce an analogy",
    "infer":          "Run typed inference (transitive closure, etc.)",
    "verify":         "Check categorical laws",
    "snapshot":       "Create versioned snapshot of a domain",
    "test":           "Run program test suite",
    "search":         "CSP/embedding analogy search between two domains",   # NEW
    "topology":       "Compute full topology report for a domain",          # NEW
    "belief_update":  "Apply evidence and propagate belief revision",        # NEW
}
```

### 2. Add three builtin handlers to `TaskScheduler._builtin_handler`

**File:** `engine/kernel.py`  
**Location:** `TaskScheduler._builtin_handler` method, after the existing `snapshot` handler

```python
elif task_type == "search":
    from engine.scale import find_analogies_csp
    source_domain = params["source_domain"]
    target_domain = params["target_domain"]
    method        = params.get("method", "csp")
    max_results   = params.get("max_results", 5)
    src = self.store.export_category(self.store.get_domain(source_domain)["id"])
    tgt = self.store.export_category(self.store.get_domain(target_domain)["id"])
    results = find_analogies_csp(src, tgt, max_results=max_results)
    # Register best result as a program artifact
    if results and results[0].get("score", 0) > 0:
        self.store.register_program(
            f"{source_domain}→{target_domain}",
            source_domain, target_domain,
            results[0]["object_map"],
            score=results[0].get("score", 0)
        )
    return {"results": results, "method": method, "count": len(results)}

elif task_type == "topology":
    from engine.topology import compute_topology_report
    domain_name    = params["domain_name"]
    max_dim        = params.get("max_dim", 3)
    t_norm         = params.get("t_norm", "godel")
    min_persistence= params.get("min_persistence", 0.0)
    return compute_topology_report(
        self.store, domain_name,
        max_dim=min(max_dim, 4),
        t_norm=t_norm,
        min_persistence=min_persistence,
    )

elif task_type == "belief_update":
    morphism_id        = params["morphism_id"]
    label              = params.get("label", "evidence")
    direction          = params.get("direction", "confirms")
    strength           = params.get("strength", 0.8)
    source             = params.get("source", "api")
    eid = self.store.add_evidence(morphism_id, label, direction, strength, source)
    return {"evidence_id": eid, "morphism_id": morphism_id}
```

### 3. Update three endpoints in `server.py`

These are the only three endpoints in `server.py` that need to change. Every other endpoint either already uses the scheduler (correct) or is a pure read (intentionally direct).

---

**Endpoint 1: `POST /api/search`** (~line 168)

```python
# BEFORE — calls find_analogies_csp directly, result not stored as task
@app.post("/api/search")
def search(data: SearchIn):
    src = store.get_domain(data.source_domain)
    tgt = store.get_domain(data.target_domain)
    if not src: raise HTTPException(404, f"Domain '{data.source_domain}' not found")
    if not tgt: raise HTTPException(404, f"Domain '{data.target_domain}' not found")
    sc = store.export_category(src["id"]); tc = store.export_category(tgt["id"])
    if data.method == "csp":
        results = find_analogies_csp(sc, tc, max_results=data.max_results, ...)
    ...
    return {"results": results, "method": data.method, "count": len(results)}


# AFTER — routes through scheduler, result stored in tasks table
@app.post("/api/search")
def search(data: SearchIn):
    if not store.get_domain(data.source_domain):
        raise HTTPException(404, f"Domain '{data.source_domain}' not found")
    if not store.get_domain(data.target_domain):
        raise HTTPException(404, f"Domain '{data.target_domain}' not found")
    tid = scheduler.submit("search", {
        "source_domain": data.source_domain,
        "target_domain": data.target_domain,
        "method":        data.method,
        "max_results":   data.max_results,
    })
    return scheduler.execute(tid)
```

The CSP call and program registration both move into the `"search"` builtin handler. The endpoint becomes 7 lines.

Note: the `"embedding"`, `"scalable"`, and `"exact"` method variants of search currently live only in server.py. They should either be added to the `"search"` builtin handler as branches, or registered as separate task types (`"search_embedding"`, etc.). The minimal version handles only `"csp"` through the task; the other methods can be wired incrementally.

---

**Endpoint 2: `POST /api/topology/report`** (~line 814)

```python
# BEFORE — calls compute_topology_report directly
@app.post("/api/topology/report")
def topology_report(req: TopologyRequest):
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


# AFTER — routes through scheduler
@app.post("/api/topology/report")
def topology_report(req: TopologyRequest):
    if not store.get_domain(req.domain_name):
        raise HTTPException(404, f"Domain '{req.domain_name}' not found")
    tid = scheduler.submit("topology", {
        "domain_name":    req.domain_name,
        "max_dim":        req.max_dim,
        "t_norm":         req.t_norm,
        "min_persistence":req.min_persistence,
    })
    return scheduler.execute(tid)
```

The other 11 topology endpoints (`/isomorphisms`, `/homology`, `/persistent-homology`, etc.) are all read-only computations that do not mutate belief state — they can remain direct for now. They are candidates for the next pass, not this one.

---

**Endpoint 3: `POST /api/evidence`** (~line 158)

```python
# BEFORE — calls store.add_evidence directly, no task record
@app.post("/api/evidence")
def add_evidence(data: EvidenceIn):
    return {"evidence_id": store.add_evidence(
        data.morphism_id, data.label, data.direction,
        data.strength, data.source
    )}


# AFTER — routes through scheduler
@app.post("/api/evidence")
def add_evidence(data: EvidenceIn):
    tid = scheduler.submit("belief_update", {
        "morphism_id": data.morphism_id,
        "label":       data.label,
        "direction":   data.direction,
        "strength":    data.strength,
        "source":      data.source,
    })
    return scheduler.execute(tid)
```

This one matters most: evidence submission triggers belief propagation, which cascades through the `morphism_dependencies` graph. That cascade should be a task artifact, not a silent side effect. With this change, every belief revision is auditable: you can query `GET /api/tasks?status=completed` and see every belief_update that ever ran, when it ran, what it changed, and how long it took.

---

## What Does Not Change

Everything else stays exactly as it is:

| Category | Examples | Action |
|---|---|---|
| Pure reads | `GET /api/domains`, `GET /api/morphisms`, `GET /api/evidence` | No change — direct reads are correct |
| Already task-backed | `/api/compose`, `/api/infer`, `/api/speculate` | No change — already correct |
| Write primitives | `POST /api/domains`, `POST /api/morphisms` | No change — kernel primitives, not computations |
| Topology reads | All 11 individual topology endpoints | No change this pass — next pass |
| Engine modules | All of `engine/` | No change — this is purely routing |
| Mathematics | Categories, functors, topology, Heyting algebra | No change — untouched |
| Tests | All 190 | No change — they test engine logic, not endpoint routing |
| Examples | Both working examples | No change — they call engine directly, which is correct for scripts |

---

## The Incremental Order

**Pass 1 (this document):** Wire the three highest-value operations through tasks.
- `"search"` — because it's the core operation and its results should be persisted
- `"topology"` — because it's the most expensive computation and benefits most from task tracking
- `"belief_update"` — because belief revision is the operation whose audit trail matters most

**Pass 2 (later, optional):** Wire the 11 individual topology endpoints through tasks.
Each is currently a direct `CategorySnapshot.from_store()` call. They could be registered as a single `"topology_component"` task type with a `component` param (`"isomorphisms"`, `"homology"`, etc.).

**Pass 3 (much later, if needed):** Wire write primitives through tasks.
`add_morphism` and `create_domain` are currently kernel primitives. Making them task-backed would give you a complete audit log of every knowledge mutation. This is the most disruptive change and has the most operational overhead — do it only if you need the audit trail at the write level.

---

## Verification

After implementing Pass 1, these three assertions should hold:

```python
# 1. Every analogy search produces a task record
results = requests.post("/api/search", json={
    "source_domain": "solar_system",
    "target_domain": "atomic_structure"
}).json()
tasks = requests.get("/api/tasks?status=completed").json()
assert any(t["task_type"] == "search" for t in tasks["tasks"])

# 2. Every topology report produces a task record  
requests.post("/api/topology/report", json={"domain_name": "solar_system"})
tasks = requests.get("/api/tasks?status=completed").json()
assert any(t["task_type"] == "topology" for t in tasks["tasks"])

# 3. Every belief update produces a task record
requests.post("/api/evidence", json={
    "morphism_id": mid, "label": "test", "direction": "confirms",
    "strength": 0.9, "source": "test"
})
tasks = requests.get("/api/tasks?status=completed").json()
assert any(t["task_type"] == "belief_update" for t in tasks["tasks"])
```

All 190 existing tests should continue to pass unchanged.

---

## What This Enables

After Pass 1, MORPHOS gains:

**Auditability:** Every computation has a timestamp, duration, params, and result in the `tasks` table. Query `GET /api/tasks` to see the complete reasoning history of the system.

**Replay:** Any task can be resubmitted with the same params. `scheduler.submit(task_type, params)` followed by `scheduler.execute(tid)` is the complete API.

**Observability:** A future monitoring dashboard can query task throughput, average search duration, and belief update frequency without instrumenting the engine.

**Consistency:** The rule "check the tasks table for what the system has computed" becomes unconditionally true, not true-except-for-three-endpoints.

---

## What This Is Not

This is not a redesign of the mathematical model. It is not a refactor of the engine modules. It is not a change to how the `TaskScheduler` or `ReasoningStore` work internally.

It is a routing discipline: three endpoints, three new task types, three new builtin handlers, ~120 lines total.
