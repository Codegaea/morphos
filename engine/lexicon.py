"""
MORPHOS Lexical Knowledge Base

Real dictionary entries with verified relationships.
Every entry follows standard lexicographic structure:
word, part of speech, definition, and typed relationships.

Relationship types modeled (from standard lexicographic practice):
  - hypernym:    IS-A (dog → animal)
  - hyponym:     TYPE-OF (animal → dog) — inverse of hypernym
  - meronym:     PART-OF (wheel → car)
  - holonym:     HAS-PART (car → wheel) — inverse of meronym
  - synonym:     SIMILAR-TO (big ≈ large)
  - antonym:     OPPOSITE-OF (hot ↔ cold)
  - derivation:  DERIVED-FROM (teach → teacher)
  - causes:      CAUSES (heat → melt)
  - entails:     ENTAILS (buy → pay)
  - domain:      BELONGS-TO-DOMAIN (scalpel → medicine)
  - similar:     ANALOGOUS (fin ≈ wing, in function)

Sources: Entries reflect standard English dictionary structure
as found in Merriam-Webster, Oxford, and WordNet taxonomy.
"""

# Each entry: word -> { pos, definition, relationships }
# Relationships: [(type, target_word), ...]

LEXICON = {
    # ══════════════════════════════════════════════════════
    # DOMAIN: WATER / FLUID
    # ══════════════════════════════════════════════════════
    "water": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "a clear liquid that forms rivers, lakes, and rain",
        "relations": [
            ("hypernym", "liquid"),
            ("hypernym", "substance"),
            ("meronym", "hydrogen"),
            ("meronym", "oxygen"),
            ("holonym", "ocean"),
            ("holonym", "river"),
            ("holonym", "lake"),
            ("causes", "erosion"),
            ("causes", "growth"),
        ],
    },
    "liquid": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "a substance that flows freely, having constant volume",
        "relations": [
            ("hypernym", "substance"),
            ("hyponym", "water"),
            ("hyponym", "oil"),
            ("antonym", "solid"),
            ("antonym", "gas"),
            ("derivation", "liquefy"),
            ("derivation", "liquidity"),
        ],
    },
    "flow": {
        "pos": "verb",
        "domain": "fluid",
        "definition": "to move steadily and continuously in a current",
        "relations": [
            ("hypernym", "move"),
            ("hyponym", "trickle"),
            ("hyponym", "gush"),
            ("hyponym", "stream"),
            ("antonym", "stagnate"),
            ("entails", "move"),
            ("derivation", "flow_n"),
            ("similar", "circulate"),
        ],
    },
    "freeze": {
        "pos": "verb",
        "domain": "fluid",
        "definition": "to change from liquid to solid by loss of heat",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "melt"),
            ("antonym", "thaw"),
            ("causes", "ice"),
            ("entails", "cool"),
            ("derivation", "frozen"),
            ("derivation", "freezing"),
        ],
    },
    "melt": {
        "pos": "verb",
        "domain": "fluid",
        "definition": "to change from solid to liquid by application of heat",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "freeze"),
            ("entails", "heat_v"),
            ("causes", "liquid"),
            ("derivation", "molten"),
        ],
    },
    "evaporate": {
        "pos": "verb",
        "domain": "fluid",
        "definition": "to change from liquid to gas",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "condense"),
            ("entails", "heat_v"),
            ("causes", "gas"),
            ("derivation", "evaporation"),
        ],
    },
    "condense": {
        "pos": "verb",
        "domain": "fluid",
        "definition": "to change from gas to liquid",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "evaporate"),
            ("entails", "cool"),
            ("causes", "liquid"),
            ("derivation", "condensation"),
        ],
    },
    "ice": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "frozen water; a solid form of water",
        "relations": [
            ("hypernym", "solid"),
            ("meronym", "crystal"),
            ("derivation", "icy"),
        ],
    },
    "river": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "a large natural stream of water flowing to the sea",
        "relations": [
            ("hypernym", "body_of_water"),
            ("meronym", "water"),
            ("meronym", "current"),
            ("meronym", "bank"),
            ("holonym", "watershed"),
        ],
    },
    "ocean": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "a very large expanse of sea",
        "relations": [
            ("hypernym", "body_of_water"),
            ("meronym", "water"),
            ("meronym", "wave"),
            ("meronym", "tide"),
            ("meronym", "current"),
        ],
    },
    "pressure": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "continuous physical force exerted on a surface per unit area",
        "relations": [
            ("hypernym", "force"),
            ("causes", "flow"),
            ("antonym", "vacuum"),
            ("derivation", "pressurize"),
        ],
    },
    "current": {
        "pos": "noun",
        "domain": "fluid",
        "definition": "a body of water or air moving in a definite direction",
        "relations": [
            ("hypernym", "flow_n"),
            ("causes", "erosion"),
        ],
    },

    # ══════════════════════════════════════════════════════
    # DOMAIN: LIGHT / VISION
    # ══════════════════════════════════════════════════════
    "light": {
        "pos": "noun",
        "domain": "light",
        "definition": "electromagnetic radiation that is visible to the eye",
        "relations": [
            ("hypernym", "radiation"),
            ("hypernym", "energy"),
            ("meronym", "photon"),
            ("antonym", "darkness"),
            ("causes", "illumination"),
            ("causes", "vision"),
            ("derivation", "lighten"),
            ("derivation", "luminous"),
        ],
    },
    "darkness": {
        "pos": "noun",
        "domain": "light",
        "definition": "the absence of light",
        "relations": [
            ("hypernym", "absence"),
            ("antonym", "light"),
            ("antonym", "brightness"),
            ("causes", "blindness"),
            ("derivation", "darken"),
        ],
    },
    "shine": {
        "pos": "verb",
        "domain": "light",
        "definition": "to emit or reflect light; to glow brightly",
        "relations": [
            ("hypernym", "emit"),
            ("hyponym", "glow"),
            ("hyponym", "glitter"),
            ("hyponym", "sparkle"),
            ("antonym", "dim_v"),
            ("entails", "emit"),
            ("derivation", "shiny"),
            ("similar", "radiate"),
        ],
    },
    "glow": {
        "pos": "verb",
        "domain": "light",
        "definition": "to emit a steady light without flame",
        "relations": [
            ("hypernym", "shine"),
            ("antonym", "dim_v"),
            ("derivation", "glow_n"),
        ],
    },
    "illuminate": {
        "pos": "verb",
        "domain": "light",
        "definition": "to light up; to make visible or bright",
        "relations": [
            ("hypernym", "light_v"),
            ("antonym", "obscure"),
            ("causes", "visibility"),
            ("derivation", "illumination"),
        ],
    },
    "shadow": {
        "pos": "noun",
        "domain": "light",
        "definition": "a dark area produced by a body blocking light",
        "relations": [
            ("hypernym", "shade"),
            ("antonym", "light"),
            ("causes", "darkness"),
            ("entails", "block"),
            ("derivation", "shadowy"),
        ],
    },
    "color": {
        "pos": "noun",
        "domain": "light",
        "definition": "the property of light as perceived by vision",
        "relations": [
            ("hypernym", "property"),
            ("hyponym", "red"),
            ("hyponym", "blue"),
            ("hyponym", "green"),
            ("meronym", "hue"),
            ("meronym", "saturation"),
            ("meronym", "brightness"),
        ],
    },
    "reflect": {
        "pos": "verb",
        "domain": "light",
        "definition": "to throw back light without absorbing it",
        "relations": [
            ("hypernym", "return"),
            ("antonym", "absorb"),
            ("derivation", "reflection"),
            ("derivation", "reflective"),
        ],
    },
    "absorb": {
        "pos": "verb",
        "domain": "light",
        "definition": "to take in energy without reflecting or transmitting",
        "relations": [
            ("hypernym", "take_in"),
            ("antonym", "reflect"),
            ("antonym", "emit"),
            ("derivation", "absorption"),
        ],
    },
    "bright": {
        "pos": "adj",
        "domain": "light",
        "definition": "emitting or reflecting much light",
        "relations": [
            ("synonym", "luminous"),
            ("synonym", "radiant"),
            ("antonym", "dim"),
            ("antonym", "dark"),
            ("derivation", "brightness"),
            ("derivation", "brighten"),
        ],
    },
    "dim": {
        "pos": "adj",
        "domain": "light",
        "definition": "not bright; giving little light",
        "relations": [
            ("synonym", "faint"),
            ("antonym", "bright"),
            ("derivation", "dimness"),
            ("derivation", "dim_v"),
        ],
    },

    # ══════════════════════════════════════════════════════
    # DOMAIN: KNOWLEDGE / LEARNING
    # ══════════════════════════════════════════════════════
    "knowledge": {
        "pos": "noun",
        "domain": "knowledge",
        "definition": "facts, information, and skills acquired through experience or education",
        "relations": [
            ("hypernym", "cognition"),
            ("antonym", "ignorance"),
            ("meronym", "fact"),
            ("meronym", "understanding"),
            ("meronym", "skill"),
            ("derivation", "know"),
            ("derivation", "knowledgeable"),
        ],
    },
    "ignorance": {
        "pos": "noun",
        "domain": "knowledge",
        "definition": "lack of knowledge or information",
        "relations": [
            ("hypernym", "absence"),
            ("antonym", "knowledge"),
            ("antonym", "wisdom"),
            ("derivation", "ignorant"),
        ],
    },
    "learn": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to gain knowledge or skill through study or experience",
        "relations": [
            ("hypernym", "acquire"),
            ("hyponym", "study"),
            ("hyponym", "memorize"),
            ("hyponym", "absorb_k"),
            ("antonym", "forget"),
            ("entails", "study"),
            ("derivation", "learner"),
            ("derivation", "learning"),
            ("similar", "understand"),
        ],
    },
    "teach": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to impart knowledge to or instruct someone",
        "relations": [
            ("hypernym", "communicate"),
            ("hyponym", "instruct"),
            ("hyponym", "tutor"),
            ("antonym", "learn"),
            ("causes", "learn"),
            ("entails", "know"),
            ("derivation", "teacher"),
            ("derivation", "teaching"),
        ],
    },
    "understand": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to perceive the meaning of; to grasp with the mind",
        "relations": [
            ("hypernym", "know"),
            ("antonym", "misunderstand"),
            ("entails", "learn"),
            ("derivation", "understanding"),
            ("derivation", "comprehension"),
        ],
    },
    "forget": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to fail to remember",
        "relations": [
            ("hypernym", "fail"),
            ("antonym", "remember"),
            ("antonym", "learn"),
            ("derivation", "forgetful"),
            ("derivation", "forgetting"),
        ],
    },
    "wisdom": {
        "pos": "noun",
        "domain": "knowledge",
        "definition": "the quality of having experience, knowledge, and good judgment",
        "relations": [
            ("hypernym", "knowledge"),
            ("antonym", "folly"),
            ("antonym", "ignorance"),
            ("derivation", "wise"),
        ],
    },
    "discover": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to find or learn something for the first time",
        "relations": [
            ("hypernym", "learn"),
            ("causes", "knowledge"),
            ("derivation", "discovery"),
            ("derivation", "discoverer"),
        ],
    },
    "idea": {
        "pos": "noun",
        "domain": "knowledge",
        "definition": "a thought or suggestion about a possible course of action",
        "relations": [
            ("hypernym", "thought"),
            ("hyponym", "concept"),
            ("hyponym", "theory"),
            ("hyponym", "hypothesis"),
            ("derivation", "ideate"),
        ],
    },
    "reason": {
        "pos": "verb",
        "domain": "knowledge",
        "definition": "to think logically; to form judgments by a process of logic",
        "relations": [
            ("hypernym", "think"),
            ("entails", "think"),
            ("causes", "conclusion"),
            ("derivation", "reasoning"),
            ("derivation", "rational"),
        ],
    },
    "conclusion": {
        "pos": "noun",
        "domain": "knowledge",
        "definition": "a judgment reached by reasoning",
        "relations": [
            ("hypernym", "judgment"),
            ("antonym", "premise"),
            ("derivation", "conclude"),
        ],
    },

    # ══════════════════════════════════════════════════════
    # DOMAIN: BODY / HEALTH
    # ══════════════════════════════════════════════════════
    "body": {
        "pos": "noun",
        "domain": "body",
        "definition": "the physical structure of a person or animal",
        "relations": [
            ("hypernym", "organism"),
            ("meronym", "heart"),
            ("meronym", "blood"),
            ("meronym", "bone"),
            ("meronym", "muscle"),
            ("meronym", "skin"),
            ("meronym", "brain"),
        ],
    },
    "heart": {
        "pos": "noun",
        "domain": "body",
        "definition": "the organ that pumps blood through the circulatory system",
        "relations": [
            ("hypernym", "organ"),
            ("holonym", "body"),
            ("meronym", "ventricle"),
            ("meronym", "atrium"),
            ("meronym", "valve"),
            ("causes", "circulation"),
        ],
    },
    "blood": {
        "pos": "noun",
        "domain": "body",
        "definition": "the red liquid circulating in arteries and veins",
        "relations": [
            ("hypernym", "fluid"),
            ("holonym", "body"),
            ("meronym", "plasma"),
            ("meronym", "cell"),
            ("derivation", "bleed"),
            ("derivation", "bloody"),
        ],
    },
    "heal": {
        "pos": "verb",
        "domain": "body",
        "definition": "to restore to health; to become well again",
        "relations": [
            ("hypernym", "restore"),
            ("antonym", "wound_v"),
            ("antonym", "injure"),
            ("causes", "health"),
            ("derivation", "healer"),
            ("derivation", "healing"),
        ],
    },
    "wound": {
        "pos": "noun",
        "domain": "body",
        "definition": "an injury to living tissue caused by a cut, blow, or impact",
        "relations": [
            ("hypernym", "injury"),
            ("antonym", "healing"),
            ("causes", "pain"),
            ("causes", "bleed"),
            ("derivation", "wound_v"),
        ],
    },
    "disease": {
        "pos": "noun",
        "domain": "body",
        "definition": "a disorder of structure or function in a living organism",
        "relations": [
            ("hypernym", "disorder"),
            ("antonym", "health"),
            ("causes", "pain"),
            ("causes", "weakness"),
            ("derivation", "diseased"),
        ],
    },
    "health": {
        "pos": "noun",
        "domain": "body",
        "definition": "the state of being free from illness or injury",
        "relations": [
            ("hypernym", "condition"),
            ("antonym", "disease"),
            ("antonym", "illness"),
            ("derivation", "healthy"),
            ("derivation", "heal"),
        ],
    },
    "breathe": {
        "pos": "verb",
        "domain": "body",
        "definition": "to take air into the lungs and expel it",
        "relations": [
            ("hypernym", "respire"),
            ("hyponym", "inhale"),
            ("hyponym", "exhale"),
            ("antonym", "suffocate"),
            ("entails", "inhale"),
            ("derivation", "breath"),
            ("derivation", "breathing"),
        ],
    },
    "pain": {
        "pos": "noun",
        "domain": "body",
        "definition": "a highly unpleasant physical sensation caused by illness or injury",
        "relations": [
            ("hypernym", "sensation"),
            ("antonym", "pleasure"),
            ("antonym", "comfort"),
            ("derivation", "painful"),
        ],
    },
    "grow": {
        "pos": "verb",
        "domain": "body",
        "definition": "to increase in size or develop to maturity",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "shrink"),
            ("antonym", "decay"),
            ("causes", "growth"),
            ("derivation", "growth"),
            ("derivation", "grower"),
        ],
    },
    "decay": {
        "pos": "verb",
        "domain": "body",
        "definition": "to decompose; to decline from a state of soundness",
        "relations": [
            ("hypernym", "change_state"),
            ("antonym", "grow"),
            ("antonym", "flourish"),
            ("causes", "death"),
            ("derivation", "decay_n"),
            ("derivation", "decayed"),
        ],
    },

    # ══════════════════════════════════════════════════════
    # DOMAIN: GOVERNANCE / AUTHORITY
    # ══════════════════════════════════════════════════════
    "govern": {
        "pos": "verb",
        "domain": "governance",
        "definition": "to conduct the policy and affairs of a state or organization",
        "relations": [
            ("hypernym", "control"),
            ("hyponym", "rule"),
            ("hyponym", "administer"),
            ("antonym", "obey"),
            ("causes", "order"),
            ("derivation", "governor"),
            ("derivation", "government"),
            ("derivation", "governance"),
        ],
    },
    "law": {
        "pos": "noun",
        "domain": "governance",
        "definition": "a system of rules recognized by a community as regulating conduct",
        "relations": [
            ("hypernym", "rule_n"),
            ("hyponym", "statute"),
            ("hyponym", "ordinance"),
            ("antonym", "anarchy"),
            ("meronym", "clause"),
            ("derivation", "lawful"),
            ("derivation", "legal"),
        ],
    },
    "citizen": {
        "pos": "noun",
        "domain": "governance",
        "definition": "a legally recognized member of a state or nation",
        "relations": [
            ("hypernym", "person"),
            ("antonym", "alien"),
            ("holonym", "nation"),
            ("derivation", "citizenship"),
        ],
    },
    "obey": {
        "pos": "verb",
        "domain": "governance",
        "definition": "to comply with a command, rule, or law",
        "relations": [
            ("hypernym", "comply"),
            ("antonym", "disobey"),
            ("antonym", "rebel"),
            ("entails", "submit"),
            ("derivation", "obedient"),
            ("derivation", "obedience"),
        ],
    },
    "rebel": {
        "pos": "verb",
        "domain": "governance",
        "definition": "to resist or rise against authority or control",
        "relations": [
            ("hypernym", "resist"),
            ("antonym", "obey"),
            ("antonym", "submit"),
            ("causes", "conflict"),
            ("derivation", "rebel_n"),
            ("derivation", "rebellion"),
        ],
    },
    "justice": {
        "pos": "noun",
        "domain": "governance",
        "definition": "the quality of being fair and reasonable",
        "relations": [
            ("hypernym", "fairness"),
            ("antonym", "injustice"),
            ("derivation", "just"),
            ("derivation", "justify"),
        ],
    },
    "freedom": {
        "pos": "noun",
        "domain": "governance",
        "definition": "the state of being free from restriction or oppression",
        "relations": [
            ("hypernym", "condition"),
            ("antonym", "slavery"),
            ("antonym", "oppression"),
            ("derivation", "free"),
            ("derivation", "liberate"),
        ],
    },
    "order": {
        "pos": "noun",
        "domain": "governance",
        "definition": "the arrangement of people or things according to a system",
        "relations": [
            ("hypernym", "arrangement"),
            ("antonym", "chaos"),
            ("antonym", "disorder"),
            ("derivation", "orderly"),
        ],
    },

    # ══════════════════════════════════════════════════════
    # SHARED / ABSTRACT (appear across domains)
    # ══════════════════════════════════════════════════════
    "change_state": {
        "pos": "verb",
        "domain": "abstract",
        "definition": "to undergo a transformation from one state to another",
        "relations": [
            ("hypernym", "change"),
            ("hyponym", "freeze"),
            ("hyponym", "melt"),
            ("hyponym", "evaporate"),
            ("hyponym", "grow"),
            ("hyponym", "decay"),
        ],
    },
    "substance": {
        "pos": "noun",
        "domain": "abstract",
        "definition": "a particular kind of matter with uniform properties",
        "relations": [
            ("hyponym", "solid"),
            ("hyponym", "liquid"),
            ("hyponym", "gas"),
        ],
    },
    "solid": {
        "pos": "noun",
        "domain": "abstract",
        "definition": "a substance firm and stable in shape",
        "relations": [
            ("hypernym", "substance"),
            ("antonym", "liquid"),
            ("antonym", "gas"),
        ],
    },
    "gas": {
        "pos": "noun",
        "domain": "abstract",
        "definition": "a substance that expands freely to fill any available space",
        "relations": [
            ("hypernym", "substance"),
            ("antonym", "solid"),
            ("antonym", "liquid"),
        ],
    },
    "energy": {
        "pos": "noun",
        "domain": "abstract",
        "definition": "the capacity for doing work",
        "relations": [
            ("hyponym", "light"),
            ("hyponym", "heat_n"),
            ("hyponym", "sound"),
            ("antonym", "inertia"),
        ],
    },
    "move": {
        "pos": "verb",
        "domain": "abstract",
        "definition": "to change position or go from one place to another",
        "relations": [
            ("hyponym", "flow"),
            ("hyponym", "walk"),
            ("hyponym", "fly"),
            ("antonym", "stay"),
            ("derivation", "movement"),
        ],
    },
    "absence": {
        "pos": "noun",
        "domain": "abstract",
        "definition": "the state of something being not present",
        "relations": [
            ("antonym", "presence"),
            ("hyponym", "darkness"),
            ("hyponym", "ignorance"),
            ("hyponym", "silence"),
        ],
    },
}


