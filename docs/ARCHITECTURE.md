# MORPHOS Architecture

Full layer-by-layer technical walkthrough. Read this before touching the code.

## Quick orientation

```
engine/kernel.py      → the database and proof system
engine/topology.py    → 12 topology engines
engine/scale.py       → analogy search (CSP)
engine/topos.py       → truth values (Heyting algebra)
server.py             → FastAPI (64 endpoints)
morphos-app.jsx       → React UI (10 tabs)
tests/                → 190 tests
examples/             → run solar_system_vs_atom.py first
```

## Layer 0 — Persistent Store

`engine/kernel.py` — `ReasoningStore` class. SQLite with WAL, foreign keys ON.

**DB path:** `ReasoningStore("morphos.db")` or `MORPHOS_DB` env var.

**14 tables:** domains, concepts, morphisms, evidence, derivations, programs, program_tests, tasks, task_results, analogies, category_fingerprints, morphism_dependencies.

The `morphism_dependencies` table is a forward index: (premise_id → derived_id). Belief propagation uses it for O(k) lookup instead of scanning all morphisms.

### CRITICAL: add_morphism signature

```python
# CORRECT — label is the SECOND argument
store.add_morphism(domain_id, "label", "source", "target", rel_type="is-a")

# WRONG — sets label="source", source="target", which creates garbage
store.add_morphism(domain_id, "source", "target", "is-a")
```

### Belief propagation

When `add_evidence(morphism_id, ...)` is called:
1. Bayesian update on the target morphism's truth degree
2. Look up all derived morphisms via `morphism_dependencies` (O(k))
3. Recompute truth degrees of all dependents recursively up to depth 10

## Layer 1 — Heyting Truth

`engine/topos.py` — `TruthValue(degree: float, modality: Modality)`

**Seven modalities (weakest to strongest):**
`IMPOSSIBLE < UNDETERMINED < COUNTERFACTUAL < POSSIBLE < PROBABLE < ACTUAL < NECESSARY`

**Heyting algebra operations:**
- Meet (∧): `min(d1, d2)`, weaker modality
- Join (∨): `max(d1, d2)`, stronger modality
- Implies (→): Gödel — `1.0` if `d1 ≤ d2`, else `d2`
- Negate (¬): `1 - degree`, inverted modality

**CRITICAL:** Double-negation elimination intentionally fails.
`tv.negate().negate() ≠ tv` for UNDETERMINED values.
This is correct — genuine epistemic indeterminacy is not resolvable by logic.

## Layer 2 — Proof Kernel

`engine/kernel.py` — `ProofTerm(rule, premises, metadata)`

Rules: `axiom | transitivity | composition | auto_compose | analogy | speculation | evidence`

**check_proof(morphism_id):** validates derivation chain structurally. Does NOT validate semantic correctness.

**normalize_proof_term(morphism_id):** canonical form via recursive tree traversal.
`"transitivity(axiom(whale→mammal), axiom(mammal→warm))"` — same proof = same string.

**extract_common_core(domain_id_1, domain_id_2):** categorical pullback.
Returns a new domain containing the abstract structure shared by both inputs.

## Layer 3 — Analogy Engine

`engine/scale.py` — `find_analogies_csp(source, target, ...)`

**Algorithm:**
1. WL fingerprint prefilter (O(n)) — screen incompatible targets before search
2. AC-3 arc consistency — propagate constraints, prune impossible assignments
3. Most-constrained-variable ordering
4. Backtracking with symmetry breaking
5. Semantic rescoring with truth-degree correspondence

**Returns:** `list[dict]` with keys `object_map, score, structural_score, semantic_score`

`AnalogyMemory` (`engine/learning.py`) stores discovered analogies in the `analogies` table and tracks confirmations/contradictions over time.

## Layer 4 — Topology Engine

`engine/topology.py` (1,956 lines) — 12 engines.

**Entry point:** `compute_topology_report(store, domain_name, max_dim=3, t_norm='godel')`

### CategorySnapshot

