"""
examples/solar_system_vs_atom.py

The classic analogy: solar system ↔ atomic structure.
Demonstrates MORPHOS finding a structural correspondence between two domains
using the CSP analogy engine — without any hard-coded mapping.

Run:
    cd /path/to/morphos
    python3 examples/solar_system_vs_atom.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.kernel import ReasoningStore
from engine.categories import Category, Morphism
from engine.scale import find_analogies_csp
from engine.topology import compute_topology_report

# ── Build two domains in a temporary in-memory database ─────────────────────

store = ReasoningStore(":memory:")

# ── Domain 1: Solar System ───────────────────────────────────────────────────

solar_id = store.create_domain("solar_system", "Newtonian solar system model")

for concept in ["sun", "planet", "moon", "gravity", "orbit", "mass", "distance"]:
    store.add_concept(solar_id, concept)

solar_morphisms = [
    ("sun-has-mass",         "sun",     "mass",     "has-property",  1.0),
    ("planet-orbits-sun",    "planet",  "sun",      "orbits",        1.0),
    ("moon-orbits-planet",   "moon",    "planet",   "orbits",        1.0),
    ("gravity-causes-orbit", "gravity", "orbit",    "causes",        1.0),
    ("mass-produces-gravity","mass",    "gravity",  "produces",      0.95),
    ("sun-is-center",        "sun",     "planet",   "attracts",      1.0),
    ("planet-has-mass",      "planet",  "mass",     "has-property",  1.0),
    ("orbit-depends-distance","orbit",  "distance", "depends-on",    0.9),
]

for label, src, tgt, rel, td in solar_morphisms:
    store.add_morphism(solar_id, label, src, tgt, rel_type=rel, truth_degree=td)

# ── Domain 2: Atomic Structure ───────────────────────────────────────────────

atom_id = store.create_domain("atomic_structure", "Bohr model of the atom")

for concept in ["nucleus", "electron", "neutron", "electrostatic_force", "orbital", "charge", "radius"]:
    store.add_concept(atom_id, concept)

atom_morphisms = [
    ("nucleus-has-charge",      "nucleus",            "charge",            "has-property",  1.0),
    ("electron-orbits-nucleus", "electron",           "nucleus",           "orbits",        1.0),
    ("neutron-in-nucleus",      "neutron",            "nucleus",           "part-of",       1.0),
    ("eforce-causes-orbital",   "electrostatic_force","orbital",           "causes",        1.0),
    ("charge-produces-eforce",  "charge",             "electrostatic_force","produces",     0.95),
    ("nucleus-attracts-electron","nucleus",           "electron",          "attracts",      1.0),
    ("electron-has-charge",     "electron",           "charge",            "has-property",  1.0),
    ("orbital-depends-radius",  "orbital",            "radius",            "depends-on",    0.9),
]

for label, src, tgt, rel, td in atom_morphisms:
    store.add_morphism(atom_id, label, src, tgt, rel_type=rel, truth_degree=td)

# ── Build Category objects for the CSP engine ────────────────────────────────

def domain_to_category(store, domain_id, name):
    import uuid
    concepts = store.get_concepts(domain_id)
    morphisms_raw = store.get_morphisms(domain_id)
    objects = [c["label"] for c in concepts]
    morphisms = []
    for m in morphisms_raw:
        if not m.get("is_identity"):
            morphisms.append(Morphism(
                id=m.get("id", str(uuid.uuid4())),
                label=m["label"],
                source=m["source_label"],
                target=m["target_label"],
                rel_type=m["rel_type"],
                value=m.get("truth_degree", 1.0),
            ))
    return Category(name=name, objects=objects, morphisms=morphisms)

solar_cat = domain_to_category(store, solar_id, "solar_system")
atom_cat  = domain_to_category(store, atom_id,  "atomic_structure")

# ── Run analogy search ────────────────────────────────────────────────────────

print("\n" + "="*60)
print("  MORPHOS — Solar System ↔ Atomic Structure")
print("="*60)
print(f"\nSource: {len(solar_cat.objects)} objects, {len(solar_cat.morphisms)} morphisms")
print(f"Target: {len(atom_cat.objects)} objects,  {len(atom_cat.morphisms)} morphisms")
print("\nSearching for structural analogies (functors)...\n")

analogies = find_analogies_csp(solar_cat, atom_cat, max_results=3)

if not analogies:
    print("No analogies found.")
    sys.exit(1)

print(f"Found {len(analogies)} analogy map(s).\n")

best = analogies[0]
print(f"Best analogy  (score: {best['score']:.3f})")
print("-"*40)
for src_obj, tgt_obj in sorted(best["object_map"].items()):
    arrow = "→"
    print(f"  {src_obj:<22} {arrow}  {tgt_obj}")

# ── Compute topology of both domains ─────────────────────────────────────────

print("\n" + "="*60)
print("  Topology")
print("="*60)

for domain_name in ["solar_system", "atomic_structure"]:
    report = compute_topology_report(store, domain_name, max_dim=2)
    hom    = report.get("homology", {})
    fg     = report.get("fundamental_groupoid", {})
    betti  = hom.get("betti_numbers", {})
    print(f"\n{domain_name}:")
    print(f"  Homotopy type : {fg.get('homotopy_type', 'unknown')}")
    print(f"  Components π₀ : {fg.get('n_components', '?')}")
    print(f"  Cycles     π₁ : {fg.get('pi1_rank', '?')}")
    print(f"  β₀ β₁ β₂     : {betti.get(0,'?')}  {betti.get(1,'?')}  {betti.get(2,'?')}")

# ── Topological comparison ────────────────────────────────────────────────────

from engine.topology import CategorySnapshot, compare_domains

snap_solar = CategorySnapshot.from_store(store, "solar_system")
snap_atom  = CategorySnapshot.from_store(store, "atomic_structure")

comparison = compare_domains(snap_solar, snap_atom, max_dim=2)

print("\n" + "="*60)
print("  Topological Distance Between Domains")
print("="*60)
for k, v in comparison.items():
    if k != "interpretation":
        try:
            print(f"  {k:<30} {float(v):.4f}")
        except (TypeError, ValueError):
            print(f"  {k:<30} {v}")
print(f"\n  {comparison.get('interpretation', '')}")

print("\n" + "="*60)
print("  Done.")
print("="*60 + "\n")