def get_domains():
    """Return set of all domains in the lexicon."""
    return set(entry["domain"] for entry in LEXICON.values())


def get_words_in_domain(domain):
    """Return all words belonging to a domain."""
    return [word for word, entry in LEXICON.items() if entry["domain"] == domain]


def get_relationships_between(words):
    """Get all relationships where both endpoints are in the word set."""
    rels = []
    word_set = set(words)
    for word in words:
        entry = LEXICON.get(word, {})
        for rel_type, target in entry.get("relations", []):
            if target in word_set:
                rels.append((word, rel_type, target))
    return rels


def get_all_relationship_types():
    """Return all unique relationship types in the lexicon."""
    types = set()
    for entry in LEXICON.values():
        for rel_type, _ in entry.get("relations", []):
            types.add(rel_type)
    return types


def stats():
    """Print lexicon statistics."""
    words = len(LEXICON)
    domains = get_domains()
    total_rels = sum(len(e.get("relations", [])) for e in LEXICON.values())
    rel_types = get_all_relationship_types()

    print(f"Lexicon: {words} entries across {len(domains)} domains")
    print(f"Domains: {', '.join(sorted(domains))}")
    print(f"Total relationships: {total_rels}")
    print(f"Relationship types: {', '.join(sorted(rel_types))}")
    for domain in sorted(domains):
        domain_words = get_words_in_domain(domain)
        domain_rels = get_relationships_between(domain_words)
        print(f"  {domain}: {len(domain_words)} words, {len(domain_rels)} internal relationships")


if __name__ == "__main__":
    stats()