```python
snap = CategorySnapshot.from_store(store, "biology")
# snap.objects, snap.hom, snap.best_hom, snap.obj_index
```

Load once into memory. **Never** query SQLite inside topology engine loops.

### CRITICAL: GF(2) rank

```python
# WRONG — real rank, wrong Betti numbers
rank = np.linalg.matrix_rank(boundary_matrix % 2)

# CORRECT — Gaussian elimination over GF(2)
rank = _rank_gf2(boundary_matrix)
```

Triangle (3 verts, 3 edges): real rank=3 → β₀=0 (wrong). GF(2) rank=2 → β₀=1 (correct).

### CRITICAL: GUDHI filtration

```python
st = nerve.to_gudhi_simplex_tree()
st.make_filtration_non_decreasing()   # REQUIRED before compute_persistence
st.compute_persistence()
```

Always call `make_filtration_non_decreasing()` first. GUDHI produces wrong results without it.

### Filtration convention

`filtration_value = 1 - truth_degree`

Higher truth = smaller filtration value = earlier entry into the complex.
This means: as we lower confidence threshold, more morphisms appear.

### Nerve dimension cap

Default `max_dim=3`. Simplices grow as O(M^k/k!).
For categories with >100 dense morphisms, use `max_dim=2`.

## Layers 5 & 6 — Server and UI

`server.py` — FastAPI, 64 endpoints, Swagger at `/docs`
Run: `uvicorn server:app --reload --port 8000`

`morphos-app.jsx` — React SPA, 10 tabs, no build step.

**JSX balance check (run after any UI edit):**
```bash
node --input-type=module -e "
import fs from 'fs';
const s = fs.readFileSync('morphos-app.jsx','utf8');
let b=0,p=0;
for(const c of s){if(c==='{')b++;if(c==='}')b--;if(c==='(')p++;if(c===')')p--;}
console.log('Brace balance:', b, '(want 0)');
console.log('Paren balance:', p, '(want 0)');
"
```

## Performance

| Operation | Complexity | Practical |
|-----------|-----------|-----------|
| CategorySnapshot load | O(n+m) | <100ms for 5000 morphisms |
| Isomorphism detection | O(m²) | <1s for 5000 morphisms |
| CSP analogy search | O(n! worst) | WL prefilter makes common case fast |
| Nerve construction | O(Σ\|N_k\|) | ~500ms for n=100, m=1000, max_dim=3 |
| GF(2) homology | O(\|N_n\|³) | <1s for \|N₂\| < 1000 |
| GUDHI persistence | O(s³) worst | <2s for 5000 simplices |
| Fundamental groupoid | O(n+m·α(n)) | <50ms for n=500 |

## Scalability Limits (honest numbers)

These are the ranges the 190 tests run across. They are measurements, not estimates.

| Category size | Analogy search | Topology (max_dim=3) |
|---|---|---|
| < 50 objects, < 200 morphisms | < 1s (typical) | < 500ms |
| 50–150 objects, < 1000 morphisms | 1–10s (WL prefilter helps) | 1–3s |
| > 150 objects, dense morphisms | Timeout risk | Use max_dim=2 |

**When the CSP times out**, the engine falls back to cosine similarity on concept label embeddings — approximate structural matching rather than exact functor search. The fallback is always attempted; results are scored lower to indicate approximation.

**When the nerve is too large**, reduce `max_dim`. A category with 200 objects and 1000 morphisms has ~166M potential 3-simplices before filtering — use `max_dim=2` for anything dense above 100 objects.

## OS Kernel Framing

See [REASONING_OS.md](./REASONING_OS.md) for the complete treatment. The short version for contributors:

- **Adding a data source?** → implement a driver in `engine/` (adapter pattern, produce `Category` objects)
- **Adding a reasoning algorithm?** → add to `engine/`, register a task type in `TASK_TYPES`, add an API endpoint
- **Adding a user-facing feature?** → work in user space (UI, CLI), keep reasoning logic in `engine/`
- **Adding a reasoning program?** → register with `TaskScheduler.register_handler()` so it submits as a task
