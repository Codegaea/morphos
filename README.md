<div align="center">

# MORPHOS

**A persistent probabilistic categorical reasoning engine.**

*Every piece of knowledge is a morphism. Every morphism is accountable.*

[![Tests](https://github.com/Codegaea/morphos/actions/workflows/tests.yml/badge.svg)](https://github.com/Codegaea/morphos/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-22863a?style=flat-square)](./LICENSE)
[![Math](https://img.shields.io/badge/math-enriched%20category%20theory-7c3aed?style=flat-square)](#mathematical-foundation)

[Overview](#overview) · [Quickstart](#quickstart) · [Architecture](#architecture) · [What's Built](#whats-built) · [API](#api-reference) · [Contributing](#contributing) · [Math](#mathematical-foundation)

</div>

---

## Overview

MORPHOS is a knowledge reasoning engine built on enriched category theory. It treats knowledge as a mathematical structure:

- **Concepts** are objects in a category
- **Relationships** are typed morphisms with proof terms and continuous truth degrees
- **Analogies** are functors — structure-preserving maps between categories
- **Belief revision** is Bayesian updating on a Heyting algebra of truth values
- **Knowledge topology** is the persistent homology of a filtered nerve complex

This is not a vector database, not a rule engine, and not a language model. It is a proof-carrying, topologically-aware reasoning substrate where every claim is traceable to its source, every inference is checkable, and the structural shape of what you know is a measurable mathematical object.

**What makes this a category, not just a labeled graph:** every domain stores explicit identity morphisms, enforces typed composition rules so that hom(A,B) sets are well-defined, and checks the associativity and unit laws. The `check_proof` system validates that every derivation respects these axioms — a plain graph has none of this structure.

### The core demonstration

```bash
python examples/solar_system_vs_atom.py
```

```
MORPHOS — Solar System ↔ Atomic Structure

Source: 7 objects, 8 morphisms
Target: 7 objects, 8 morphisms

Searching for structural analogies (functors)...

Found 1 analogy map(s).

Best analogy  (score: 0.820)
----------------------------------------
  distance               →  radius
  gravity                →  electrostatic_force
  mass                   →  charge
  moon                   →  neutron
  orbit                  →  orbital
  planet                 →  nucleus
  sun                    →  electron

Topology
  solar_system:     homotopy_type=circle (S¹)   β₀=1  β₁=0
  atomic_structure: homotopy_type=circle (S¹)   β₀=1  β₁=0

Topological distance: 0.0000
→ Topologically nearly identical — very similar structural connectivity
```

The engine found the analogy without being told the mapping. It also computed that the two domains are topologically identical — same shape, confirmed from two different angles.

A second example — the classical Ohm's law / hydraulic analogy:

```bash
python examples/electrical_vs_fluid.py
```

```
  electrical_circuit     →   fluid_system
  -------------------------------------------
  current                →   flow
  ground                 →   reservoir
  power                  →   work
  resistance             →   pipe_resistance
  voltage                →   pressure

  Both: homotopy_type=circle (S¹)   bottleneck distance: 0.0
```

Same structural result: topologically identical domains, analogy found without any domain knowledge encoded.

---

## Why This Exists

| System | Expressive | Uncertain | Explainable | Structural |
|---|---|---|---|---|
| Theorem provers | ✅ | ❌ | ✅ | ❌ |
| Knowledge graphs | partial | ❌ | partial | ❌ |
| Vector databases | ❌ | partial | ❌ | ❌ |
| Language models | ❌ | partial | ❌ | ❌ |
| **MORPHOS** | ✅ | ✅ | ✅ | ✅ |

Most systems make a hard tradeoff across these four properties. MORPHOS tries to hold all four, with the mathematical framework doing the heavy lifting.

---

## Quickstart

### Requirements

Python 3.12+. No Docker. No cloud dependencies.

### Install

```bash
git clone https://github.com/Codegaea/morphos.git
cd morphos
pip install -r requirements.txt
```

### Verify

```bash
python -m pytest tests/ -q
# → 190 passed

python examples/solar_system_vs_atom.py
# → analogy + topology output
```

### Run the server

```bash
uvicorn server:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

### Your first domain

```python
from engine.kernel import ReasoningStore
from engine.topology import compute_topology_report

store = ReasoningStore("my_knowledge.db")
domain_id = store.create_domain("biology", "Biological taxonomy")

# Add morphisms — the core unit of MORPHOS
store.add_morphism(domain_id, "whale→mammal",  "whale",  "mammal",
                   rel_type="is-a",    truth_degree=1.0)
store.add_morphism(domain_id, "mammal→warm",   "mammal", "warm-blooded",
                   rel_type="implies", truth_degree=1.0)

# Derive a fact with an explicit proof
store.add_derived_morphism(domain_id, "whale→warm", "whale", "warm-blooded",
                            rule="transitivity",
                            premises=["whale→mammal", "mammal→warm"])

# Check the proof
store.check_proof("whale→warm")
# → {"valid": True, "rule": "transitivity", "premises": [...]}

# Submit evidence and watch belief propagate
store.add_evidence("whale→mammal", likelihood_if_true=0.99, likelihood_if_false=0.01)

# Compute topology
report = compute_topology_report(store, "biology")
print(report["fundamental_groupoid"]["homotopy_type"])  # "contractible"
print(report["homology"]["betti_numbers"])              # {0: 1, 1: 0, 2: 0}
```

---

## Architecture

**Unified mathematical framework:** all six layers are grounded in a single structure — categories enriched over the quantale **Q = ([0,1], ≤, min, 1)**. The Heyting truth layer is the algebra on Q. The proof kernel enforces the enrichment axioms. The analogy engine searches for Q-enriched functors. The topology engine computes the persistent homology of the enriched nerve. Nothing is bolted on; the mathematics connects end-to-end.

**What "reasoning OS" means concretely:** the kernel schedules typed reasoning tasks, manages a persistent knowledge store that survives process restarts, and executes inference programs (stored functors) on demand. A task queue decouples slow operations (analogy search, topology) from interactive queries. Programs are versioned, testable, and reinforced by evidence — closer to software artifacts than query results. The mapping to OS concepts is precise and corresponds to working code — see [docs/REASONING_OS.md](./docs/REASONING_OS.md) for the full architecture-level treatment.

| OS Component | MORPHOS Component |
|---|---|
| Kernel | `engine/kernel.py` — ReasoningStore + TaskScheduler |
| Filesystem | SQLite persistent store (14 tables) |
| Memory | `CategorySnapshot` — loaded on demand, released after use |
| Processes | `tasks` table — pending → running → completed |
| Executables | `programs` table — versioned, testable stored functors |
| Scheduler | `TaskScheduler.submit()` / `execute()` / `run_next()` |
| System calls | REST API (64 endpoints) + CLI |
| Device drivers | `engine/adapters.py`, dataset loaders, WordNet parsers |

```
┌────────────────────────────────────────────────────────────┐
│  Layer 6 — React UI              morphos-app.jsx           │
│  10 tabs · D3 visualizations · no build step               │
├────────────────────────────────────────────────────────────┤
│  Layer 5 — FastAPI Server         server.py                │
│  64 REST endpoints · task queue · Swagger at /docs         │
├────────────────────────────────────────────────────────────┤
│  Layer 4 — Topology Engine        engine/topology.py       │
│  12 engines · GUDHI · persistent homology · GF(2) rank     │
├────────────────────────────────────────────────────────────┤
│  Layer 3 — Analogy Engine         engine/scale.py          │
│  CSP + AC-3 · WL fingerprints · AnalogyMemory              │
├────────────────────────────────────────────────────────────┤
│  Layer 2 — Proof Kernel           engine/kernel.py         │
│  ProofTerm · check_proof · normalize · belief propagation  │
├────────────────────────────────────────────────────────────┤
│  Layer 1 — Heyting Truth          engine/topos.py          │
│  Gödel algebra · 7 modalities · ¬¬p ≠ p by design         │
├────────────────────────────────────────────────────────────┤
│  Layer 0 — Persistent Store       SQLite (WAL)             │
│  14 tables · proof traces · dependency index               │
└────────────────────────────────────────────────────────────┘
```

| File | Lines | Purpose |
|------|-------|---------|
| `engine/kernel.py` | 1,548 | Store, proof system, belief propagation |
| `engine/topology.py` | 1,956 | 12 topology engines |
| `engine/scale.py` | 1,175 | CSP analogy search, AnalogyMemory |
| `engine/topos.py` | 495 | Heyting algebra, truth values |
| `engine/learning.py` | 715 | Analogy program storage and tracking |
| `server.py` | 1,121 | FastAPI — 64 endpoints |
| `morphos-app.jsx` | 1,403 | React UI — 10 tabs |

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the full walkthrough including known gotchas.

---

## What's Built

### Truth System

Every morphism carries a `TruthValue` — a continuous degree in [0,1] and a modal qualifier.

**Seven modalities:** `NECESSARY · ACTUAL · PROBABLE · POSSIBLE · COUNTERFACTUAL · UNDETERMINED · IMPOSSIBLE`

The truth layer implements a **Gödel-style Heyting algebra over [0,1]** with four defined operations: meet (∧ = min), join (∨ = max), Gödel implication (p → q = 1 if p ≤ q, else q), and pseudo-complement (¬p = p → 0). These satisfy the Heyting algebra axioms — in particular, the algebra is not Boolean. Double-negation fails: `¬¬p ≠ p` for `UNDETERMINED` values. This is not a bug — it is the formal expression of genuine epistemic indeterminacy that classical two-valued logic cannot represent.

### Proof System

```python
# Structured proof terms — every derived fact is traceable
store.check_proof(morphism_id)
# → {"valid": True, "rule": "transitivity", "premises": [...]}

store.normalize_proof_term(morphism_id)
# → "transitivity(axiom(whale→mammal), axiom(mammal→warm))"

# Categorical pullback — extract shared structure from two domains
store.extract_common_core(domain_id_1, domain_id_2)
# → new domain with abstract morphisms common to both
```

**On evidence-driven inference:** `add_evidence(morphism_id, likelihood_if_true, likelihood_if_false)` applies Bayes' rule directly to the `truth_degree` of the named morphism. The updated degree is then propagated forward through the `morphism_dependencies` index — every morphism derived from this one (via transitivity, composition, or analogy) has its truth degree recomputed in O(k) where k is the number of dependents. This means belief revision is local by default but cascades correctly through derivation chains. What it does *not* do: it treats each evidence item as independent (no correlation model), and it does not propagate backwards to revise premises. Both are known limitations.

### Analogy Engine

```python
from engine.scale import find_analogies_csp

analogies = find_analogies_csp(source_category, target_category, max_results=5)
# Returns ranked list of object maps with scores
# Uses AC-3 constraint propagation + WL fingerprint prefilter
```

Functor search over arbitrary categories is combinatorially explosive. MORPHOS controls this with two layers: first, a **Weisfeiler-Lehman graph fingerprint** screens out structurally incompatible targets in O(n) before any search begins; second, **AC-3 arc consistency propagation** prunes the candidate space before backtracking, reducing the effective branching factor dramatically. The result is that most common analogy searches complete in under a second. Dense categories with more than ~150 objects may still time out — this is an acknowledged limitation and an open problem.

### Topology Engine (12 engines)

```python
from engine.topology import *

snap = CategorySnapshot.from_store(store, "biology")

# Isomorphism structure
IsomorphismEngine(snap).iso_degree("A", "B")          # ∈ [0, 1]
IsomorphismEngine(snap).isomorphism_classes(0.9)

# Homology — GF(2), not reals
HomologyEngine(NerveComplex(snap)).betti_numbers()    # {0: 1, 1: 0}

# Persistent homology
PersistentHomologyEngine(NerveComplex(snap)).compute()

# Fundamental groupoid
FundamentalGroupoid(snap).compute()
# → {homotopy_type: "contractible", n_components: 1, pi1_rank: 0}

# Classify a functor: full? faithful? equivalence?
FunctorClassifier(snap_C, snap_D, object_map).classify()

# Check adjunction F ⊣ G
AdjunctionDetector(snap_C, snap_D, F_map, G_map).compute()

# Compare two domains by topological distance
compare_domains(snap1, snap2)
# → {bottleneck_dim0: 0.0, interpretation: "topologically identical"}
```

**On the nerve construction:** MORPHOS builds the categorical nerve — not a clique complex or Vietoris-Rips complex. A k-simplex corresponds to a composable chain of k morphisms (A₀→A₁→...→A_k) where the direct edge A₀→A_k also exists, filtered by the minimum truth degree along the chain. This is the standard categorical nerve construction, not graph-theoretic approximation. Simplex count grows as O(M^k/k!), so the default cap is dimension 3; for dense categories, dimension 2 is recommended.

---

## API Reference

64 REST endpoints. Swagger UI at `http://localhost:8000/docs`.

### Topology (12 endpoints)

```
POST /api/topology/report                        Full report — all engines
GET  /api/topology/{domain}/isomorphisms         Graded iso classes
GET  /api/topology/{domain}/homology             Betti numbers, Euler characteristic
POST /api/topology/persistent-homology           GUDHI persistence diagram
POST /api/topology/compare                       Bottleneck distance between domains
GET  /api/topology/{domain}/fundamental-groupoid π₀, π₁ rank, homotopy type
GET  /api/topology/{domain}/yoneda               Yoneda matrix and rank
GET  /api/topology/{domain}/limits               Terminal, initial, products, pullbacks
POST /api/topology/classify-functor              Full/faithful/equivalence
POST /api/topology/check-adjunction              Graded adjunction degree F ⊣ G
POST /api/topology/homotopy-classes              Collapse analogies by nat. isomorphism
GET  /api/topology/{domain}/metric-enrichment    Lawvere metric axiom check
```

### Core

```
POST /api/domains                    Create domain
POST /api/domains/{id}/morphisms     Add morphism
POST /api/evidence                   Submit evidence → belief propagation
POST /api/search                     CSP analogy search
POST /api/pipeline                   7-step guided analogy workflow
GET  /api/proof/{id}/check           Validate proof chain
GET  /api/proof/{id}/normalize       Canonical proof term
POST /api/extract/common-core        Categorical pullback of two domains
POST /api/query                      Natural language / DSL query
```

---

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Persistent store (SQLite, 14 tables) | ✅ Complete | WAL, dependency index |
| Heyting truth layer (7 modalities) | ✅ Complete | Bayesian updating |
| Proof kernel | ✅ Complete | check, normalize, extract_common_core |
| CSP analogy engine | ✅ Complete | WL prefilter, AC-3, embedding fallback |
| Topology engine (12 engines) | ✅ Complete | GUDHI, correct GF(2) homology |
| FastAPI server (64 endpoints) | ✅ Complete | Full Swagger docs |
| React UI (10 tabs) | ✅ Complete | D3 visualizations, no build step |
| Test suite (190 tests) | ✅ Complete | 4 suites, 0 failures |
| **Knowledge ingestion pipeline** | 🔴 Not built | **Highest priority open problem** |
| Topology-guided reasoning | 🟡 Designed | Not yet implemented |
| Correlated belief propagation | 🟡 Planned | Independence assumption for now |

---

## Contributing

Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening a PR.

**Most needed:** A working ingestion pipeline for any structured data source — OWL ontologies, WordNet, Wikidata, or NLP-extracted relations. This is the single thing that would make the system usable for real research domains.

**Good first issues:** Look for the `good first issue` label.

**Non-negotiable rules:**
- `python -m pytest tests/ -q` must show 190+ passing
- GF(2) homology uses `_rank_gf2()` — never `np.linalg.matrix_rank`
- No SQL inside topology engine loops
- New functions need tests

---

## Intellectual Ancestry

MORPHOS is a direct descendant of **SME — the Structure-Mapping Engine** (Forbus & Gentner, 1986), which implemented Dedre Gentner's structure-mapping theory: that analogy is not surface similarity but *relational structure preservation*.

SME was correct. The question it left open was what formal mathematics makes structural preservation exact.

The answer is: **functors**. A functor F: C → D satisfies F(g∘f) = F(g)∘F(f) — it preserves composition. Gentner's systematicity principle (deeper, more compositionally coherent mappings score higher) is this law. SME's greedy structural consistency algorithm was always approximating functor search. MORPHOS makes it exact.

Three things MORPHOS adds that SME never had:

| | SME | MORPHOS |
|---|---|---|
| Truth model | Binary — relations hold or don't | Continuous in [0,1], Bayesian updates |
| Persistence | Runs once, returns a mapping | Full runtime — programs, provenance, derivation log |
| Global structure | Not analyzed | Persistent homology of the categorical nerve |

The fourth entry in that table — topology — is the genuinely new idea. Two domains with similar persistence diagrams are candidates for strong analogies. The solar system and atom example demonstrates this: both produce identical diagrams (circle S¹, bottleneck distance 0.0), which is a topological explanation of *why* that analogy works, not just evidence that it does.

See [docs/INTELLECTUAL_ANCESTRY.md](./docs/INTELLECTUAL_ANCESTRY.md) for the full lineage, including the Yoneda lemma as a theory of conceptual meaning, the precise divergences from Cyc / Wolfram / OpenCog, and the open questions the project has not yet answered.

---

## Mathematical Foundation

MORPHOS categories are enriched over **Q = ([0,1], ≤, min, 1)**. By Lawvere's 1973 theorem this is a generalized metric space: `d(A,B) = −log(hom(A,B))`. This single structure unifies all six layers: the Heyting algebra is the logic on Q, the proof kernel enforces the enrichment axioms, the analogy engine searches for Q-enriched functors, and the topology engine computes the persistent homology of the enriched nerve.

**What topology reveals that graph statistics don't:** standard graph metrics (degree distribution, clustering coefficient, diameter) are local. Persistent homology captures *global* relational cycles — loops that exist across the full morphism network at varying confidence thresholds. Two domains that look structurally different by local statistics can have identical persistence diagrams, which is exactly what happens in the solar system / atom example above: both produce a circle (S¹) with β₀=1, β₁=1, bottleneck distance 0.0. That topological equivalence is a structural fact about the *shape* of the relational cycles, not about individual nodes or edges. It provides a fast structural similarity test before committing to an expensive full functor search.

The filtered nerve `N_τ(C)` uses morphisms with `truth_degree ≥ τ`. As τ decreases, more morphisms enter and topological structure accumulates. Persistent homology tracks features across this filtration.

**Stability theorem** (Cohen-Steiner et al. 2007): small belief changes cause at most proportional changes to the persistence diagram. Belief revision is topologically stable.

See [docs/MATH.md](./docs/MATH.md) for full definitions with citations.

---

## Repository Structure

```
morphos/
├── engine/              # All 21 reasoning engine modules
├── tests/               # 190 tests across 9 test files
├── examples/
│   └── solar_system_vs_atom.py   # Working demo — run this first
├── docs/
│   ├── ARCHITECTURE.md         # Layer-by-layer technical walkthrough
│   ├── MATH.md                 # Mathematical definitions and references
│   ├── REASONING_OS.md         # OS kernel framing — precise component mapping
│   └── INTELLECTUAL_ANCESTRY.md # Lineage from Gentner/SME through category theory
├── .github/
│   ├── ISSUE_TEMPLATE/  # Bug, feature, math correction templates
│   └── workflows/       # CI — full test suite + example on every PR
├── server.py            # FastAPI — 64 endpoints
├── morphos-app.jsx      # React UI — 10 tabs, no build step
├── morphos_cli.py       # Command-line interface
├── requirements.txt
└── LICENSE              # MIT
```

---

## License

MIT — see [LICENSE](./LICENSE).

---

<div align="center">

**The substrate is built. The mathematics is sound. The implementation is correct.**

*What it becomes depends on who shows up.*

</div>
