# MORPHOS as a Reasoning Operating System

This document explains the architecture of MORPHOS through the lens of operating system design. The analogy is precise, not decorative — every mapping corresponds to working code.

---

## Why an OS Kernel Is the Right Frame

An operating system kernel exists to manage resources, execution, persistence, isolation, and communication on behalf of programs that cannot manage these things themselves.

MORPHOS manages the same concerns, but over knowledge structures and reasoning processes rather than CPU, memory, and disk.

| OS Component | MORPHOS Component | Implementation |
|---|---|---|
| Kernel | Reasoning runtime | `engine/kernel.py` — `ReasoningStore` + `TaskScheduler` |
| Filesystem | Persistent knowledge store | SQLite (WAL), 14 tables |
| Memory | In-memory category objects | `CategorySnapshot` — loaded from store on demand |
| Processes | Running reasoning jobs | `tasks` table — status: pending → running → completed |
| Executables | Stored reasoning programs | `programs` table — registered functors with versioning |
| Scheduler | Task priority queue | `TaskScheduler.submit()` / `execute()` / `run_next()` |
| System calls | REST API + CLI | `server.py` (64 endpoints), `morphos_cli.py` |
| Device drivers | Data adapters | `engine/adapters.py`, `engine/datasets.py`, WordNet parsers |
| User space | Client interfaces | React UI, CLI, API clients |
| Kernel space | Core engine | `engine/` — all reasoning algorithms |

This is not metaphor. Each row is a claim about code responsibilities that can be verified by reading the corresponding module.

---

## The Kernel

`engine/kernel.py` — `ReasoningStore` and `TaskScheduler`

### ReasoningStore (the kernel runtime)

The store is the root of the system. Every other component receives it as a dependency. It owns:

- The SQLite connection (WAL mode, foreign keys ON)
- All read/write access to the 14 knowledge tables
- The belief propagation mechanism (`morphism_dependencies` forward index)
- Proof term storage and validation
- Domain versioning (snapshots)

Nothing operates on persistent knowledge except through the store. There is no way to bypass it — this is intentional, for the same reason OS processes cannot bypass the kernel to access hardware.

### TaskScheduler (the process scheduler)

```python
class TaskScheduler:
    """
    Schedules and executes reasoning tasks.
    Each task produces artifacts (new morphisms, functors, evidence)
    that are recorded in the persistent store.
    """
    def submit(self, task_type: str, params: dict, priority: int = 0) -> str
    def execute(self, task_id: str) -> dict
    def run_next(self) -> dict
```

Built-in task types (analogous to kernel system services):

| Task type | Description |
|-----------|-------------|
| `compose` | Compute transitive compositions in a domain |
| `speculate` | Generate candidate morphisms |
| `map` | CSP analogy search between two domains |
| `learn` | Store and reinforce a discovered analogy |
| `infer` | Run typed inference (transitive closure, etc.) |
| `verify` | Check categorical laws (enrichment axioms) |
| `snapshot` | Create versioned snapshot of a domain |

New task types can be registered at runtime via `scheduler.register_handler(task_type, handler)` — analogous to loadable kernel modules.

---

## The Filesystem

`SQLite database` (default: `morphos.db`, configurable via `MORPHOS_DB`)

The persistent store is the knowledge filesystem. Every inference writes artifacts into it. Nothing is lost when the process restarts.

```
morphos.db
├── domains          ← named knowledge partitions (directories)
├── concepts         ← objects within a domain (inodes)
├── morphisms        ← typed weighted relationships (files with metadata)
├── evidence         ← observational records (provenance log)
├── derivations      ← proof traces (execution log)
├── programs         ← stored reasoning programs (executable registry)
├── program_tests    ← test assertions for programs (test suite)
├── tasks            ← reasoning job queue (process table)
├── task_results     ← task output artifacts
├── analogies        ← discovered analogy maps with tracking
├── category_fingerprints  ← WL structural hashes (index cache)
└── morphism_dependencies  ← forward propagation index (inode links)
```

