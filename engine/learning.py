"""
MORPHOS Learning Engine — Phase 2

The engine remembers discovered analogies and uses them to predict new ones.

Architecture:
1. CategoryFingerprint: structural hash of a category for fast lookup
2. AnalogyMemory: persistent store of discovered analogies, indexed by fingerprint
3. MetaCategory: a category whose objects are categories and morphisms are analogies
4. Predictor: uses prior discoveries to guide new searches and predict unmapped structure
5. Reinforcement: Bayesian updating of analogy confidence as new evidence arrives

The key insight: if the engine discovers that A≅B and B≅C, it should
predict A≅C without being asked, and use the A≅B mapping to narrow
the search space for A→C. This is analogy-by-analogy — learning about
structural similarity from structural similarity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
import uuid
import json
import time

from .categories import Category, Morphism, create_category
from .scalable_search import (
    SignatureMatch, find_functors_scalable, _compute_signatures,
)
from .topos import (
    TruthValue, Modality, bayesian_update, compose_truth,
    actual, probable, possible, undetermined, TRUE,
)


# ══════════════════════════════════════════════════════════════
# 1. CATEGORY FINGERPRINT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CategoryFingerprint:
    """
    Structural fingerprint of a category for fast similarity lookup.

    Captures the "shape" of a category independent of object/morphism labels:
    - n_objects: number of objects
    - n_morphisms: number of user morphisms
    - degree_sequence: sorted tuple of (out_degree, in_degree) per object
    - n_rel_types: number of distinct relationship types
    - freq_distribution: sorted tuple of how many morphisms each type has
    - has_cycles: whether the category contains cycles
    - max_chain_length: longest non-repeating path
    """
    n_objects: int
    n_morphisms: int
    degree_sequence: tuple
    n_rel_types: int
    freq_distribution: tuple
    has_cycles: bool
    max_chain_length: int

    def similarity(self, other: CategoryFingerprint) -> float:
        """Compute similarity between two fingerprints. Returns 0-1."""
        if self == other:
            return 1.0

        # Size similarity
        size_sim = 1.0 - abs(self.n_objects - other.n_objects) / max(self.n_objects, other.n_objects, 1)
        morph_sim = 1.0 - abs(self.n_morphisms - other.n_morphisms) / max(self.n_morphisms, other.n_morphisms, 1)

        # Degree sequence similarity
        deg_sim = _sequence_similarity(self.degree_sequence, other.degree_sequence)

        # Relation type count similarity
        type_sim = 1.0 - abs(self.n_rel_types - other.n_rel_types) / max(self.n_rel_types, other.n_rel_types, 1)

        # Frequency distribution similarity
        freq_sim = _sequence_similarity(
            tuple((x,) for x in self.freq_distribution),
            tuple((x,) for x in other.freq_distribution),
        )

        # Cycle and chain similarity
        cycle_sim = 1.0 if self.has_cycles == other.has_cycles else 0.5
        chain_sim = 1.0 - abs(self.max_chain_length - other.max_chain_length) / max(self.max_chain_length, other.max_chain_length, 1)

        return (0.15 * size_sim + 0.15 * morph_sim + 0.25 * deg_sim +
                0.15 * type_sim + 0.10 * freq_sim + 0.10 * cycle_sim + 0.10 * chain_sim)


def fingerprint(cat: Category) -> CategoryFingerprint:
    """Compute the structural fingerprint of a category."""
    um = cat.user_morphisms()

    # Degree sequence
    degrees = []
    for obj in cat.objects:
        out_d = sum(1 for m in um if m.source == obj)
        in_d = sum(1 for m in um if m.target == obj)
        degrees.append((out_d, in_d))
    degrees.sort(reverse=True)

    # Relation type distribution (count how many types have each frequency)
    rel_counts = defaultdict(int)
    for m in um:
        rt = m.rel_type or m.label
        rel_counts[rt] += 1
    # Store sorted frequency distribution, not the type names
    freq_distribution = tuple(sorted(rel_counts.values(), reverse=True))
    n_rel_types = len(rel_counts)

    # Cycle detection (simple: check if any object can reach itself)
    has_cycles = False
    adj = defaultdict(set)
    for m in um:
        adj[m.source].add(m.target)

    for start in cat.objects:
        visited = set()
        stack = list(adj[start])
        while stack:
            node = stack.pop()
            if node == start:
                has_cycles = True
                break
            if node not in visited:
                visited.add(node)
                stack.extend(adj[node])
        if has_cycles:
            break

    # Max chain length (longest path without cycles)
    max_chain = 0
    for start in cat.objects:
        max_chain = max(max_chain, _longest_path(adj, start, set()))

    return CategoryFingerprint(
        n_objects=len(cat.objects),
        n_morphisms=len(um),
        degree_sequence=tuple(degrees),
        n_rel_types=n_rel_types,
        freq_distribution=freq_distribution,
        has_cycles=has_cycles,
        max_chain_length=max_chain,
    )


def _longest_path(adj, node, visited):
    """DFS to find longest path from node."""
    best = 0
    for neighbor in adj.get(node, []):
        if neighbor not in visited:
            visited.add(neighbor)
            best = max(best, 1 + _longest_path(adj, neighbor, visited))
            visited.discard(neighbor)
    return best


def _sequence_similarity(seq1, seq2):
    """Compare two sorted sequences element-wise."""
    if not seq1 and not seq2:
        return 1.0
    max_len = max(len(seq1), len(seq2))
    # Pad shorter sequence
    s1 = list(seq1) + [(0, 0)] * (max_len - len(seq1))
    s2 = list(seq2) + [(0, 0)] * (max_len - len(seq2))
    diffs = 0
    total = 0
    for a, b in zip(s1, s2):
        if isinstance(a, tuple) and isinstance(b, tuple):
            for x, y in zip(a, b):
                diffs += abs(x - y)
                total += max(abs(x), abs(y), 1)
        else:
            diffs += abs(a - b) if isinstance(a, (int, float)) else 0
            total += max(abs(a), abs(b), 1) if isinstance(a, (int, float)) else 1
    return 1.0 - (diffs / max(total, 1))


# ══════════════════════════════════════════════════════════════
# 2. DISCOVERED ANALOGY RECORD
# ══════════════════════════════════════════════════════════════

@dataclass
class DiscoveredAnalogy:
    """A discovered structural analogy between two categories."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_name: str = ""
    target_name: str = ""
    source_fingerprint: Optional[CategoryFingerprint] = None
    target_fingerprint: Optional[CategoryFingerprint] = None
    object_map: dict[str, str] = field(default_factory=dict)
    morphism_map: dict[str, str] = field(default_factory=dict)
    score: float = 0.0
    truth_value: TruthValue = field(default_factory=lambda: probable(0.5))
    discovered_at: float = field(default_factory=time.time)
    confirmations: int = 0
    contradictions: int = 0
    evidence: list[str] = field(default_factory=list)

    def confidence(self) -> float:
        """Current confidence combining score and truth value."""
        return self.score * self.truth_value.degree

    def reinforce(self, label: str, strength: float = 0.8):
        """Strengthen this analogy based on confirming evidence."""
        self.truth_value = bayesian_update(
            self.truth_value, label,
            likelihood_if_true=strength,
            likelihood_if_false=1.0 - strength,
        )
        self.confirmations += 1
        self.evidence.append(f"+{label}")

    def weaken(self, label: str, strength: float = 0.8):
        """Weaken this analogy based on contradicting evidence."""
        self.truth_value = bayesian_update(
            self.truth_value, label,
            likelihood_if_true=1.0 - strength,
            likelihood_if_false=strength,
        )
        self.contradictions += 1
        self.evidence.append(f"-{label}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_name,
            "target": self.target_name,
            "score": round(self.score, 4),
            "confidence": round(self.confidence(), 4),
            "truth_value": self.truth_value.label(),
            "object_map": self.object_map,
            "confirmations": self.confirmations,
            "contradictions": self.contradictions,
            "evidence_count": len(self.evidence),
        }


