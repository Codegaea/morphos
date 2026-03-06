"""
Data Adapters — Ingest any structured dataset into MORPHOS categories.

Supported formats:
- CSV/TSV triples (subject, relation, object per line)
- ConceptNet CSV (assertions with metadata and weights)
- JSON-LD / JSON triples
- Edge list (simple pairs with optional labels)
- Adjacency dict (Python dict of {node: [neighbors]})

Each adapter converts external data into create_category() calls.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import csv
import json
from typing import Optional, Callable

from .categories import Category, create_category
from .epistemic import Probable


# ── CSV/TSV Triple Reader ─────────────────────────────────────

def from_triples_csv(
    path: str | Path,
    name: str = "csv_category",
    subject_col: int = 0,
    relation_col: int = 1,
    object_col: int = 2,
    weight_col: int | None = None,
    delimiter: str = "\t",
    skip_header: bool = True,
    max_rows: int | None = None,
    filter_fn: Callable | None = None,
    auto_close: bool = False,
) -> Category:
    """
    Read triples from a CSV/TSV file and build a category.

    Args:
        path: path to the CSV/TSV file
        name: category name
        subject_col: column index for subject (source object)
        relation_col: column index for relation (morphism label)
        object_col: column index for object (target object)
        weight_col: optional column index for confidence weight (0-1)
        delimiter: column separator
        skip_header: skip first line
        max_rows: limit number of rows read
        filter_fn: optional function(row) -> bool to filter rows
        auto_close: whether to auto-compose (expensive for large data)
    """
    objects = set()
    morphisms = []
    statuses = {}

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader, None)

        count = 0
        for row in reader:
            if max_rows and count >= max_rows:
                break

            ncols = max(subject_col, relation_col, object_col) + 1
            if len(row) < ncols:
                continue

            if filter_fn and not filter_fn(row):
                continue

            subj = _clean_name(row[subject_col])
            rel = _clean_name(row[relation_col])
            obj = _clean_name(row[object_col])

            if not subj or not rel or not obj or subj == obj:
                continue

            objects.add(subj)
            objects.add(obj)

            # Handle duplicate (rel, subj, obj) by appending count
            key = (rel, subj, obj)
            label = rel
            morphisms.append((label, subj, obj))

            if weight_col is not None and weight_col < len(row):
                try:
                    w = float(row[weight_col])
                    if 0 < w < 1:
                        statuses[label] = f"probable({w:.3f})"
                except ValueError:
                    pass

            count += 1

    # Deduplicate morphisms
    seen = set()
    unique = []
    for label, subj, obj in morphisms:
        key = (label, subj, obj)
        if key not in seen:
            seen.add(key)
            unique.append((label, subj, obj))

    return create_category(
        name,
        sorted(objects),
        unique,
        statuses=statuses,
        auto_close=auto_close,
    )


# ── ConceptNet CSV Adapter ────────────────────────────────────

def from_conceptnet_csv(
    path: str | Path,
    name: str = "conceptnet",
    language: str = "en",
    min_weight: float = 1.0,
    relations: set[str] | None = None,
    max_rows: int | None = None,
    auto_close: bool = False,
) -> Category:
    """
    Read ConceptNet assertions CSV and build a category.

    ConceptNet CSV format (tab-separated):
        col 0: assertion URI    /a/[/r/IsA/,/c/en/dog/,/c/en/animal/]
        col 1: relation URI     /r/IsA
        col 2: source URI       /c/en/dog
        col 3: target URI       /c/en/animal
        col 4: JSON metadata    {"weight": 2.0, ...}

    Args:
        path: path to ConceptNet assertions CSV (conceptnet-assertions-*.csv)
        name: category name
        language: language code filter (e.g., "en")
        min_weight: minimum assertion weight to include
        relations: optional set of relation names to include (e.g., {"IsA", "PartOf"})
        max_rows: limit number of rows
        auto_close: whether to auto-compose
    """
    objects = set()
    morphisms = []
    statuses = {}

    lang_prefix = f"/c/{language}/"

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        count = 0

        for row in reader:
            if max_rows and count >= max_rows:
                break
            if len(row) < 5:
                continue

            rel_uri = row[1]    # /r/IsA
            src_uri = row[2]    # /c/en/dog
            tgt_uri = row[3]    # /c/en/animal
            meta_str = row[4]   # {"weight": ...}

            # Language filter
            if not src_uri.startswith(lang_prefix) or not tgt_uri.startswith(lang_prefix):
                continue

            # Extract relation name
            rel_name = rel_uri.split("/")[-1]  # "IsA"

            # Relation filter
            if relations and rel_name not in relations:
                continue

            # Weight filter
            weight = 1.0
            try:
                meta = json.loads(meta_str)
                weight = meta.get("weight", 1.0)
            except (json.JSONDecodeError, TypeError):
                pass

            if weight < min_weight:
                continue

            # Extract concept names
            src_name = _extract_conceptnet_name(src_uri, lang_prefix)
            tgt_name = _extract_conceptnet_name(tgt_uri, lang_prefix)

            if not src_name or not tgt_name or src_name == tgt_name:
                continue

            objects.add(src_name)
            objects.add(tgt_name)
            morphisms.append((rel_name, src_name, tgt_name))

            # Normalize weight to epistemic status
            if weight < 2.0:
                norm_w = min(weight / 5.0, 0.99)
                if norm_w > 0:
                    statuses[rel_name] = f"probable({norm_w:.3f})"

            count += 1

    # Deduplicate
    seen = set()
    unique = []
    for label, subj, obj in morphisms:
        key = (label, subj, obj)
        if key not in seen:
            seen.add(key)
            unique.append((label, subj, obj))

    return create_category(
        name,
        sorted(objects),
        unique,
        statuses=statuses,
        auto_close=auto_close,
    )


def _extract_conceptnet_name(uri: str, lang_prefix: str) -> str:
    """Extract clean concept name from ConceptNet URI."""
    name = uri[len(lang_prefix):]
    # Remove POS suffix if present (e.g., /n, /v)
    parts = name.split("/")
    name = parts[0]
    return name.replace("_", " ")


# ── ConceptNet Neighborhood Builder ───────────────────────────

CONCEPTNET_RELATIONS = {
    "RelatedTo", "FormOf", "IsA", "PartOf", "HasA", "UsedFor",
    "CapableOf", "AtLocation", "Causes", "HasSubevent", "HasFirstSubevent",
    "HasLastSubevent", "HasPrerequisite", "HasProperty", "MotivatedByGoal",
    "ObstructedBy", "Desires", "CreatedBy", "Synonym", "Antonym",
    "DistinctFrom", "DerivedFrom", "SymbolOf", "DefinedAs",
    "MannerOf", "LocatedNear", "HasContext", "SimilarTo",
    "EtymologicallyRelatedTo", "EtymologicallyDerivedFrom",
    "CausesDesire", "MadeOf", "ReceivesAction", "ExternalURL",
    "InstanceOf", "NotDesires", "NotUsedFor", "NotCapableOf",
    "NotHasProperty", "NotIsA",
}

# The most semantically rich relations for analogy discovery
CONCEPTNET_CORE_RELATIONS = {
    "IsA", "PartOf", "HasA", "UsedFor", "CapableOf", "AtLocation",
    "Causes", "HasPrerequisite", "HasProperty", "MotivatedByGoal",
    "Desires", "Antonym", "MadeOf", "CausesDesire", "MannerOf",
    "Synonym", "SimilarTo", "InstanceOf",
}


def from_conceptnet_neighborhood(
    path: str | Path,
    seed_words: list[str],
    name: str = "conceptnet_neighborhood",
    language: str = "en",
    relations: set[str] | None = None,
    max_nodes: int = 50,
    min_weight: float = 1.0,
    auto_close: bool = False,
) -> Category:
    """
    Build a category from ConceptNet by extracting the neighborhood
    around seed words.

    Reads the full CSV but only keeps nodes within 1 hop of seeds.
    """
    if relations is None:
        relations = CONCEPTNET_CORE_RELATIONS

    lang_prefix = f"/c/{language}/"
    seeds = set(w.lower().replace(" ", "_") for w in seed_words)

    # First pass: find all edges touching seeds
    objects = set(seed_words)
    morphisms = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 5:
                continue

            rel_uri = row[1]
            src_uri = row[2]
            tgt_uri = row[3]

            if not src_uri.startswith(lang_prefix) or not tgt_uri.startswith(lang_prefix):
                continue

            rel_name = rel_uri.split("/")[-1]
            if rel_name not in relations:
                continue

            src_name = _extract_conceptnet_name(src_uri, lang_prefix)
            tgt_name = _extract_conceptnet_name(tgt_uri, lang_prefix)

            src_key = src_name.lower().replace(" ", "_")
            tgt_key = tgt_name.lower().replace(" ", "_")

            # Keep edges where at least one endpoint is a seed
            if src_key not in seeds and tgt_key not in seeds:
                continue

            # Weight filter
            try:
                meta = json.loads(row[4])
                if meta.get("weight", 1.0) < min_weight:
                    continue
            except (json.JSONDecodeError, TypeError):
                pass

            if src_name == tgt_name:
                continue

            objects.add(src_name)
            objects.add(tgt_name)
            morphisms.append((rel_name, src_name, tgt_name))

            if len(objects) >= max_nodes:
                break

    # Deduplicate
    seen = set()
    unique = []
    for label, subj, obj in morphisms:
        key = (label, subj, obj)
        if key not in seen:
            seen.add(key)
            unique.append((label, subj, obj))

    if not unique:
        return create_category(name, list(objects), [], auto_close=False)

    return create_category(
        name,
        sorted(objects),
        unique,
        auto_close=auto_close,
    )


# ── JSON Triples Reader ──────────────────────────────────────

def from_json_triples(
    path: str | Path,
    name: str = "json_category",
    subject_key: str = "subject",
    relation_key: str = "relation",
    object_key: str = "object",
    weight_key: str | None = "weight",
    max_items: int | None = None,
    auto_close: bool = False,
) -> Category:
    """
    Read triples from a JSON file (list of objects or JSONL).

    Supports:
    - JSON array: [{"subject": "A", "relation": "r", "object": "B"}, ...]
    - JSON Lines: one JSON object per line
    """
    items = []
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content.startswith("["):
            items = json.loads(content)
        else:
            # JSON Lines
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    objects = set()
    morphisms = []
    statuses = {}

    for i, item in enumerate(items):
        if max_items and i >= max_items:
            break

        subj = _clean_name(str(item.get(subject_key, "")))
        rel = _clean_name(str(item.get(relation_key, "")))
        obj = _clean_name(str(item.get(object_key, "")))

        if not subj or not rel or not obj or subj == obj:
            continue

        objects.add(subj)
        objects.add(obj)
        morphisms.append((rel, subj, obj))

        if weight_key and weight_key in item:
            try:
                w = float(item[weight_key])
                if 0 < w < 1:
                    statuses[rel] = f"probable({w:.3f})"
            except (ValueError, TypeError):
                pass

    # Deduplicate
    seen = set()
    unique = []
    for label, subj, obj in morphisms:
        key = (label, subj, obj)
        if key not in seen:
            seen.add(key)
            unique.append((label, subj, obj))

    return create_category(
        name,
        sorted(objects),
        unique,
        statuses=statuses,
        auto_close=auto_close,
    )


# ── Edge List Reader ──────────────────────────────────────────

def from_edge_list(
    path: str | Path,
    name: str = "edge_category",
    default_label: str = "connected",
    delimiter: str = " ",
    max_rows: int | None = None,
    auto_close: bool = False,
) -> Category:
    """
    Read an edge list file (one edge per line: source target [label]).
    Common format for graph datasets (SNAP, NetworkX, etc.)
    """
    objects = set()
    morphisms = []

    with open(path, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            if max_rows and count >= max_rows:
                break
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("%"):
                continue

            parts = line.split(delimiter)
            if len(parts) < 2:
                continue

            src = _clean_name(parts[0])
            tgt = _clean_name(parts[1])
            label = _clean_name(parts[2]) if len(parts) > 2 else default_label

            if not src or not tgt or src == tgt:
                continue

            objects.add(src)
            objects.add(tgt)
            morphisms.append((label, src, tgt))
            count += 1

    seen = set()
    unique = [(l, s, t) for l, s, t in morphisms if (l, s, t) not in seen and not seen.add((l, s, t))]

    return create_category(
        name,
        sorted(objects),
        unique,
        auto_close=auto_close,
    )


# ── Dict/Programmatic Builder ─────────────────────────────────

def from_dict(
    data: dict[str, list[tuple[str, str]]],
    name: str = "dict_category",
    auto_close: bool = True,
) -> Category:
    """
    Build a category from a Python dictionary.

    Args:
        data: {source_object: [(relation, target_object), ...]}
        name: category name

    Example:
        from_dict({
            "dog": [("IsA", "animal"), ("HasA", "tail"), ("CapableOf", "bark")],
            "cat": [("IsA", "animal"), ("HasA", "tail"), ("CapableOf", "purr")],
            "animal": [("IsA", "living_thing")],
        })
    """
    objects = set()
    morphisms = []

    for src, relations in data.items():
        objects.add(src)
        for rel, tgt in relations:
            objects.add(tgt)
            morphisms.append((rel, src, tgt))

    return create_category(
        name,
        sorted(objects),
        morphisms,
        auto_close=auto_close,
    )


# ── WordNet-to-Category Adapter ───────────────────────────────

def from_wordnet(
    db,
    seed_word: str,
    depth: int = 1,
    max_nodes: int = 15,
    name: str | None = None,
    auto_close: bool = False,
) -> Optional[Category]:
    """
    Build a category from WordNet data around a seed word.

    Args:
        db: WordNetDB instance (from engine.wordnet_parser)
        seed_word: word to center the category around
        depth: how many hops to expand
        max_nodes: maximum number of objects
        name: category name (defaults to wn_{seed_word})
    """
    synsets = db.lookup(seed_word)
    if not synsets:
        return None

    root = synsets[0]
    objects = set()
    morphisms = []
    definitions = {}

    def clean(s):
        return s.replace(" ", "_").replace("(", "").replace(")", "")

    seed = clean(root.words[0])
    objects.add(seed)
    definitions[seed] = root.definition

    frontier = [(seed, root)]
    for _ in range(depth):
        next_frontier = []
        for src_name, src_synset in frontier:
            for rtype, related in db.get_related(src_synset):
                tgt_name = clean(related.words[0])
                if tgt_name == src_name:
                    continue
                if tgt_name not in objects and len(objects) < max_nodes:
                    objects.add(tgt_name)
                    definitions[tgt_name] = related.definition
                    next_frontier.append((tgt_name, related))
                if tgt_name in objects:
                    morphisms.append((rtype, src_name, tgt_name))
        frontier = next_frontier

    # Deduplicate
    seen = set()
    unique = []
    for label, src, tgt in morphisms:
        key = (label, src, tgt)
        if key not in seen:
            seen.add(key)
            unique.append((label, src, tgt))

    if not unique:
        return None

    objs = sorted(objects)
    # Final filter
    obj_set = set(objs)
    unique = [(l, s, t) for l, s, t in unique if s in obj_set and t in obj_set]

    cat_name = name or f"wn_{seed_word}"
    cat = create_category(cat_name, objs, unique, auto_close=auto_close)
    cat.description = f"WordNet neighborhood of '{seed_word}'"

    # Attach definitions as metadata
    cat._definitions = definitions
    return cat


# ── Utility ───────────────────────────────────────────────────

def _clean_name(s: str) -> str:
    """Clean a string for use as an object name."""
    s = s.strip().strip('"').strip("'")
    # Replace problematic characters
    for ch in ["\t", "\n", "\r"]:
        s = s.replace(ch, " ")
    s = s.strip()
    return s if s else ""


def describe_dataset(path: str | Path, delimiter: str = "\t", n_sample: int = 5) -> dict:
    """
    Quick summary of a triple dataset file.
    Shows column count, sample rows, and basic stats.
    """
    path = Path(path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 100:
                break
            lines.append(line.strip())

    total_lines = sum(1 for _ in open(path, encoding="utf-8"))

    # Analyze structure
    col_counts = Counter()
    for line in lines:
        cols = line.split(delimiter)
        col_counts[len(cols)] += 1

    sample_rows = []
    for line in lines[:n_sample]:
        sample_rows.append(line.split(delimiter))

    return {
        "path": str(path),
        "total_lines": total_lines,
        "column_distribution": dict(col_counts),
        "sample_rows": sample_rows,
        "file_size_mb": path.stat().st_size / (1024 * 1024),
    }