The `morphism_dependencies` table is the key performance structure — it is the knowledge equivalent of filesystem hard links: a many-to-many index that makes forward propagation (belief revision cascading through derived facts) O(k) instead of O(n).

---

## Programs and Processes

In a standard OS: a **program** is an executable artifact on disk; a **process** is a running instance of that program.

MORPHOS makes the same distinction, and it matters for the same reasons.

### Programs (stored reasoning procedures)

A program is a registered functor — a stored, versioned, testable mapping between two domains.

```python
store.register_program(
    name="fluid_to_circuit",
    source_domain="fluid_system",
    target_domain="electrical_circuit",
    object_map={"pressure": "voltage", "flow": "current", ...},
    score=0.838
)
```

Programs live in the `programs` table. They have:
- A version number (incremented on update)
- A test suite (`program_tests` table)
- A reinforcement count (incremented each time the program produces a correct result)
- A contradiction count (decremented when evidence conflicts)

This is the difference between a reasoning system and a calculator. Programs accumulate confirmation over time; they are not ephemeral.

### Processes (running reasoning jobs)

A process is a task in the `tasks` table with a lifecycle:

```
pending → running → completed | failed
```

```python
tid = scheduler.submit("map", {
    "source_domain": "fluid_system",
    "target_domain": "electrical_circuit",
    "max_results": 5
}, priority=1)

result = scheduler.execute(tid)
# result is stored in tasks.result and returned
```

Long-running operations (topology, large CSP searches) are submitted as tasks rather than blocking the API. This is the same pattern an OS uses to handle long-running processes: don't block the scheduler; run asynchronously and store results.

---

## Memory Model

An OS loads programs from disk into RAM for execution, then writes results back.

MORPHOS does the same with knowledge:

```
SQLite (disk)
    ↓  from_store()
CategorySnapshot (RAM)
    ↓  reasoning algorithm
Result dict
    ↓  store_result()
SQLite (disk)
```

`CategorySnapshot` is the in-memory representation of a domain — all objects, morphisms, and hom-set values loaded into Python dicts for O(1) access. It is explicitly loaded before any topology or analogy algorithm runs, and explicitly discarded afterward. No reasoning algorithm queries SQLite during execution. This is not an optimization — it is a correctness requirement, because topology algorithms make thousands of hom-set lookups and SQLite latency per lookup would make them impractical.

---

## System Calls

In a POSIX system, user programs cross the user/kernel boundary through system calls.

In MORPHOS, clients cross the interface boundary through the REST API or CLI.

```
API call (POST /api/search)          ← user space
    ↓  server.py (FastAPI)
engine/scale.py (find_analogies_csp) ← kernel space
    ↓
engine/kernel.py (store results)
    ↓
SQLite (persist)
```

Every API endpoint is a named system call with typed parameters, a documented return type, and a guarantee that the result is persisted before the response is returned. The Swagger UI at `/docs` is the equivalent of a syscall reference manual.

---

## Device Drivers (Data Adapters)

An OS kernel cannot know about every storage device, so it defines a driver interface.

MORPHOS cannot know about every external knowledge source, so it defines an adapter interface:

| Adapter | External source | Produces |
|---------|-----------------|----------|
| `engine/adapters.py` | Generic JSON/dict categories | `Category` objects |
| `engine/datasets.py` | Built-in test corpora | `Category` objects |
| `engine/wordnet_parser.py` | NLTK WordNet | Concepts + is-a morphisms |
| `engine/deep_wordnet.py` | WordNet with depth/weight | Weighted concept graphs |
| `engine/linguistic_kb.py` | Linguistic knowledge bases | Typed semantic relations |

The driver interface contract is simple: produce a `Category` object (or call `store.add_morphism` directly), and the kernel handles persistence, indexing, and topology from there.

The largest open problem in the system — knowledge ingestion — is essentially a driver problem: no working general-purpose driver exists yet for unstructured text or arbitrary ontologies.

---

## User Space and Kernel Space