# ══════════════════════════════════════════════════════════════
# 3. ANALOGY MEMORY — Persistent store with fingerprint indexing
# ══════════════════════════════════════════════════════════════

class AnalogyMemory:
    """
    Persistent store of discovered analogies.

    Indexes analogies by category fingerprint for fast retrieval.
    When a ReasoningStore is provided all operations are backed by SQLite
    so discovered analogies survive session restarts.

    Supports:
    - Store a discovered analogy
    - Retrieve analogies involving a category (by fingerprint similarity)
    - Find transitive analogy chains (if A≅B and B≅C, predict A≅C)
    - Reinforce/weaken analogies based on new evidence
    - Export/import for persistence
    """

    def __init__(self, store=None):
        """
        Args:
            store: Optional ReasoningStore instance. When provided all
                   analogies and fingerprints are persisted to SQLite.
        """
        self._store = store  # ReasoningStore | None
        self.analogies: dict[str, DiscoveredAnalogy] = {}  # id -> analogy
        self.by_source: dict[str, list[str]] = defaultdict(list)  # name -> [analogy_ids]
        self.by_target: dict[str, list[str]] = defaultdict(list)
        self.fingerprints: dict[str, CategoryFingerprint] = {}  # cat_name -> fingerprint
        self._search_count = 0
        self._hit_count = 0

        # Hydrate from SQLite if a store was given
        if store is not None:
            self._load_from_store()

    # ── Private: SQLite hydration ──────────────────────────

    def _load_from_store(self):
        """Populate in-memory dicts from the persistent store."""
        from .topos import TruthValue, Modality

        # Load fingerprints
        for name, fp_dict in self._store.load_fingerprints().items():
            deg_seq = tuple(tuple(pair) if isinstance(pair, list) else pair
                            for pair in fp_dict["degree_sequence"])
            freq_dist = tuple(fp_dict["freq_distribution"])
            self.fingerprints[name] = CategoryFingerprint(
                n_objects=fp_dict["n_objects"],
                n_morphisms=fp_dict["n_morphisms"],
                degree_sequence=deg_seq,
                n_rel_types=fp_dict["n_rel_types"],
                freq_distribution=freq_dist,
                has_cycles=fp_dict["has_cycles"],
                max_chain_length=fp_dict["max_chain_length"],
            )

        # Load analogies
        for row in self._store.load_analogies():
            modality = Modality[row["truth_modality"]]
            tv = TruthValue(row["truth_degree"], modality)
            analogy = DiscoveredAnalogy(
                id=row["id"],
                source_name=row["source_name"],
                target_name=row["target_name"],
                source_fingerprint=self.fingerprints.get(row["source_name"]),
                target_fingerprint=self.fingerprints.get(row["target_name"]),
                object_map=row["object_map"],
                morphism_map=row["morphism_map"],
                score=row["score"],
                truth_value=tv,
                discovered_at=row["discovered_at"],
                confirmations=row["confirmations"],
                contradictions=row["contradictions"],
                evidence=row["evidence"],
            )
            self.analogies[analogy.id] = analogy
            self.by_source[analogy.source_name].append(analogy.id)
            self.by_target[analogy.target_name].append(analogy.id)

    def _persist_analogy(self, analogy: DiscoveredAnalogy):
        """Write a single analogy to SQLite (no-op if no store)."""
        if self._store is None:
            return
        self._store.store_analogy(
            analogy_id=analogy.id,
            source_name=analogy.source_name,
            target_name=analogy.target_name,
            object_map=analogy.object_map,
            morphism_map=analogy.morphism_map,
            score=analogy.score,
            truth_degree=analogy.truth_value.degree,
            truth_modality=analogy.truth_value.modality.name,
            discovered_at=analogy.discovered_at,
            confirmations=analogy.confirmations,
            contradictions=analogy.contradictions,
            evidence=analogy.evidence,
        )

    def _persist_fingerprint(self, name: str, fp: CategoryFingerprint):
        """Write a category fingerprint to SQLite (no-op if no store)."""
        if self._store is None:
            return
        self._store.store_fingerprint(
            cat_name=name,
            n_objects=fp.n_objects,
            n_morphisms=fp.n_morphisms,
            degree_sequence=list(fp.degree_sequence),
            n_rel_types=fp.n_rel_types,
            freq_distribution=list(fp.freq_distribution),
            has_cycles=fp.has_cycles,
            max_chain_length=fp.max_chain_length,
        )

    # ── Public API ─────────────────────────────────────────

    def store(self, analogy: DiscoveredAnalogy) -> str:
        """Store a discovered analogy. Returns its ID."""
        # Check for existing analogy between same pair
        existing = self.get_between(analogy.source_name, analogy.target_name)
        if existing:
            # Update existing with new evidence
            best = max(existing, key=lambda a: a.score)
            if analogy.score > best.score:
                best.object_map = analogy.object_map
                best.morphism_map = analogy.morphism_map
                best.score = analogy.score
            best.reinforce("rediscovered", 0.7)
            self._persist_analogy(best)
            return best.id

        self.analogies[analogy.id] = analogy
        self.by_source[analogy.source_name].append(analogy.id)
        self.by_target[analogy.target_name].append(analogy.id)

        if analogy.source_fingerprint:
            self.fingerprints[analogy.source_name] = analogy.source_fingerprint
            self._persist_fingerprint(analogy.source_name, analogy.source_fingerprint)
        if analogy.target_fingerprint:
            self.fingerprints[analogy.target_name] = analogy.target_fingerprint
            self._persist_fingerprint(analogy.target_name, analogy.target_fingerprint)

        self._persist_analogy(analogy)
        return analogy.id

    def register_category(self, cat: Category):
        """Register a category's fingerprint for future lookups."""
        fp = fingerprint(cat)
        self.fingerprints[cat.name] = fp
        self._persist_fingerprint(cat.name, fp)

    def get(self, analogy_id: str) -> Optional[DiscoveredAnalogy]:
        return self.analogies.get(analogy_id)

    def get_between(self, source: str, target: str) -> list[DiscoveredAnalogy]:
        """Get all analogies between two named categories."""
        source_ids = set(self.by_source.get(source, []))
        target_ids = set(self.by_target.get(target, []))
        ids = source_ids & target_ids
        return [self.analogies[i] for i in ids if i in self.analogies]

    def get_involving(self, name: str) -> list[DiscoveredAnalogy]:
        """Get all analogies involving a named category (as source or target)."""
        ids = set(self.by_source.get(name, []) + self.by_target.get(name, []))
        return [self.analogies[i] for i in ids if i in self.analogies]

    def find_similar(self, cat: Category, min_similarity: float = 0.5) -> list[tuple[str, float]]:
        """
        Find categories in memory with similar fingerprints.
        Returns [(category_name, similarity_score), ...] sorted by similarity.
        """
        fp = fingerprint(cat)
        results = []
        for name, stored_fp in self.fingerprints.items():
            sim = fp.similarity(stored_fp)
            if sim >= min_similarity:
                results.append((name, sim))
        results.sort(key=lambda x: -x[1])
        return results

    def predict_transitive(self, source_name: str, target_name: str) -> Optional[DiscoveredAnalogy]:
        """
        Predict an analogy A→C by composing known analogies A→B and B→C.

        If we know A≅B (with mapping φ) and B≅C (with mapping ψ),
        then A≅C with mapping ψ∘φ.

        The confidence of the transitive analogy is the composition
        of the individual truth values.
        """
        # Find all intermediaries
        source_targets = {}  # target_name -> analogy
        for aid in self.by_source.get(source_name, []):
            a = self.analogies.get(aid)
            if a:
                source_targets[a.target_name] = a

        target_sources = {}  # source_name -> analogy
        for aid in self.by_target.get(target_name, []):
            a = self.analogies.get(aid)
            if a:
                target_sources[a.source_name] = a

        # Find common intermediaries
        intermediaries = set(source_targets.keys()) & set(target_sources.keys())

        best = None
        for mid in intermediaries:
            ab = source_targets[mid]
            bc = target_sources[mid]

            # Compose object maps: A→B→C
            composed_map = {}
            for a_obj, b_obj in ab.object_map.items():
                if b_obj in bc.object_map:
                    composed_map[a_obj] = bc.object_map[b_obj]

            if not composed_map:
                continue

            # Compose truth values
            composed_truth = compose_truth(ab.truth_value, bc.truth_value)
            composed_score = ab.score * bc.score

            candidate = DiscoveredAnalogy(
                source_name=source_name,
                target_name=target_name,
                source_fingerprint=ab.source_fingerprint,
                target_fingerprint=bc.target_fingerprint,
                object_map=composed_map,
                score=composed_score,
                truth_value=composed_truth,
                evidence=[f"transitive_via_{mid}"],
            )

            if best is None or candidate.confidence() > best.confidence():
                best = candidate

        return best

    def all_analogies(self, min_confidence: float = 0.0) -> list[DiscoveredAnalogy]:
        """Get all stored analogies above a confidence threshold."""
        results = [a for a in self.analogies.values() if a.confidence() >= min_confidence]
        results.sort(key=lambda a: -a.confidence())
        return results

    @property
    def stats(self) -> dict:
        return {
            "total_analogies": len(self.analogies),
            "registered_categories": len(self.fingerprints),
            "total_searches": self._search_count,
            "cache_hits": self._hit_count,
        }

    def export_json(self) -> str:
        """Export memory to JSON for persistence."""
        return json.dumps({
            "analogies": [a.to_dict() for a in self.analogies.values()],
            "stats": self.stats,
        }, indent=2)


