"""
MORPHOS Linguistic & Computational Knowledge Base

Real data for:
1. GRAMMAR: Parts of speech, phrase structure, dependency relations
2. IPA PHONETICS: Full IPA chart with articulatory features
3. SEMANTICS: Thematic roles, semantic fields, compositional semantics
4. UNICODE: Block structure, encoding relationships, script families
5. PROGRAMMING LANGUAGES: Type systems, paradigms, feature relationships
6. LINGUISTIC MATHEMATICS: Formal language hierarchy, automata correspondence
7. CELTIC LINGUISTICS: Irish/Cornish mutation systems, verb morphology

All data from standard references:
- IPA: International Phonetic Association (2015 chart)
- Grammar: Chomsky hierarchy, X-bar theory, Universal Dependencies
- Unicode: The Unicode Standard, Version 15.0
- PLT: Pierce (Types and Programming Languages), TIOBE
"""
from __future__ import annotations


# ══════════════════════════════════════════════════════════════
# 1. GRAMMAR — Syntactic categories, phrase structure, dependencies
# Source: Universal Dependencies, X-bar theory, Chomsky
# ══════════════════════════════════════════════════════════════

def grammar_structure() -> dict:
    """Syntactic structure: POS tags, phrase rules, dependency relations."""
    return {
        "name": "Grammar",
        "objects": [
            # Parts of speech (Universal Dependencies tagset)
            "NOUN", "VERB", "ADJ", "ADV", "DET", "PRON", "ADP",
            "CONJ", "NUM", "PART", "INTJ", "AUX", "PUNCT",
            # Phrase types
            "NP", "VP", "AP", "AdvP", "PP", "CP", "IP", "DP",
            "S", "S_bar",
            # Grammatical functions
            "subject", "object_gf", "indirect_object",
            "predicate", "complement", "adjunct", "specifier",
            "head", "modifier", "determiner_fn",
            # Clause types
            "declarative", "interrogative", "imperative", "exclamative",
            "relative_clause", "complement_clause", "adverbial_clause",
            # Morphological features
            "tense", "aspect", "mood", "number", "person",
            "case", "gender", "voice",
            "present", "past", "future",
            "singular", "plural",
            "nominative", "accusative", "dative", "genitive",
            "active", "passive",
            "indicative", "subjunctive", "conditional",
            # Agreement
            "agreement", "government", "binding",
        ],
        "morphisms": [
            # POS → Phrase projection (X-bar theory)
            ("projects_to", "NOUN", "NP"), ("projects_to", "VERB", "VP"),
            ("projects_to", "ADJ", "AP"), ("projects_to", "ADV", "AdvP"),
            ("projects_to", "ADP", "PP"), ("projects_to", "DET", "DP"),

            # Phrase → Clause
            ("combines_to", "NP", "S"), ("combines_to", "VP", "S"),
            ("combines_to", "NP", "IP"), ("combines_to", "VP", "IP"),
            ("combines_to", "CP", "S_bar"),

            # Head relations
            ("head_of", "NOUN", "NP"), ("head_of", "VERB", "VP"),
            ("head_of", "ADJ", "AP"), ("head_of", "ADP", "PP"),

            # Dependency relations (Universal Dependencies)
            ("dep_nsubj", "NP", "subject"),
            ("dep_obj", "NP", "object_gf"),
            ("dep_iobj", "NP", "indirect_object"),
            ("dep_obl", "PP", "adjunct"),
            ("dep_amod", "AP", "modifier"),
            ("dep_advmod", "AdvP", "modifier"),
            ("dep_det", "DP", "determiner_fn"),
            ("dep_nmod", "PP", "modifier"),

            # Grammatical function → Phrase
            ("realized_by", "subject", "NP"),
            ("realized_by", "predicate", "VP"),
            ("realized_by", "object_gf", "NP"),
            ("realized_by", "complement", "CP"),
            ("realized_by", "adjunct", "PP"),
            ("realized_by", "adjunct", "AdvP"),
            ("realized_by", "specifier", "DP"),

            # Clause types → Features
            ("has_feature", "declarative", "indicative"),
            ("has_feature", "interrogative", "indicative"),
            ("has_feature", "imperative", "mood"),
            ("has_feature", "relative_clause", "complement"),

            # Morphological feature hierarchy
            ("instance_of", "present", "tense"),
            ("instance_of", "past", "tense"),
            ("instance_of", "future", "tense"),
            ("instance_of", "singular", "number"),
            ("instance_of", "plural", "number"),
            ("instance_of", "nominative", "case"),
            ("instance_of", "accusative", "case"),
            ("instance_of", "dative", "case"),
            ("instance_of", "genitive", "case"),
            ("instance_of", "active", "voice"),
            ("instance_of", "passive", "voice"),
            ("instance_of", "indicative", "mood"),
            ("instance_of", "subjunctive", "mood"),
            ("instance_of", "conditional", "mood"),

            # Verb morphology requires
            ("requires", "VERB", "tense"),
            ("requires", "VERB", "aspect"),
            ("requires", "VERB", "mood"),
            ("requires", "VERB", "voice"),
            ("requires", "NOUN", "number"),
            ("requires", "NOUN", "case"),
            ("requires", "PRON", "person"),
            ("requires", "PRON", "number"),
            ("requires", "PRON", "case"),

            # Agreement relations
            ("triggers", "subject", "agreement"),
            ("target_of", "VERB", "agreement"),
            ("governs", "VERB", "object_gf"),
            ("governs", "ADP", "complement"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 2. IPA PHONETICS — Articulatory feature system
# Source: IPA Chart (International Phonetic Association, 2015)
# ══════════════════════════════════════════════════════════════

def ipa_phonetics() -> dict:
    """IPA consonants and vowels with full articulatory features."""
    return {
        "name": "IPA_Phonetics",
        "objects": [
            # Consonants (selected inventory)
            "p", "b", "t", "d", "k", "ɡ", "ʔ",          # plosives
            "m", "n", "ŋ", "ɲ",                            # nasals
            "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", # fricatives
            "tʃ", "dʒ",                                     # affricates
            "ɹ", "l", "j", "w",                             # approximants
            "ɾ", "r",                                        # rhotics
            # Vowels
            "i", "ɪ", "e", "ɛ", "æ", "ɑ", "ɒ", "ɔ",
            "o", "ʊ", "u", "ə", "ʌ",
            # Diphthongs
            "aɪ", "aʊ", "ɔɪ", "eɪ", "oʊ",
            # Manner of articulation
            "plosive", "fricative", "affricate", "nasal",
            "approximant", "lateral", "trill", "tap",
            # Place of articulation
            "bilabial", "labiodental", "dental", "alveolar",
            "postalveolar", "palatal", "velar", "glottal",
            # Voicing
            "voiced", "voiceless",
            # Vowel features
            "high", "mid", "low",
            "front", "central", "back",
            "rounded", "unrounded",
            # Suprasegmental
            "stress", "intonation", "tone", "length",
            "syllable", "onset", "nucleus", "coda",
        ],
        "morphisms": [
            # Consonant → Manner
            ("manner", "p", "plosive"), ("manner", "b", "plosive"),
            ("manner", "t", "plosive"), ("manner", "d", "plosive"),
            ("manner", "k", "plosive"), ("manner", "ɡ", "plosive"),
            ("manner", "ʔ", "plosive"),
            ("manner", "m", "nasal"), ("manner", "n", "nasal"),
            ("manner", "ŋ", "nasal"), ("manner", "ɲ", "nasal"),
            ("manner", "f", "fricative"), ("manner", "v", "fricative"),
            ("manner", "θ", "fricative"), ("manner", "ð", "fricative"),
            ("manner", "s", "fricative"), ("manner", "z", "fricative"),
            ("manner", "ʃ", "fricative"), ("manner", "ʒ", "fricative"),
            ("manner", "h", "fricative"),
            ("manner", "tʃ", "affricate"), ("manner", "dʒ", "affricate"),
            ("manner", "ɹ", "approximant"), ("manner", "l", "lateral"),
            ("manner", "j", "approximant"), ("manner", "w", "approximant"),
            ("manner", "ɾ", "tap"), ("manner", "r", "trill"),

            # Consonant → Place
            ("place", "p", "bilabial"), ("place", "b", "bilabial"),
            ("place", "m", "bilabial"),
            ("place", "f", "labiodental"), ("place", "v", "labiodental"),
            ("place", "θ", "dental"), ("place", "ð", "dental"),
            ("place", "t", "alveolar"), ("place", "d", "alveolar"),
            ("place", "n", "alveolar"), ("place", "s", "alveolar"),
            ("place", "z", "alveolar"), ("place", "l", "alveolar"),
            ("place", "ɹ", "alveolar"), ("place", "ɾ", "alveolar"),
            ("place", "ʃ", "postalveolar"), ("place", "ʒ", "postalveolar"),
            ("place", "tʃ", "postalveolar"), ("place", "dʒ", "postalveolar"),
            ("place", "ɲ", "palatal"), ("place", "j", "palatal"),
            ("place", "k", "velar"), ("place", "ɡ", "velar"),
            ("place", "ŋ", "velar"), ("place", "w", "velar"),
            ("place", "ʔ", "glottal"), ("place", "h", "glottal"),

            # Consonant → Voicing
            ("voicing", "p", "voiceless"), ("voicing", "b", "voiced"),
            ("voicing", "t", "voiceless"), ("voicing", "d", "voiced"),
            ("voicing", "k", "voiceless"), ("voicing", "ɡ", "voiced"),
            ("voicing", "f", "voiceless"), ("voicing", "v", "voiced"),
            ("voicing", "θ", "voiceless"), ("voicing", "ð", "voiced"),
            ("voicing", "s", "voiceless"), ("voicing", "z", "voiced"),
            ("voicing", "ʃ", "voiceless"), ("voicing", "ʒ", "voiced"),
            ("voicing", "tʃ", "voiceless"), ("voicing", "dʒ", "voiced"),
            ("voicing", "m", "voiced"), ("voicing", "n", "voiced"),
            ("voicing", "ŋ", "voiced"), ("voicing", "ɾ", "voiced"),
            ("voicing", "ɹ", "voiced"), ("voicing", "l", "voiced"),

            # Voiced-voiceless pairs (phonological opposition)
            ("voice_pair", "p", "b"), ("voice_pair", "b", "p"),
            ("voice_pair", "t", "d"), ("voice_pair", "d", "t"),
            ("voice_pair", "k", "ɡ"), ("voice_pair", "ɡ", "k"),
            ("voice_pair", "f", "v"), ("voice_pair", "v", "f"),
            ("voice_pair", "θ", "ð"), ("voice_pair", "ð", "θ"),
            ("voice_pair", "s", "z"), ("voice_pair", "z", "s"),
            ("voice_pair", "ʃ", "ʒ"), ("voice_pair", "ʒ", "ʃ"),
            ("voice_pair", "tʃ", "dʒ"), ("voice_pair", "dʒ", "tʃ"),

            # Vowels → Height
            ("height", "i", "high"), ("height", "ɪ", "high"),
            ("height", "u", "high"), ("height", "ʊ", "high"),
            ("height", "e", "mid"), ("height", "ə", "mid"),
            ("height", "o", "mid"), ("height", "ɔ", "mid"),
            ("height", "ɛ", "mid"),
            ("height", "æ", "low"), ("height", "ɑ", "low"),
            ("height", "ɒ", "low"), ("height", "ʌ", "low"),

            # Vowels → Backness
            ("backness", "i", "front"), ("backness", "ɪ", "front"),
            ("backness", "e", "front"), ("backness", "ɛ", "front"),
            ("backness", "æ", "front"),
            ("backness", "ə", "central"), ("backness", "ʌ", "central"),
            ("backness", "u", "back"), ("backness", "ʊ", "back"),
            ("backness", "o", "back"), ("backness", "ɔ", "back"),
            ("backness", "ɑ", "back"), ("backness", "ɒ", "back"),

            # Vowels → Rounding
            ("rounding", "i", "unrounded"), ("rounding", "e", "unrounded"),
            ("rounding", "ɛ", "unrounded"), ("rounding", "æ", "unrounded"),
            ("rounding", "ɑ", "unrounded"),
            ("rounding", "u", "rounded"), ("rounding", "o", "rounded"),
            ("rounding", "ɔ", "rounded"), ("rounding", "ɒ", "rounded"),

            # Syllable structure
            ("syllable_role", "onset", "syllable"),
            ("syllable_role", "nucleus", "syllable"),
            ("syllable_role", "coda", "syllable"),
            ("fills", "plosive", "onset"), ("fills", "fricative", "onset"),
            ("fills", "nasal", "onset"), ("fills", "nasal", "coda"),
            ("fills", "fricative", "coda"), ("fills", "plosive", "coda"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 3. SEMANTICS — Thematic roles, semantic relations, compositionality
# Source: Dowty (1991), Jackendoff, FrameNet
# ══════════════════════════════════════════════════════════════

def semantic_structure() -> dict:
    """Semantic roles, relations, and compositional semantics."""
    return {
        "name": "Semantics",
        "objects": [
            # Thematic roles (theta roles)
            "Agent", "Patient", "Theme", "Experiencer", "Beneficiary",
            "Instrument", "Location", "Source_role", "Goal", "Stimulus",
            "Recipient", "Cause_role",
            # Semantic relations
            "hyponymy", "meronymy", "antonymy", "synonymy",
            "polysemy", "homonymy", "metonymy", "metaphor",
            # Semantic features
            "animate", "inanimate", "human", "concrete", "abstract_sem",
            "countable", "mass", "telic", "atelic",
            # Event types (Vendler)
            "state", "activity", "accomplishment", "achievement",
            # Aspect
            "perfective", "imperfective", "progressive", "habitual",
            # Logic
            "proposition", "predicate_logic", "argument",
            "quantifier", "universal", "existential",
            "negation", "conjunction", "disjunction", "implication",
            # Pragmatics
            "presupposition", "implicature", "speech_act",
            "assertion", "question", "command", "promise",
            "declarative", "interrogative", "imperative",
            # Compositionality
            "compositionality", "type_raising", "function_application",
        ],
        "morphisms": [
            # Thematic role hierarchy
            ("entails", "Agent", "animate"),
            ("entails", "Agent", "Cause_role"),
            ("entails", "Patient", "Theme"),
            ("entails", "Experiencer", "animate"),
            ("entails", "Recipient", "animate"),
            ("entails", "Instrument", "inanimate"),

            # Event type → Aspectual properties
            ("has_aspect", "state", "atelic"),
            ("has_aspect", "activity", "atelic"),
            ("has_aspect", "accomplishment", "telic"),
            ("has_aspect", "achievement", "telic"),
            ("compatible", "state", "imperfective"),
            ("compatible", "activity", "progressive"),
            ("compatible", "accomplishment", "perfective"),
            ("compatible", "achievement", "perfective"),

            # Semantic relation types
            ("is_structural", "hyponymy", "compositionality"),
            ("is_structural", "meronymy", "compositionality"),
            ("is_figurative", "metaphor", "polysemy"),
            ("is_figurative", "metonymy", "polysemy"),
            ("inverse", "hyponymy", "hyponymy"),  # hypernymy is inverse
            ("inverse", "antonymy", "antonymy"),   # symmetric
            ("inverse", "synonymy", "synonymy"),   # symmetric

            # Logical connectives
            ("IsA", "universal", "quantifier"),
            ("IsA", "existential", "quantifier"),
            ("IsA", "negation", "predicate_logic"),
            ("IsA", "conjunction", "predicate_logic"),
            ("IsA", "disjunction", "predicate_logic"),
            ("IsA", "implication", "predicate_logic"),

            # Speech acts (Austin/Searle)
            ("IsA", "assertion", "speech_act"),
            ("IsA", "question", "speech_act"),
            ("IsA", "command", "speech_act"),
            ("IsA", "promise", "speech_act"),
            ("expresses", "declarative", "assertion"),
            ("expresses", "interrogative", "question"),
            ("expresses", "imperative", "command"),

            # Compositionality
            ("operation", "function_application", "compositionality"),
            ("operation", "type_raising", "compositionality"),
            ("input", "predicate_logic", "function_application"),
            ("input", "argument", "function_application"),
            ("output", "function_application", "proposition"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 4. UNICODE — Block structure, script families, encoding
# Source: Unicode Standard 15.0
# ══════════════════════════════════════════════════════════════

def unicode_structure() -> dict:
    """Unicode block structure, script relationships, and encoding."""
    return {
        "name": "Unicode",
        "objects": [
            # Scripts
            "Latin", "Greek", "Cyrillic", "Arabic", "Hebrew",
            "Devanagari", "CJK", "Hangul", "Hiragana", "Katakana",
            "Thai", "Georgian", "Armenian", "Ethiopic",
            "Ogham", "Runic", "Cherokee", "Tibetan",
            # Script families
            "alphabetic", "abjad", "abugida", "syllabary",
            "logographic", "featural",
            # Unicode blocks (representative)
            "Basic_Latin", "Latin_Extended_A", "Latin_Extended_B",
            "IPA_Extensions", "Greek_and_Coptic", "Cyrillic_block",
            "Arabic_block", "Devanagari_block", "CJK_Unified",
            "Hangul_Syllables", "Mathematical_Operators",
            "Arrows", "Box_Drawing", "Braille_Patterns",
            "Musical_Symbols", "Emoji",
            # Encoding
            "UTF_8", "UTF_16", "UTF_32", "ASCII", "ISO_8859_1",
            # Character categories (General Category)
            "Lu", "Ll", "Lt", "Lm", "Lo",  # Letter subcategories
            "Nd", "Nl", "No",               # Number
            "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po",  # Punctuation
            "Sm", "Sc", "Sk", "So",         # Symbol
            "Zs", "Zl", "Zp",              # Separator
            "Cc", "Cf",                      # Control/Format
            # Higher categories
            "Letter", "Number_cat", "Punctuation_cat",
            "Symbol_cat", "Separator", "Other_cat",
            # Properties
            "bidirectional", "normalization", "case_mapping",
            "canonical_combining",
        ],
        "morphisms": [
            # Script → Family classification
            ("script_type", "Latin", "alphabetic"),
            ("script_type", "Greek", "alphabetic"),
            ("script_type", "Cyrillic", "alphabetic"),
            ("script_type", "Georgian", "alphabetic"),
            ("script_type", "Armenian", "alphabetic"),
            ("script_type", "Cherokee", "syllabary"),
            ("script_type", "Hiragana", "syllabary"),
            ("script_type", "Katakana", "syllabary"),
            ("script_type", "Arabic", "abjad"),
            ("script_type", "Hebrew", "abjad"),
            ("script_type", "Devanagari", "abugida"),
            ("script_type", "Thai", "abugida"),
            ("script_type", "Ethiopic", "abugida"),
            ("script_type", "Tibetan", "abugida"),
            ("script_type", "CJK", "logographic"),
            ("script_type", "Hangul", "featural"),

            # Script → Block
            ("in_block", "Latin", "Basic_Latin"),
            ("in_block", "Latin", "Latin_Extended_A"),
            ("in_block", "Latin", "Latin_Extended_B"),
            ("in_block", "Greek", "Greek_and_Coptic"),
            ("in_block", "Cyrillic", "Cyrillic_block"),
            ("in_block", "Arabic", "Arabic_block"),
            ("in_block", "Devanagari", "Devanagari_block"),
            ("in_block", "CJK", "CJK_Unified"),
            ("in_block", "Hangul", "Hangul_Syllables"),

            # Historical derivation between scripts
            ("derived_from", "Latin", "Greek"),
            ("derived_from", "Cyrillic", "Greek"),
            ("derived_from", "Greek", "Devanagari"),  # both from Proto-Sinaitic
            ("derived_from", "Arabic", "Hebrew"),      # Aramaic lineage
            ("derived_from", "Katakana", "CJK"),
            ("derived_from", "Hiragana", "CJK"),

            # Encoding relationships
            ("subset_of", "ASCII", "UTF_8"),
            ("subset_of", "ASCII", "ISO_8859_1"),
            ("subset_of", "ISO_8859_1", "UTF_8"),
            ("encodes", "UTF_8", "Latin"), ("encodes", "UTF_8", "CJK"),
            ("encodes", "UTF_8", "Arabic"), ("encodes", "UTF_8", "Emoji"),
            ("encodes", "UTF_16", "CJK"), ("encodes", "UTF_32", "CJK"),

            # General Category hierarchy
            ("subcategory", "Lu", "Letter"), ("subcategory", "Ll", "Letter"),
            ("subcategory", "Lt", "Letter"), ("subcategory", "Lm", "Letter"),
            ("subcategory", "Lo", "Letter"),
            ("subcategory", "Nd", "Number_cat"), ("subcategory", "Nl", "Number_cat"),
            ("subcategory", "Sm", "Symbol_cat"), ("subcategory", "Sc", "Symbol_cat"),
            ("subcategory", "Ps", "Punctuation_cat"), ("subcategory", "Pe", "Punctuation_cat"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 5. PROGRAMMING LANGUAGES — Type systems, paradigms, features
# Source: Pierce (TAPL), TIOBE Index, language specifications
# ══════════════════════════════════════════════════════════════

def programming_languages() -> dict:
    """Programming languages with type systems, paradigms, and features."""
    return {
        "name": "ProgrammingLanguages",
        "objects": [
            # Languages
            "Python", "JavaScript", "TypeScript", "Java", "C",
            "Cpp", "Rust", "Go", "Haskell", "OCaml", "Lisp",
            "Prolog", "SQL", "R_lang", "Julia", "Scala",
            "Kotlin", "Swift", "Perl", "Ruby", "Elixir",
            "Fortran", "COBOL", "Assembly",
            # Paradigms
            "imperative", "functional", "object_oriented",
            "logic_prog", "declarative_prog", "procedural",
            "concurrent", "metaprogramming",
            # Type system features
            "static_typing", "dynamic_typing", "strong_typing",
            "weak_typing", "type_inference", "dependent_types",
            "generics", "algebraic_types", "gradual_typing",
            # Memory management
            "garbage_collection", "manual_memory", "ownership",
            "reference_counting", "borrow_checker",
            # Evaluation
            "eager_eval", "lazy_eval", "strict_eval",
            # Compilation
            "compiled", "interpreted", "jit_compiled", "transpiled",
            # Abstractions
            "first_class_functions", "pattern_matching",
            "monads", "traits", "interfaces", "protocols",
            "macros", "closures", "coroutines",
        ],
        "morphisms": [
            # Language → Paradigm
            ("paradigm", "Python", "imperative"),
            ("paradigm", "Python", "object_oriented"),
            ("paradigm", "Python", "functional"),
            ("paradigm", "JavaScript", "imperative"),
            ("paradigm", "JavaScript", "object_oriented"),
            ("paradigm", "JavaScript", "functional"),
            ("paradigm", "TypeScript", "imperative"),
            ("paradigm", "TypeScript", "object_oriented"),
            ("paradigm", "Java", "object_oriented"),
            ("paradigm", "Java", "imperative"),
            ("paradigm", "C", "procedural"), ("paradigm", "C", "imperative"),
            ("paradigm", "Cpp", "object_oriented"), ("paradigm", "Cpp", "imperative"),
            ("paradigm", "Cpp", "functional"),
            ("paradigm", "Rust", "imperative"), ("paradigm", "Rust", "functional"),
            ("paradigm", "Rust", "concurrent"),
            ("paradigm", "Go", "imperative"), ("paradigm", "Go", "concurrent"),
            ("paradigm", "Haskell", "functional"),
            ("paradigm", "OCaml", "functional"), ("paradigm", "OCaml", "imperative"),
            ("paradigm", "Lisp", "functional"), ("paradigm", "Lisp", "metaprogramming"),
            ("paradigm", "Prolog", "logic_prog"), ("paradigm", "Prolog", "declarative_prog"),
            ("paradigm", "SQL", "declarative_prog"),
            ("paradigm", "Julia", "functional"), ("paradigm", "Julia", "imperative"),
            ("paradigm", "Scala", "functional"), ("paradigm", "Scala", "object_oriented"),
            ("paradigm", "Elixir", "functional"), ("paradigm", "Elixir", "concurrent"),
            ("paradigm", "Ruby", "object_oriented"),
            ("paradigm", "Kotlin", "object_oriented"), ("paradigm", "Kotlin", "functional"),
            ("paradigm", "Swift", "object_oriented"), ("paradigm", "Swift", "functional"),

            # Language → Type system
            ("type_system", "Python", "dynamic_typing"),
            ("type_system", "Python", "strong_typing"),
            ("type_system", "JavaScript", "dynamic_typing"),
            ("type_system", "JavaScript", "weak_typing"),
            ("type_system", "TypeScript", "static_typing"),
            ("type_system", "TypeScript", "gradual_typing"),
            ("type_system", "Java", "static_typing"),
            ("type_system", "Java", "strong_typing"),
            ("type_system", "C", "static_typing"),
            ("type_system", "C", "weak_typing"),
            ("type_system", "Cpp", "static_typing"),
            ("type_system", "Rust", "static_typing"),
            ("type_system", "Rust", "strong_typing"),
            ("type_system", "Rust", "algebraic_types"),
            ("type_system", "Go", "static_typing"),
            ("type_system", "Go", "strong_typing"),
            ("type_system", "Haskell", "static_typing"),
            ("type_system", "Haskell", "strong_typing"),
            ("type_system", "Haskell", "type_inference"),
            ("type_system", "Haskell", "algebraic_types"),
            ("type_system", "OCaml", "static_typing"),
            ("type_system", "OCaml", "type_inference"),
            ("type_system", "OCaml", "algebraic_types"),
            ("type_system", "Julia", "dynamic_typing"),
            ("type_system", "Julia", "strong_typing"),
            ("type_system", "Scala", "static_typing"),
            ("type_system", "Scala", "type_inference"),

            # Language → Memory management
            ("memory", "Python", "garbage_collection"),
            ("memory", "Java", "garbage_collection"),
            ("memory", "Go", "garbage_collection"),
            ("memory", "Haskell", "garbage_collection"),
            ("memory", "JavaScript", "garbage_collection"),
            ("memory", "C", "manual_memory"),
            ("memory", "Cpp", "manual_memory"),
            ("memory", "Rust", "ownership"),
            ("memory", "Rust", "borrow_checker"),
            ("memory", "Swift", "reference_counting"),

            # Language → Compilation
            ("compilation", "C", "compiled"), ("compilation", "Cpp", "compiled"),
            ("compilation", "Rust", "compiled"), ("compilation", "Go", "compiled"),
            ("compilation", "Haskell", "compiled"),
            ("compilation", "Java", "jit_compiled"),
            ("compilation", "Scala", "jit_compiled"),
            ("compilation", "Python", "interpreted"),
            ("compilation", "Ruby", "interpreted"),
            ("compilation", "JavaScript", "jit_compiled"),
            ("compilation", "TypeScript", "transpiled"),
            ("compilation", "Julia", "jit_compiled"),

            # Language → Features
            ("has_feature", "Haskell", "monads"),
            ("has_feature", "Haskell", "lazy_eval"),
            ("has_feature", "Haskell", "pattern_matching"),
            ("has_feature", "Rust", "pattern_matching"),
            ("has_feature", "Rust", "traits"),
            ("has_feature", "OCaml", "pattern_matching"),
            ("has_feature", "Scala", "pattern_matching"),
            ("has_feature", "Elixir", "pattern_matching"),
            ("has_feature", "Python", "first_class_functions"),
            ("has_feature", "JavaScript", "first_class_functions"),
            ("has_feature", "JavaScript", "closures"),
            ("has_feature", "Go", "coroutines"),
            ("has_feature", "Kotlin", "coroutines"),
            ("has_feature", "Java", "interfaces"),
            ("has_feature", "Go", "interfaces"),
            ("has_feature", "Swift", "protocols"),
            ("has_feature", "Lisp", "macros"),
            ("has_feature", "Rust", "macros"),
            ("has_feature", "Elixir", "macros"),
            ("has_feature", "Java", "generics"),
            ("has_feature", "Cpp", "generics"),
            ("has_feature", "Rust", "generics"),
            ("has_feature", "TypeScript", "generics"),

            # Influenced-by relationships
            ("influenced_by", "Python", "C"),
            ("influenced_by", "Python", "Haskell"),
            ("influenced_by", "JavaScript", "Lisp"),
            ("influenced_by", "JavaScript", "Java"),
            ("influenced_by", "TypeScript", "JavaScript"),
            ("influenced_by", "Rust", "Haskell"),
            ("influenced_by", "Rust", "Cpp"),
            ("influenced_by", "Rust", "OCaml"),
            ("influenced_by", "Go", "C"),
            ("influenced_by", "Julia", "Python"),
            ("influenced_by", "Julia", "Lisp"),
            ("influenced_by", "Julia", "Fortran"),
            ("influenced_by", "Kotlin", "Java"),
            ("influenced_by", "Kotlin", "Scala"),
            ("influenced_by", "Swift", "Rust"),
            ("influenced_by", "Swift", "Haskell"),
            ("influenced_by", "Scala", "Java"),
            ("influenced_by", "Scala", "Haskell"),
            ("influenced_by", "Elixir", "Ruby"),
            ("influenced_by", "Elixir", "Haskell"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 6. FORMAL LANGUAGE THEORY — Chomsky hierarchy, automata
# Source: Hopcroft/Ullman, Sipser
# ══════════════════════════════════════════════════════════════

def formal_language_theory() -> dict:
    """Chomsky hierarchy with automata correspondence."""
    return {
        "name": "FormalLanguageTheory",
        "objects": [
            # Language classes
            "regular", "context_free", "context_sensitive",
            "recursively_enumerable", "recursive",
            # Automata
            "DFA", "NFA", "PDA", "LBA", "Turing_machine",
            # Grammar types
            "regular_grammar", "CFG", "CSG", "unrestricted_grammar",
            # Operations
            "union_op", "concatenation", "Kleene_star",
            "intersection", "complement_op",
            # Properties
            "decidable", "undecidable", "closure_property",
            "pumping_lemma", "halting_problem",
            # Parsing
            "LL_parsing", "LR_parsing", "Earley_parsing",
            "CYK_parsing", "recursive_descent",
            # Complexity
            "P_class", "NP_class", "PSPACE", "EXPTIME",
        ],
        "morphisms": [
            # Chomsky hierarchy (strict containment)
            ("contains", "context_free", "regular"),
            ("contains", "context_sensitive", "context_free"),
            ("contains", "recursively_enumerable", "context_sensitive"),
            ("contains", "recursively_enumerable", "recursive"),
            ("contains", "recursive", "context_sensitive"),

            # Language ↔ Automaton correspondence (the key categorical insight)
            ("recognized_by", "regular", "DFA"),
            ("recognized_by", "regular", "NFA"),
            ("recognized_by", "context_free", "PDA"),
            ("recognized_by", "context_sensitive", "LBA"),
            ("recognized_by", "recursively_enumerable", "Turing_machine"),
            ("recognized_by", "recursive", "Turing_machine"),

            # Language ↔ Grammar correspondence
            ("generated_by", "regular", "regular_grammar"),
            ("generated_by", "context_free", "CFG"),
            ("generated_by", "context_sensitive", "CSG"),
            ("generated_by", "recursively_enumerable", "unrestricted_grammar"),

            # Automata power hierarchy
            ("simulated_by", "DFA", "NFA"),
            ("simulated_by", "NFA", "PDA"),
            ("simulated_by", "PDA", "LBA"),
            ("simulated_by", "LBA", "Turing_machine"),
            ("equivalent_to", "DFA", "NFA"),  # same power

            # Closure properties
            ("closed_under", "regular", "union_op"),
            ("closed_under", "regular", "concatenation"),
            ("closed_under", "regular", "Kleene_star"),
            ("closed_under", "regular", "intersection"),
            ("closed_under", "regular", "complement_op"),
            ("closed_under", "context_free", "union_op"),
            ("closed_under", "context_free", "concatenation"),
            ("closed_under", "context_free", "Kleene_star"),
            # CFL NOT closed under intersection or complement

            # Decidability
            ("has_property", "regular", "decidable"),
            ("has_property", "context_free", "decidable"),
            ("has_property", "recursive", "decidable"),
            ("has_property", "recursively_enumerable", "undecidable"),
            ("instance_of", "halting_problem", "undecidable"),

            # Parsing methods → Language classes
            ("parses", "LL_parsing", "context_free"),
            ("parses", "LR_parsing", "context_free"),
            ("parses", "Earley_parsing", "context_free"),
            ("parses", "CYK_parsing", "context_free"),
            ("parses", "recursive_descent", "context_free"),

            # Complexity containment
            ("contains", "NP_class", "P_class"),
            ("contains", "PSPACE", "NP_class"),
            ("contains", "EXPTIME", "PSPACE"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 7. CELTIC LINGUISTICS — Irish & Cornish mutation systems
# Source: Stifter (Old Irish), Ó Siadhail (Modern Irish),
#         George (Cornish), Williams (Middle Welsh)
# ══════════════════════════════════════════════════════════════

def celtic_linguistics() -> dict:
    """Irish and Cornish initial mutation systems with verb morphology."""
    return {
        "name": "CelticLinguistics",
        "objects": [
            # Irish initial consonants
            "b_ir", "c_ir", "d_ir", "f_ir", "g_ir",
            "m_ir", "p_ir", "s_ir", "t_ir",
            # Lenited forms
            "bh_ir", "ch_ir", "dh_ir", "fh_ir", "gh_ir",
            "mh_ir", "ph_ir", "sh_ir", "th_ir",
            # Eclipsed forms
            "mb_ir", "gc_ir", "nd_ir", "bhf_ir", "ng_ir",
            "bp_ir", "dt_ir",
            # Cornish initial consonants
            "b_kw", "k_kw", "d_kw", "g_kw",
            "m_kw", "p_kw", "t_kw",
            # Cornish soft mutation (lenition)
            "v_kw", "g_kw_len", "dh_kw", "w_kw",
            "v_kw_nas", "b_kw_len", "d_kw_len",
            # Mutation triggers
            "lenition_trigger", "eclipsis_trigger",
            "h_prefix_trigger", "soft_mutation_trigger",
            # Grammatical contexts
            "after_article_fem", "after_preposition",
            "after_possessive_1s", "after_possessive_3s_m",
            "after_verbal_particle", "after_numeral",
            "genitive_context",
            # Verb features
            "present_ir", "past_ir", "future_ir",
            "conditional_ir", "habitual_ir",
            "independent_form", "dependent_form",
            "analytic_form", "synthetic_form",
            # Verb classes
            "first_conjugation", "second_conjugation",
            "irregular_verb",
        ],
        "morphisms": [
            # Irish lenition: b→bh, c→ch, d→dh, etc.
            ("lenition", "b_ir", "bh_ir"), ("lenition", "c_ir", "ch_ir"),
            ("lenition", "d_ir", "dh_ir"), ("lenition", "f_ir", "fh_ir"),
            ("lenition", "g_ir", "gh_ir"), ("lenition", "m_ir", "mh_ir"),
            ("lenition", "p_ir", "ph_ir"), ("lenition", "s_ir", "sh_ir"),
            ("lenition", "t_ir", "th_ir"),
            # De-lenition (inverse)
            ("delenition", "bh_ir", "b_ir"), ("delenition", "ch_ir", "c_ir"),
            ("delenition", "dh_ir", "d_ir"), ("delenition", "fh_ir", "f_ir"),
            ("delenition", "gh_ir", "g_ir"), ("delenition", "mh_ir", "m_ir"),
            ("delenition", "ph_ir", "p_ir"), ("delenition", "sh_ir", "s_ir"),
            ("delenition", "th_ir", "t_ir"),

            # Irish eclipsis: b→mb, c→gc, d→nd, etc.
            ("eclipsis", "b_ir", "mb_ir"), ("eclipsis", "c_ir", "gc_ir"),
            ("eclipsis", "d_ir", "nd_ir"), ("eclipsis", "f_ir", "bhf_ir"),
            ("eclipsis", "g_ir", "ng_ir"), ("eclipsis", "p_ir", "bp_ir"),
            ("eclipsis", "t_ir", "dt_ir"),
            # De-eclipsis
            ("de_eclipsis", "mb_ir", "b_ir"), ("de_eclipsis", "gc_ir", "c_ir"),
            ("de_eclipsis", "nd_ir", "d_ir"), ("de_eclipsis", "bhf_ir", "f_ir"),
            ("de_eclipsis", "ng_ir", "g_ir"), ("de_eclipsis", "bp_ir", "p_ir"),
            ("de_eclipsis", "dt_ir", "t_ir"),

            # Cornish soft mutation (lenition): b→v, k→g, d→dh, etc.
            ("soft_mutation", "b_kw", "v_kw"),
            ("soft_mutation", "k_kw", "g_kw_len"),
            ("soft_mutation", "d_kw", "dh_kw"),
            ("soft_mutation", "g_kw", "w_kw"),
            ("soft_mutation", "m_kw", "v_kw_nas"),
            ("soft_mutation", "p_kw", "b_kw_len"),
            ("soft_mutation", "t_kw", "d_kw_len"),

            # Mutation triggers → mutation type
            ("triggers", "after_article_fem", "lenition_trigger"),
            ("triggers", "after_possessive_1s", "lenition_trigger"),
            ("triggers", "after_possessive_3s_m", "lenition_trigger"),
            ("triggers", "after_preposition", "eclipsis_trigger"),
            ("triggers", "after_numeral", "eclipsis_trigger"),
            ("triggers", "genitive_context", "lenition_trigger"),

            # Irish lenition trigger → context
            ("applies_in", "lenition_trigger", "after_article_fem"),
            ("applies_in", "lenition_trigger", "after_possessive_1s"),
            ("applies_in", "eclipsis_trigger", "after_preposition"),

            # Verb morphology
            ("has_tense", "first_conjugation", "present_ir"),
            ("has_tense", "first_conjugation", "past_ir"),
            ("has_tense", "first_conjugation", "future_ir"),
            ("has_tense", "second_conjugation", "present_ir"),
            ("has_tense", "second_conjugation", "past_ir"),
            ("has_form", "present_ir", "independent_form"),
            ("has_form", "present_ir", "dependent_form"),
            ("has_form", "past_ir", "independent_form"),
            ("has_form", "past_ir", "dependent_form"),
            ("after_particle", "dependent_form", "after_verbal_particle"),
            ("type_of", "analytic_form", "independent_form"),
            ("type_of", "synthetic_form", "independent_form"),

            # Cross-Celtic analogy: Irish lenition ↔ Cornish soft mutation
            # (structurally parallel: both map voiceless→voiced, stop→fricative)
            ("cross_celtic", "lenition_trigger", "soft_mutation_trigger"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# ALL LINGUISTIC DATASETS
# ══════════════════════════════════════════════════════════════

ALL_LINGUISTIC_DATASETS = {
    "grammar": grammar_structure,
    "ipa_phonetics": ipa_phonetics,
    "semantics": semantic_structure,
    "unicode": unicode_structure,
    "programming_languages": programming_languages,
    "formal_language_theory": formal_language_theory,
    "celtic_linguistics": celtic_linguistics,
}

def stats_linguistic():
    """Print statistics for all linguistic datasets."""
    total_obj = 0
    total_morph = 0
    for name, fn in ALL_LINGUISTIC_DATASETS.items():
        data = fn()
        n_obj = len(data["objects"])
        n_morph = len(data["morphisms"])
        rel_types = set(m[0] for m in data["morphisms"])
        total_obj += n_obj
        total_morph += n_morph
        print(f"  {name:30s}: {n_obj:4d} objects, {n_morph:4d} morphisms, {len(rel_types):2d} rel types")
    print(f"  {'TOTAL':30s}: {total_obj:4d} objects, {total_morph:4d} morphisms")
