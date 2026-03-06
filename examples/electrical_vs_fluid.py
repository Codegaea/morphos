"""
examples/electrical_vs_fluid.py

The Ohm's law / hydraulic analogy:
  voltage   ↔ pressure
  current   ↔ flow rate
  resistance ↔ pipe resistance

Demonstrates MORPHOS finding the classical physics analogy structurally,
without any domain knowledge or hard-coded mapping.

Run:
    python examples/electrical_vs_fluid.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from engine.kernel import ReasoningStore
from engine.categories import Category, Morphism
from engine.scale import find_analogies_csp
from engine.topology import compute_topology_report, CategorySnapshot, compare_domains

store = ReasoningStore(":memory:")

# ── Electrical circuit domain ─────────────────────────────────────────────────

elec_id = store.create_domain("electrical_circuit", "Ohm's law circuit model")
for concept in ["voltage", "current", "resistance", "power", "ground"]:
    store.add_concept(elec_id, concept)

for label, src, tgt, rel, td in [
    ("v-drives-i",       "voltage",    "current",    "drives",       1.0),
    ("r-limits-i",       "resistance", "current",    "limits",       1.0),
    ("i-produces-p",     "current",    "power",      "produces",     0.9),
    ("v-across-r",       "voltage",    "resistance", "exists-across",1.0),
    ("i-flows-to-ground","current",    "ground",     "flows-to",     1.0),
]:
    store.add_morphism(elec_id, label, src, tgt, rel_type=rel, truth_degree=td)

# ── Fluid system domain ───────────────────────────────────────────────────────

fluid_id = store.create_domain("fluid_system", "Hydraulic pipe model")
for concept in ["pressure", "flow", "pipe_resistance", "work", "reservoir"]:
    store.add_concept(fluid_id, concept)

for label, src, tgt, rel, td in [
    ("p-drives-f",      "pressure",       "flow",           "drives",       1.0),
    ("pr-limits-f",     "pipe_resistance","flow",           "limits",       1.0),
    ("f-produces-w",    "flow",           "work",           "produces",     0.9),
    ("p-across-pr",     "pressure",       "pipe_resistance","exists-across",1.0),
    ("f-to-reservoir",  "flow",           "reservoir",      "flows-to",     1.0),
]:
    store.add_morphism(fluid_id, label, src, tgt, rel_type=rel, truth_degree=td)

# ── Build Category objects ────────────────────────────────────────────────────

def to_category(store, domain_id, name):
    concepts = store.get_concepts(domain_id)
    morphs   = store.get_morphisms(domain_id)
    objects  = [c["label"] for c in concepts]
    morphisms = [
        Morphism(
            id=m.get("id", str(uuid.uuid4())),
            label=m["label"],
            source=m["source_label"],
            target=m["target_label"],
            rel_type=m["rel_type"],
            value=m.get("truth_degree", 1.0),
        )
        for m in morphs if not m.get("is_identity")
    ]
    return Category(name=name, objects=objects, morphisms=morphisms)

elec_cat  = to_category(store, elec_id,  "electrical_circuit")
fluid_cat = to_category(store, fluid_id, "fluid_system")

# ── Search ────────────────────────────────────────────────────────────────────

print("\n" + "="*55)
print("  MORPHOS — Electrical Circuit ↔ Fluid System")
print("="*55)
print(f"\nSource: {len(elec_cat.objects)} objects, {len(elec_cat.morphisms)} morphisms")
print(f"Target: {len(fluid_cat.objects)} objects, {len(fluid_cat.morphisms)} morphisms")
print("\nSearching for structural analogy...\n")

results = find_analogies_csp(elec_cat, fluid_cat, max_results=3)

if not results:
    print("No analogy found.")
    sys.exit(1)

best = results[0]
print(f"Found {len(results)} analogy map(s). Best score: {best['score']:.3f}\n")
print("  electrical_circuit     →   fluid_system")
print("  " + "-"*44)
for src, tgt in sorted(best["object_map"].items()):
    print(f"  {src:<22} →   {tgt}")

# ── Topology ──────────────────────────────────────────────────────────────────

print("\n" + "="*55)
print("  Topology")
print("="*55)
for domain_name in ["electrical_circuit", "fluid_system"]:
    r  = compute_topology_report(store, domain_name, max_dim=2)
    fg = r.get("fundamental_groupoid", {})
    h  = r.get("homology", {}).get("betti_numbers", {})
    print(f"\n{domain_name}:")
    print(f"  Homotopy type : {fg.get('homotopy_type', '?')}")
    print(f"  β₀  β₁        : {h.get(0,'?')}  {h.get(1,'?')}")

snap1 = CategorySnapshot.from_store(store, "electrical_circuit")
snap2 = CategorySnapshot.from_store(store, "fluid_system")
cmp   = compare_domains(snap1, snap2, max_dim=2)
bd    = cmp.get("bottleneck_distances", {})
print(f"\nBottleneck distance (dim 0): {bd.get('bottleneck_dim0', '?')}")
print(f"Interpretation: {cmp.get('interpretation', '')}")

print("\n" + "="*55)
print("  Done.")
print("="*55 + "\n")