# ══════════════════════════════════════════════════════════════
# 4. META-CATEGORY — Category of categories
# ══════════════════════════════════════════════════════════════

class MetaCategory:
    """
    A category whose objects are categories and whose morphisms are analogies.

    This is the highest level of abstraction: it lets the engine reason
    about the structure of its own knowledge. If it knows domains A, B, C
    with analogies A→B and B→C, the meta-category represents this directly,
    and its composition table predicts A→C.
    """

    def __init__(self, memory: AnalogyMemory):
        self.memory = memory

    def build(self, min_confidence: float = 0.1) -> Category:
        """Build an actual MORPHOS Category from the meta-level structure."""
        analogies = self.memory.all_analogies(min_confidence)
        if not analogies:
            return create_category("MetaCategory", [], [])

        # Objects = all category names
        objects = set()
        for a in analogies:
            objects.add(a.source_name)
            objects.add(a.target_name)

        # Morphisms = analogies
        morphisms = []
        for a in analogies:
            label = f"analogy_{a.source_name}_{a.target_name}"
            morphisms.append((
                label,
                a.source_name,
                a.target_name,
                "analogy",
                a.confidence(),
            ))

        return create_category(
            "MetaCategory",
            sorted(objects),
            morphisms,
            auto_close=False,
        )

    def connected_components(self) -> list[set[str]]:
        """Find groups of categories connected by analogies."""
        analogies = self.memory.all_analogies()
        adj = defaultdict(set)
        nodes = set()
        for a in analogies:
            adj[a.source_name].add(a.target_name)
            adj[a.target_name].add(a.source_name)
            nodes.add(a.source_name)
            nodes.add(a.target_name)

        visited = set()
        components = []
        for node in nodes:
            if node in visited:
                continue
            component = set()
            stack = [node]
            while stack:
                n = stack.pop()
                if n in visited:
                    continue
                visited.add(n)
                component.add(n)
                stack.extend(adj[n])
            components.append(component)

        return sorted(components, key=len, reverse=True)