| Layer | Analogy | Components |
|-------|---------|------------|
| User space | Applications | React UI (`morphos-app.jsx`), CLI (`morphos_cli.py`), API clients |
| System call interface | POSIX / syscall table | REST API (`server.py`), CLI commands |
| Kernel space | Kernel modules | `engine/` — all reasoning algorithms |
| Hardware | Persistent storage | SQLite + filesystem |

**What this means for contributors:**

- If you are adding a new data source → write a driver in `engine/` following the adapter pattern
- If you are adding a new reasoning algorithm → add it to kernel space (`engine/`), expose it via a new API endpoint, add a task type to `TASK_TYPES`
- If you are adding a new user-facing feature → work in user space (UI, CLI), do not add reasoning logic there
- If you are adding a new program type → register it with `TaskScheduler.register_handler()` so it can be submitted as a task

---

## Why This Framing Is Useful

### It explains what "extensible" means concretely

When someone asks "can I add my own reasoning algorithm?" the answer is: yes, the same way you add a loadable kernel module. Implement the reasoning function, register a task handler, add an API endpoint. The persistence, scheduling, and monitoring infrastructure is already there.

### It explains why programs accumulate value over time

A program that has been confirmed 40 times and contradicted 3 times is more reliable than one confirmed 2 times and contradicted 0 times. The reinforcement model is the knowledge equivalent of a frequently-executed, well-tested binary. Programs get better with use.

### It explains the topology layer's role

Topology is not a feature — it is an introspection interface, like `/proc` in Linux. It allows you to query the structural state of the knowledge filesystem (Betti numbers, homotopy type, persistence diagram) without running any reasoning programs. It answers: "what shape is this knowledge domain in?" independently of any specific query.

### It points toward what comes next

An OS kernel can be extended with:
- Loadable modules → new reasoning algorithms as plugins
- Distributed filesystems → sharded knowledge stores across machines
- Process isolation → sandboxed reasoning with capability restrictions
- Inter-process communication → functors as message-passing channels between isolated domains
- Cgroups → resource quotas on CSP search time and nerve complexity

Each of these is a coherent next step, not a vague aspiration, precisely because the OS framing defines what the interfaces should look like.

---

## What MORPHOS Is Not

This framing also clarifies what the system is not.

It is **not a language model.** Language models have no persistent identity, no program store, no proof traces, and no topological structure. Every query is stateless. MORPHOS accumulates structure over time.

It is **not a knowledge graph database.** Knowledge graph databases store typed edges but do not enforce categorical axioms, do not carry proof terms, do not schedule reasoning tasks, and do not compute topological invariants. The graph is the data structure; MORPHOS is the runtime.

It is **not a theorem prover.** Theorem provers work over discrete, exact truth values in a fixed logical system. MORPHOS works over continuous truth degrees in a Heyting algebra, with Bayesian updates from evidence. It is probabilistic reasoning with proof accountability, not proof search.

It is **not SME.** The Structure-Mapping Engine (Forbus & Gentner, 1986) is the closest historical ancestor — it introduced the correct insight that analogy is relational structure preservation. MORPHOS is what SME becomes when you formalize that insight as category theory, add persistence, add uncertainty, and build a runtime around it rather than a standalone algorithm. See [docs/INTELLECTUAL_ANCESTRY.md](./INTELLECTUAL_ANCESTRY.md) for the precise account.

---

## Summary

MORPHOS is a **reasoning runtime** in the same sense that Linux is a process runtime: it manages resources (knowledge structures), schedules execution (reasoning tasks), provides persistent storage (the knowledge filesystem), enforces correctness invariants (categorical axioms, proof terms), and exposes a well-defined interface (REST API, CLI) to programs running above it.

The mathematical substrate — enriched category theory, Heyting algebra, persistent homology — is not an aesthetic choice. It is the formal specification of what the runtime guarantees: that composition is associative, that proof terms are verifiable, that topological invariants are stable under small belief changes, and that functor search finds structure-preserving maps rather than superficial similarity.

That combination — OS-style runtime accountability with category-theoretic correctness guarantees — is what makes MORPHOS unusual.
