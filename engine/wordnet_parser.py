"""
MORPHOS WordNet Parser

Parses Princeton WordNet 3.1 database files (from npm wordnet-db)
into MORPHOS categories.

WordNet data files are the standard format used by Princeton's
WordNet project, licensed under the Princeton WordNet License.

Pointer types parsed:
  @  hypernym          (IS-A upward)
  ~  hyponym           (IS-A downward)
  #m member meronym    (MEMBER-OF)
  %m member holonym    (HAS-MEMBER)
  #p part meronym      (PART-OF)
  %p part holonym      (HAS-PART)
  #s substance meronym (MADE-OF)
  %s substance holonym (SUBSTANCE-HAS)
  !  antonym
  +  derivationally related
  =  attribute
  *  entailment (verbs)
  >  cause (verbs)
  &  similar to
  ;c domain (topic)
  -c member of domain
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict


WN_DIR = Path(__file__).parent.parent / "node_modules" / "wordnet-db" / "dict"

# Map WordNet pointer symbols to human-readable relationship names
POINTER_MAP = {
    "@":  "hypernym",
    "@i": "instance_hypernym",
    "~":  "hyponym",
    "~i": "instance_hyponym",
    "#m": "member_meronym",
    "%m": "member_holonym",
    "#p": "part_meronym",
    "%p": "part_holonym",
    "#s": "substance_meronym",
    "%s": "substance_holonym",
    "!":  "antonym",
    "+":  "derivation",
    "=":  "attribute",
    "*":  "entailment",
    ">":  "cause",
    "&":  "similar",
    ";c": "domain_topic",
    "-c": "domain_member_topic",
    ";r": "domain_region",
    "-r": "domain_member_region",
    ";u": "domain_usage",
    "-u": "domain_member_usage",
    "$":  "verb_group",
    "<":  "participle",
    "\\":  "pertainym",
    "^":  "also_see",
}

POS_MAP = {"n": "noun", "v": "verb", "a": "adj", "s": "adj_satellite", "r": "adv"}


class Synset:
    """A WordNet synset (set of synonymous words sharing a definition)."""
    __slots__ = ("offset", "pos", "words", "gloss", "pointers")

    def __init__(self, offset, pos, words, gloss, pointers):
        self.offset = offset
        self.pos = pos
        self.words = words          # list of lemma strings
        self.gloss = gloss          # definition + examples
        self.pointers = pointers    # list of (ptr_type, target_offset, target_pos)

    @property
    def name(self):
        return f"{self.words[0]}.{self.pos}.{self.offset}"

    @property
    def definition(self):
        return self.gloss.split(";")[0].strip(' "') if self.gloss else ""

    def __repr__(self):
        return f"Synset({self.words[0]}.{self.pos})"


class WordNetDB:
    """Parser and accessor for WordNet database files."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else WN_DIR
        self.synsets = {}           # (offset, pos) -> Synset
        self.offset_index = {}      # offset -> Synset (first match)
        self.word_index = defaultdict(list)  # lemma -> [(offset, pos), ...]
        self._loaded = False

    def load(self, pos_list=None):
        """Load WordNet data files. pos_list filters which POS to load."""
        if pos_list is None:
            pos_list = ["noun", "verb", "adj", "adv"]

        pos_to_file = {"noun": "n", "verb": "v", "adj": "a", "adv": "r"}

        for pos_name in pos_list:
            pos_char = pos_to_file.get(pos_name)
            if not pos_char:
                continue
            data_file = self.data_dir / f"data.{pos_name}"
            if data_file.exists():
                self._parse_data_file(data_file, pos_char)

            idx_file = self.data_dir / f"index.{pos_name}"
            if idx_file.exists():
                self._parse_index_file(idx_file, pos_char)

        # Build offset-only index for fast cross-POS lookups
        for (offset, _), synset in self.synsets.items():
            if offset not in self.offset_index:
                self.offset_index[offset] = synset

        self._loaded = True

    def _parse_data_file(self, path, pos_char):
        """Parse a WordNet data file (data.noun, data.verb, etc.)."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("  "):
                    continue  # copyright header
                line = line.strip()
                if not line:
                    continue

                try:
                    parts = line.split("|")
                    gloss = parts[1].strip() if len(parts) > 1 else ""
                    tokens = parts[0].split()

                    offset = tokens[0]
                    # tokens[1] = lex_filenum
                    ss_type = tokens[2]
                    w_cnt = int(tokens[3], 16)

                    # Read words
                    words = []
                    idx = 4
                    for _ in range(w_cnt):
                        word = tokens[idx].replace("_", " ")
                        # skip lex_id
                        idx += 2
                        words.append(word)

                    # Read pointers
                    p_cnt = int(tokens[idx])
                    idx += 1
                    pointers = []
                    for _ in range(p_cnt):
                        if idx + 4 > len(tokens):
                            break
                        ptr_sym = tokens[idx]
                        ptr_offset = tokens[idx + 1]
                        ptr_pos = tokens[idx + 2]
                        # source/target = tokens[idx + 3]
                        idx += 4
                        rel_name = POINTER_MAP.get(ptr_sym, ptr_sym)
                        pointers.append((rel_name, ptr_offset, ptr_pos))

                    synset = Synset(offset, ss_type, words, gloss, pointers)
                    self.synsets[(offset, ss_type)] = synset

                except (IndexError, ValueError):
                    continue

    def _parse_index_file(self, path, pos_char):
        """Parse a WordNet index file to build word->synset mapping."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("  "):
                    continue
                line = line.strip()
                if not line:
                    continue
                tokens = line.split()
                if len(tokens) < 6:
                    continue
                lemma = tokens[0].replace("_", " ")
                pos = tokens[1]
                try:
                    synset_cnt = int(tokens[2])
                    p_cnt = int(tokens[3])
                    # skip pointer symbols
                    skip = 4 + p_cnt
                    sense_cnt = int(tokens[skip])
                    # tagsense_cnt = int(tokens[skip + 1])
                    offsets = tokens[skip + 2: skip + 2 + synset_cnt]
                    for off in offsets:
                        self.word_index[lemma].append((off, pos))
                except (IndexError, ValueError):
                    continue

    def lookup(self, word):
        """Look up all synsets for a word. Returns list of Synset objects."""
        entries = self.word_index.get(word.lower().replace(" ", "_"), [])
        results = []
        seen = set()
        for off, pos in entries:
            # Try exact (offset, pos) match first
            synset = self.synsets.get((off, pos))
            # Adj satellites: index uses 'a' but data uses 's'
            if not synset and pos == "a":
                synset = self.synsets.get((off, "s"))
            # Fallback to offset-only index
            if not synset:
                synset = self.offset_index.get(off)
            if synset and synset.offset not in seen:
                seen.add(synset.offset)
                results.append(synset)
        return results

    def get_synset(self, offset, pos=None):
        """Get a synset by its offset. O(1) via index."""
        if pos:
            synset = self.synsets.get((offset, pos))
            if synset:
                return synset
            # Adj satellite fallback
            if pos == "a":
                return self.synsets.get((offset, "s"))
            if pos == "s":
                return self.synsets.get((offset, "a"))
        return self.offset_index.get(offset)

    def get_related(self, synset, rel_type=None):
        """Get synsets related to the given synset."""
        results = []
        for ptr_type, ptr_offset, ptr_pos in synset.pointers:
            if rel_type and ptr_type != rel_type:
                continue
            related = self.get_synset(ptr_offset)
            if related:
                results.append((ptr_type, related))
        return results

    def relationship_graph(self, words, max_depth=1):
        """
        Build a relationship graph starting from a set of seed words,
        expanding outward by max_depth hops.

        Uses offset-qualified names to avoid polysemy collisions:
        different synsets with the same first word get distinct node names.

        Returns: (nodes: dict[str, Synset], edges: list[(str, rel_type, str)])
        """
        nodes = {}      # node_name -> Synset
        offset_to_name = {}  # offset -> node_name
        edges = []
        frontier = set()

        def node_name(synset):
            """Generate a unique, human-readable node name for a synset."""
            base = synset.words[0]
            if base not in nodes:
                return base
            # Disambiguate with POS
            name = f"{base}_{POS_MAP.get(synset.pos, synset.pos)}"
            if name not in nodes:
                return name
            # Last resort: use offset
            return f"{base}_{synset.offset}"

        def get_or_add(synset):
            """Get existing node name or create new one."""
            if synset.offset in offset_to_name:
                return offset_to_name[synset.offset]
            name = node_name(synset)
            nodes[name] = synset
            offset_to_name[synset.offset] = name
            return name

        # Start with seed synsets
        for word in words:
            for synset in self.lookup(word):
                name = get_or_add(synset)
                frontier.add(name)

        # Expand
        for _ in range(max_depth):
            new_frontier = set()
            for name in frontier:
                synset = nodes[name]
                for rel_type, related in self.get_related(synset):
                    rel_name = get_or_add(related)
                    edge = (name, rel_type, rel_name)
                    if edge not in edges:
                        edges.append(edge)
                    if rel_name not in frontier and related.offset not in {
                        nodes[n].offset for n in frontier
                    }:
                        new_frontier.add(rel_name)
            frontier = new_frontier

        return nodes, edges

    def stats(self):
        """Print database statistics."""
        n_synsets = len(self.synsets)
        n_words = len(self.word_index)
        n_pointers = sum(len(s.pointers) for s in self.synsets.values())

        by_pos = defaultdict(int)
        for (_, pos), _ in self.synsets.items():
            by_pos[POS_MAP.get(pos, pos)] += 1

        by_rel = defaultdict(int)
        for s in self.synsets.values():
            for ptr_type, _, _ in s.pointers:
                by_rel[ptr_type] += 1

        print(f"WordNet 3.1 loaded:")
        print(f"  Synsets: {n_synsets:,}")
        print(f"  Indexed words: {n_words:,}")
        print(f"  Total relationships: {n_pointers:,}")
        print(f"  By POS: {dict(by_pos)}")
        print(f"  Top relationship types:")
        for rel, count in sorted(by_rel.items(), key=lambda x: -x[1])[:15]:
            print(f"    {rel:25s}: {count:,}")