# ══════════════════════════════════════════════════════════════
# 5. LEARNING SEARCH — Uses memory to accelerate future searches
# ══════════════════════════════════════════════════════════════

def learn_and_search(
    source: Category,
    target: Category,
    memory: AnalogyMemory,
    min_score: float = 0.3,
) -> list[DiscoveredAnalogy]:
    """
    Search for analogies while learning from the results.

    1. Check memory for existing analogies between these categories
    2. Check for transitive predictions via intermediaries
    3. Run scalable search if no cached result
    4. Store the result in memory for future use
    5. Check if new discovery enables transitive predictions

    Returns discovered analogies, sorted by confidence.
    """
    memory._search_count += 1

    # Step 1: Check cache
    existing = memory.get_between(source.name, target.name)
    if existing:
        memory._hit_count += 1
        best = max(existing, key=lambda a: a.confidence())
        if best.confidence() > min_score:
            return existing

    # Step 2: Check transitive predictions
    predicted = memory.predict_transitive(source.name, target.name)
    if predicted and predicted.confidence() > min_score:
        memory.store(predicted)
        return [predicted]

    # Step 3: Run actual search
    memory.register_category(source)
    memory.register_category(target)

    results = find_functors_scalable(source, target, min_score=min_score)

    if not results:
        return []

    # Step 4: Store results
    discovered = []
    for match in results:
        analogy = DiscoveredAnalogy(
            source_name=source.name,
            target_name=target.name,
            source_fingerprint=memory.fingerprints.get(source.name),
            target_fingerprint=memory.fingerprints.get(target.name),
            object_map=match.object_map,
            morphism_map=match.morphism_map,
            score=match.overall_score,
            truth_value=actual(match.overall_score),
            evidence=[f"discovered_by_search"],
        )
        memory.store(analogy)
        discovered.append(analogy)

    # Step 5: Check for new transitive opportunities
    _discover_transitive(source.name, memory, min_score)
    _discover_transitive(target.name, memory, min_score)

    return discovered


