"""
Deep WordNet Extraction

Goes beyond 1-hop neighborhoods to extract:
- Full hypernym chains (entity → ... → specific_concept)
- Cross-POS derivation networks (teach_v → teacher_n → teaching_n)
- Frequency-weighted morphisms (common words get stronger connections)
- Semantic domain clustering via topic relationships

Uses the wordfreq package for word frequency data.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Optional

from .wordnet_parser import WordNetDB, POS_MAP
from .categories import Category, create_category

# Try to load wordfreq for frequency data
try:
    from wordfreq import word_frequency, zipf_frequency
    HAS_WORDFREQ = True
except ImportError:
    HAS_WORDFREQ = False


def extract_hypernym_chain(
    db: WordNetDB,
    word: str,
    max_depth: int = 15,
) -> list[tuple[str, str, str, float]]:
    """
    Extract the full hypernym chain from a word up to the root entity.

    Returns list of (label, child, parent, depth_ratio) tuples.
    The depth_ratio (0-1) indicates position in the chain, usable
    as a quantitative morphism value.
    """
    synsets = db.lookup(word)
    if not synsets:
        return []

    chain = []
    visited = set()
    current = synsets[0]
    depth = 0

    while depth < max_depth:
        hypernyms = [
            rel for rtype, rel in db.get_related(current)
            if rtype in ("hypernym", "instance_hypernym")
        ]
        if not hypernyms:
            break

        parent = hypernyms[0]
        child_name = _clean(current.words[0])
        parent_name = _clean(parent.words[0])

        if parent.offset in visited:
            break
        visited.add(parent.offset)

        chain.append((child_name, parent_name, depth))
        current = parent
        depth += 1

    # Convert to morphism tuples with depth ratio as value
    total = len(chain) if chain else 1
    return [
        ("hypernym", child, parent, "hypernym", round((total - d) / total, 3))
        for child, parent, d in chain
    ]


def extract_derivation_network(
    db: WordNetDB,
    word: str,
    max_hops: int = 2,
) -> list[tuple[str, str, str, str, float]]:
    """
    Extract cross-POS derivation network.

    Follows derivationally-related-forms links across parts of speech:
    teach (v) → teacher (n) → teaching (n) → teachable (a)

    Returns morphism tuples with frequency ratio as value.
    """
    synsets = db.lookup(word)
    if not synsets:
        return []

    morphisms = []
    visited = set()
    frontier = [(synsets[0], _clean(synsets[0].words[0]))]

    for _ in range(max_hops):
        new_frontier = []
        for synset, src_name in frontier:
            if synset.offset in visited:
                continue
            visited.add(synset.offset)

            for rtype, related in db.get_related(synset):
                if rtype != "derivation":
                    continue
                tgt_name = _clean(related.words[0])
                if tgt_name == src_name:
                    continue

                # Use frequency ratio as value
                freq_val = _freq_ratio(src_name, tgt_name)
                pos_src = POS_MAP.get(synset.pos, "?")
                pos_tgt = POS_MAP.get(related.pos, "?")
                label = f"derives_{pos_src}_{pos_tgt}"

                morphisms.append((label, src_name, tgt_name, "derivation", freq_val))

                if related.offset not in visited:
                    new_frontier.append((related, tgt_name))

        frontier = new_frontier

    return morphisms


def extract_domain_cluster(
    db: WordNetDB,
    domain_word: str,
    max_members: int = 30,
) -> list[tuple[str, str, str, str, Optional[float]]]:
    """
    Extract all words belonging to a semantic domain.

    Uses WordNet's domain_topic and domain_member_topic relations
    to find words clustered around a domain (e.g., "physics",
    "music", "medicine").
    """
    synsets = db.lookup(domain_word)
    if not synsets:
        return []

    domain_synset = synsets[0]
    domain_name = _clean(domain_synset.words[0])

    morphisms = []
    members = set()

    # Find all members of this domain
    for rtype, related in db.get_related(domain_synset):
        if rtype == "domain_member_topic" and len(members) < max_members:
            member_name = _clean(related.words[0])
            if member_name != domain_name:
                members.add(member_name)
                freq = _freq_value(member_name)
                morphisms.append(("domain_member", member_name, domain_name, "domain_member", freq))

    # Also find what this domain is a member of
    for rtype, related in db.get_related(domain_synset):
        if rtype == "domain_topic":
            parent_name = _clean(related.words[0])
            morphisms.append(("domain_topic", domain_name, parent_name, "domain_topic", None))

    # Add inter-member relationships
    for member in members:
        member_synsets = db.lookup(member)
        if not member_synsets:
            continue
        for rtype, related in db.get_related(member_synsets[0]):
            rel_name = _clean(related.words[0])
            if rel_name in members and rel_name != member:
                morphisms.append((rtype, member, rel_name, rtype, None))

    return morphisms


def build_deep_category(
    db: WordNetDB,
    seed_word: str,
    include_hypernym_chain: bool = True,
    include_derivations: bool = True,
    include_domain: bool = True,
    include_standard: bool = True,
    max_nodes: int = 25,
    name: str | None = None,
) -> Optional[Category]:
    """
    Build a richly connected category using all available
    extraction methods.

    Combines:
    - Standard 1-hop neighborhood (all relation types)
    - Full hypernym chain to root
    - Cross-POS derivation network
    - Domain cluster membership
    - Word frequency as morphism values
    """
    all_morphisms: list[tuple] = []
    all_objects: set[str] = set()

    synsets = db.lookup(seed_word)
    if not synsets:
        return None

    seed = _clean(synsets[0].words[0])
    all_objects.add(seed)

    # Standard 1-hop neighborhood
    if include_standard:
        for rtype, related in db.get_related(synsets[0]):
            tgt = _clean(related.words[0])
            if tgt == seed:
                continue
            all_objects.add(tgt)
            freq = _freq_ratio(seed, tgt)
            all_morphisms.append((rtype, seed, tgt, rtype, freq))

    # Full hypernym chain
    if include_hypernym_chain:
        chain = extract_hypernym_chain(db, seed_word)
        for morph in chain:
            all_objects.add(morph[1])
            all_objects.add(morph[2])
            all_morphisms.append(morph)

    # Cross-POS derivations
    if include_derivations:
        derivs = extract_derivation_network(db, seed_word, max_hops=2)
        for morph in derivs:
            all_objects.add(morph[1])
            all_objects.add(morph[2])
            all_morphisms.append(morph)

    # Domain cluster
    if include_domain:
        domains = extract_domain_cluster(db, seed_word, max_members=10)
        for morph in domains:
            all_objects.add(morph[1])
            all_objects.add(morph[2])
            all_morphisms.append(morph)

    # Trim to max_nodes — keep seed + most connected
    if len(all_objects) > max_nodes:
        conn_count: dict[str, int] = defaultdict(int)
        for m in all_morphisms:
            conn_count[m[1]] += 1
            conn_count[m[2]] += 1
        ranked = sorted(conn_count.items(), key=lambda x: -x[1])
        keep = {seed}
        for obj, _ in ranked:
            if len(keep) >= max_nodes:
                break
            keep.add(obj)
        all_objects = keep
        all_morphisms = [m for m in all_morphisms if m[1] in keep and m[2] in keep]

    # Deduplicate
    seen = set()
    unique = []
    for m in all_morphisms:
        key = (m[0], m[1], m[2])
        if key not in seen and m[1] != m[2]:
            seen.add(key)
            unique.append(m)

    if not unique:
        return None

    objs = sorted(all_objects)
    cat_name = name or f"deep_{seed_word}"
    return create_category(cat_name, objs, unique, auto_close=False)


def build_frequency_enriched_category(
    db: WordNetDB,
    words: list[str],
    name: str = "freq_enriched",
    max_nodes: int = 50,
) -> Optional[Category]:
    """
    Build a category connecting multiple words with frequency-weighted
    morphisms. Words that co-occur more frequently in language get
    stronger connection values.
    """
    all_morphisms = []
    all_objects = set()

    for word in words:
        synsets = db.lookup(word)
        if not synsets:
            continue

        s = synsets[0]
        src = _clean(s.words[0])
        all_objects.add(src)

        for rtype, related in db.get_related(s):
            tgt = _clean(related.words[0])
            if tgt == src or len(all_objects) >= max_nodes:
                continue
            all_objects.add(tgt)
            freq = _freq_ratio(src, tgt)
            all_morphisms.append((rtype, src, tgt, rtype, freq))

    # Cross-connect: find relationships between seed words
    for w1 in words:
        for w2 in words:
            if w1 == w2:
                continue
            s1 = db.lookup(w1)
            s2 = db.lookup(w2)
            if not s1 or not s2:
                continue
            n1 = _clean(s1[0].words[0])
            n2 = _clean(s2[0].words[0])
            for rtype, related in db.get_related(s1[0]):
                if related.offset == s2[0].offset:
                    freq = _freq_ratio(n1, n2)
                    all_morphisms.append((rtype, n1, n2, rtype, freq))

    seen = set()
    unique = []
    for m in all_morphisms:
        key = (m[0], m[1], m[2])
        if key not in seen and m[1] != m[2]:
            seen.add(key)
            unique.append(m)

    if not unique:
        return None

    return create_category(name, sorted(all_objects), unique, auto_close=False)


# ── Utilities ─────────────────────────────────────────────────

def _clean(s: str) -> str:
    return s.replace(" ", "_").replace("(", "").replace(")", "").replace("'", "")

def _freq_value(word: str) -> Optional[float]:
    """Get Zipf frequency for a word (0-8 scale, higher = more common)."""
    if not HAS_WORDFREQ:
        return None
    try:
        z = zipf_frequency(word.replace("_", " "), "en")
        return round(z, 2) if z > 0 else None
    except Exception:
        return None

def _freq_ratio(word1: str, word2: str) -> Optional[float]:
    """
    Compute frequency-based connection strength.
    Returns a value in (0, 1] where higher means both words
    are more common (stronger conceptual connection).
    """
    if not HAS_WORDFREQ:
        return None
    try:
        f1 = zipf_frequency(word1.replace("_", " "), "en")
        f2 = zipf_frequency(word2.replace("_", " "), "en")
        if f1 <= 0 or f2 <= 0:
            return None
        # Geometric mean normalized to 0-1 (Zipf scale is 0-8)
        return round(min((f1 * f2) ** 0.5 / 8.0, 1.0), 3)
    except Exception:
        return None
