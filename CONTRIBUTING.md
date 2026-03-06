# Contributing to MORPHOS

MORPHOS is an open research project. Contributions that deepen the mathematical rigor of the core are more valuable than those that add surface features.

---

## Before You Start

Read in order:

1. **README.md** — what MORPHOS is and why
2. **docs/ARCHITECTURE.md** — full layer-by-layer technical walkthrough
3. **docs/MATH.md** — the mathematical definitions everything is built on

Then run:

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
# Must show: 190 passed
python examples/solar_system_vs_atom.py
# Must complete without error
```

---

## What We Need Most

### Priority 1 — Knowledge Ingestion (highest impact)

The biggest gap. Every category must currently be built by hand. Even one working parser would unlock all the reasoning capabilities for real data.

- **OWL/OBO/SKOS → MORPHOS**: `owlready2` or `rdflib` parses ontology; `owl:ObjectProperty` → morphism; `rdfs:subClassOf` → is-a with truth_degree=1.0
- **WordNet bootstrap**: NLTK synsets as objects, lexical relations as morphisms; path similarity as truth degree
- **Wikidata SPARQL**: P31 (instance-of), P279 (subclass-of), P361 (part-of) as morphisms; filter by domain Q-code
- **NLP relation extraction**: spaCy + custom rel model → typed triples → morphisms with confidence as truth degree

### Priority 2 — Topology-Guided Reasoning

The topology layer computes invariants but does not influence reasoning.

- **Topology-guided CSP**: add a fitness term to analogy search that prefers functors preserving the source domain's persistence diagram
- **Anomaly detection**: morphisms whose removal changes Betti numbers significantly are structurally load-bearing — flag them
- **Hypothesis generation**: if a domain has a 1-cycle that topology suggests should close, propose the completing morphism

### Good first issues

Look for issues labeled `good first issue`. Each one has a concrete spec.

- Persistence diagram barcode visualization in the Topology tab
- Benchmark suite: analogy search time vs. category size/density
- Evidence correlation model (replace independence assumption)

---

## Development Rules

These are invariants, not preferences.

### 1. 190 tests must pass

```bash
python -m pytest tests/ -q
# → 190 passed, 0 failed
```

Never merge code that breaks this.

### 2. GF(2) rank computation

Homology uses `_rank_gf2()` in `engine/topology.py` — custom Gaussian elimination over GF(2).

**Never replace with `np.linalg.matrix_rank`** — it computes rank over the reals and gives wrong Betti numbers. This is documented in the code. Do not remove the comment.

### 3. No SQL inside topology loops

Load data into `CategorySnapshot` once. Never query SQLite inside the inner loops of topology engines.

### 4. JSON-serializable API responses

Convert all numpy types before returning: `.tolist()` for arrays, `float()` for scalars.

### 5. Tests before merge

Every new public function needs at least one test. Mathematical definition changes need a citation.

---

## Pull Request Process

1. Fork and branch from `main`: `feat/owl-importer`, `fix/gf2-rank`, `docs/math`
2. Write tests for all new code
3. Run `python -m pytest tests/ -q` — confirm 190+ pass
4. Run the example: `python examples/solar_system_vs_atom.py`
5. Open PR using the template — it will ask you to confirm the checklist

---

## Code Style

- **Python**: PEP 8, type hints on public functions, docstrings on classes
- **Mathematical notation**: use standard symbols in comments (∘, ⊗, ⊣, →, ≅)
- **Commits**: `feat(scope): description`, `fix(scope): description`, `math(scope): description`

---

## Questions

Open a Discussion. This is a research project — questions about the mathematics are as welcome as bug reports.