def _discover_transitive(
    pivot_name: str,
    memory: AnalogyMemory,
    min_score: float,
):
    """Check if a category enables new transitive analogies."""
    involving = memory.get_involving(pivot_name)

    # For each pair of analogies sharing this pivot
    as_target = [a for a in involving if a.target_name == pivot_name]
    as_source = [a for a in involving if a.source_name == pivot_name]

    for ab in as_target:
        for bc in as_source:
            if ab.source_name == bc.target_name:
                continue  # would be self-loop
            existing = memory.get_between(ab.source_name, bc.target_name)
            if not existing:
                predicted = memory.predict_transitive(ab.source_name, bc.target_name)
                if predicted and predicted.confidence() > min_score:
                    memory.store(predicted)


def suggest_explorations(
    memory: AnalogyMemory,
    categories: dict[str, Category],
    max_suggestions: int = 5,
) -> list[tuple[str, str, float, str]]:
    """
    Suggest which category pairs to explore next.

    Returns list of (source_name, target_name, predicted_score, reason).
    """
    suggestions = []
    explored = set()
    for a in memory.all_analogies():
        explored.add((a.source_name, a.target_name))
        explored.add((a.target_name, a.source_name))

    # Use cat.name for fingerprint matching
    cat_items = [(cat.name, cat) for cat in categories.values()]

    for i, (n1, c1) in enumerate(cat_items):
        for n2, c2 in cat_items[i + 1:]:
            if (n1, n2) in explored:
                continue

            # Fingerprint similarity
            fp1 = memory.fingerprints.get(n1)
            fp2 = memory.fingerprints.get(n2)
            if fp1 and fp2:
                sim = fp1.similarity(fp2)
                if sim > 0.2:
                    suggestions.append((n1, n2, sim, f"fingerprint_similarity={sim:.3f}"))

            # Transitive potential
            predicted = memory.predict_transitive(n1, n2)
            if predicted:
                suggestions.append((n1, n2, predicted.confidence(),
                                    f"transitive_prediction={predicted.confidence():.3f}"))

    suggestions.sort(key=lambda x: -x[2])
    return suggestions[:max_suggestions]
