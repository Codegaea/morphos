"""
MORPHOS Query Language — Compiles natural expressions into kernel tasks.

Syntax (by example):
    find analogies between celtic_linguistics and programming_languages
    search celtic_linguistics → programming_languages using csp
    what is dog
    query heart
    show domains
    import all
    import periodic_table
    info grammar
    compare ipa_phonetics and celtic_linguistics
    speculate on grammar
    compose grammar
    infer grammar rule=transitivity
    evidence <morphism_id>
    explain <morphism_id>
    explain path x → y in grammar
    save program <name> <source> <target>
    test program <name>
    reinforce program <name>
    snapshot grammar
    programs
    suggest
    pipeline <source> <target>
    derive is_a dog vertebrate via transitivity from m1 m2

Grammar:
    COMMAND := SEARCH_CMD | QUERY_CMD | INFO_CMD | IMPORT_CMD | DERIVE_CMD
             | DOMAIN_CMD | MISC_CMD | EXPLAIN_CMD | COMPOSE_CMD | INFER_CMD
             | SAVE_CMD | TEST_CMD | REINFORCE_CMD | PIPELINE_CMD
    SEARCH_CMD := ("find" | "search" | "compare" | "analogy" | "map")
                  DOMAIN ("→" | ">" | "to" | "and" | "between" | "with") DOMAIN
                  ["using" METHOD]?
    QUERY_CMD := ("what is" | "query" | "lookup" | "about" | "tell me about") CONCEPT
    INFO_CMD := ("info" | "show" | "describe" | "details") DOMAIN
    IMPORT_CMD := "import" (DATASET | "all" | FILE)
    DERIVE_CMD := "derive" LABEL SOURCE TARGET ["via" RULE] ["from" PREMISES...]
    DOMAIN_CMD := ("domains" | "show domains" | "list domains")
    EXPLAIN_CMD := ("explain" | "why" | "proof" | "trace") MORPHISM_ID
                 | "explain path" SOURCE "→" TARGET "in" DOMAIN
    COMPOSE_CMD := ("compose" | "compositions") DOMAIN
    INFER_CMD := ("infer" | "inference" | "close") DOMAIN ["rule=RULE"]
    SAVE_CMD := ("save" | "register") "program" NAME SOURCE TARGET
    TEST_CMD := ("test" | "run tests") "program" NAME
    REINFORCE_CMD := ("reinforce" | "confirm") "program" NAME
    PIPELINE_CMD := ("pipeline" | "run pipeline") SOURCE TARGET
    MISC_CMD := "suggest" | "programs" | "tasks" | "stats" | "datasets"
              | "speculate" ["on"] DOMAIN | "snapshot" DOMAIN
              | "evidence" MORPHISM_ID | "memory" | "beliefs"

The compiler produces Task dicts that the kernel scheduler can execute.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedCommand:
    """Result of parsing a natural language query."""
    action: str         # search, query, info, import, derive, domains, etc.
    params: dict        # action-specific parameters
    raw: str            # original input
    confidence: float = 1.0  # how confident the parse is

    def to_task(self) -> Optional[dict]:
        """Convert to a kernel task dict."""
        if self.action == "search":
            return {
                "task_type": "map",
                "params": {
                    "source_domain": self.params["source"],
                    "target_domain": self.params["target"],
                    "method": self.params.get("method", "csp"),
                },
            }
        if self.action == "verify":
            return {
                "task_type": "verify",
                "params": {"domain_name": self.params["domain"]},
            }
        if self.action == "snapshot":
            return {
                "task_type": "snapshot",
                "params": {"domain_name": self.params["domain"]},
            }
        if self.action == "speculate":
            return {
                "task_type": "speculate",
                "params": {"domain_name": self.params["domain"]},
            }
        if self.action == "compose":
            return {
                "task_type": "compose",
                "params": {"domain_name": self.params["domain"]},
            }
        if self.action == "infer":
            return {
                "task_type": "infer",
                "params": {
                    "domain_name": self.params["domain"],
                    "rule": self.params.get("rule", "transitivity"),
                },
            }
        if self.action == "test_program":
            return {
                "task_type": "test",
                "params": {"program_id": self.params.get("program_id", "")},
            }
        if self.action == "pipeline":
            return {
                "task_type": "pipeline",
                "params": {
                    "source_domain": self.params["source"],
                    "target_domain": self.params["target"],
                },
            }
        # Non-task actions return None (handled directly by CLI/server)
        return None


# ── Tokenizer ─────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Split into tokens, preserving quoted strings and special chars."""
    # Normalize arrows
    text = text.replace("→", " → ").replace("->", " → ").replace(" > ", " → ")
    # Remove unnecessary punctuation
    text = text.replace(",", " ").replace(";", " ").replace("?", "").replace("!", "")
    tokens = text.split()
    return [t.strip() for t in tokens if t.strip()]


# ── Pattern Matchers ──────────────────────────────────

_SEARCH_VERBS = {"find", "search", "compare", "map", "analogy", "analogies", "match"}
_SEARCH_PREPS = {"between", "and", "to", "with", "→", "vs", "versus"}
_QUERY_VERBS = {"what", "query", "lookup", "about", "tell", "whats", "who", "where", "describe"}
_INFO_VERBS = {"info", "show", "details", "detail", "examine", "inspect"}
_IMPORT_VERBS = {"import", "load", "add", "ingest"}
_METHOD_WORDS = {"using", "with", "via", "method"}
_METHODS = {"csp", "embedding", "scalable", "exact"}

# Known domain names (loaded dynamically, but these are defaults)
_KNOWN_DOMAINS = {
    "periodic_table", "musical_theory", "color_theory", "biological_taxonomy",
    "process_chains", "mathematical_structures", "commonsense", "physics",
    "spatial_geometry", "world_knowledge", "visual_relationships",
    "grammar", "ipa_phonetics", "semantics", "unicode",
    "programming_languages", "formal_language_theory", "celtic_linguistics",
}


def compile_query(text: str, known_domains: set[str] = None) -> ParsedCommand:
    """
    Compile a natural language expression into a ParsedCommand.

    Handles ambiguity by trying multiple parse strategies and
    picking the highest-confidence result.
    """
    if known_domains:
        domains = known_domains | _KNOWN_DOMAINS
    else:
        domains = _KNOWN_DOMAINS

    text = text.strip()
    if not text:
        return ParsedCommand("error", {"message": "Empty query"}, text, 0.0)

    tokens = _tokenize(text)
    lower_tokens = [t.lower() for t in tokens]

    # Try each parser in priority order
    parsers = [
        _parse_simple_command,
        _parse_explain,
        _parse_compose,
        _parse_infer,
        _parse_pipeline,
        _parse_save_program,
        _parse_test_program,
        _parse_reinforce_program,
        _parse_search,
        _parse_query,
        _parse_info,
        _parse_import,
        _parse_derive,
        _parse_speculate,
        _parse_evidence,
        _parse_snapshot,
        _parse_fallback_search,
    ]

    for parser in parsers:
        result = parser(tokens, lower_tokens, text, domains)
        if result:
            return result

    return ParsedCommand("unknown", {"text": text}, text, 0.0)


def _parse_simple_command(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse single-word commands."""
    if not tokens:
        return None
    cmd = lower[0]
    if cmd in ("domains", "list"):
        if len(tokens) == 1 or (len(tokens) == 2 and lower[1] == "domains"):
            return ParsedCommand("domains", {}, raw)
    if cmd in ("programs", "program"):
        return ParsedCommand("programs", {}, raw)
    if cmd in ("tasks", "task"):
        return ParsedCommand("tasks", {}, raw)
    if cmd in ("stats", "statistics", "status"):
        return ParsedCommand("stats", {}, raw)
    if cmd in ("datasets", "dataset"):
        return ParsedCommand("datasets", {}, raw)
    if cmd in ("suggest", "suggestions", "recommend"):
        return ParsedCommand("suggest", {}, raw)
    if cmd in ("help", "?"):
        return ParsedCommand("help", {}, raw)
    if cmd in ("memory", "beliefs", "analogies"):
        return ParsedCommand("memory", {}, raw)
    return None


def _parse_search(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse search/analogy commands."""
    if not tokens:
        return None

    # Check for search verb
    if lower[0] not in _SEARCH_VERBS:
        return None

    # Extract domain names from the rest
    rest = tokens[1:]
    rest_lower = lower[1:]

    # Remove filler words
    fillers = {"analogies", "analogy", "between", "for", "the", "in", "of", "structural", "structure", "me"}
    cleaned = [(t, l) for t, l in zip(rest, rest_lower) if l not in fillers]
    clean_tokens = [t for t, _ in cleaned]
    clean_lower = [l for _, l in cleaned]

    return _extract_two_domains(clean_tokens, clean_lower, raw, domains)


def _parse_explain(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse explain / proof / trace commands.

    explain <morphism_id>
    explain path <source> → <target> in <domain>
    why <morphism_id>
    proof <morphism_id>
    """
    if not tokens or lower[0] not in ("explain", "why", "proof", "trace", "audit"):
        return None

    rest = tokens[1:]
    rest_lower = lower[1:]

    # "explain path src → tgt in domain"
    if rest_lower and rest_lower[0] == "path":
        rest = rest[1:]
        rest_lower = rest_lower[1:]
        if "→" in rest:
            idx = rest.index("→")
            src = " ".join(rest[:idx])
            remainder = rest[idx + 1:]
            # Split on "in" to get domain
            if "in" in [t.lower() for t in remainder]:
                in_idx = next(i for i, t in enumerate(remainder) if t.lower() == "in")
                tgt = " ".join(remainder[:in_idx])
                dom = _find_domain(" ".join(remainder[in_idx + 1:]), domains) or " ".join(remainder[in_idx + 1:])
            else:
                tgt = " ".join(remainder)
                dom = None
            return ParsedCommand("explain_path", {"source": src, "target": tgt, "domain": dom}, raw, 0.9)

    # "explain <morphism_id>" — IDs look like UUIDs or short hex
    if rest:
        mid = rest[0]
        return ParsedCommand("explain", {"morphism_id": mid}, raw, 0.9)

    return None


def _parse_compose(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse compose commands.

    compose <domain>
    compositions <domain>
    """
    if not tokens or lower[0] not in ("compose", "compositions", "composition", "close"):
        return None
    # "close" is ambiguous with other uses, only match if followed by a domain
    if lower[0] == "close" and len(tokens) < 2:
        return None
    rest = tokens[1:]
    if rest:
        domain = _find_domain(" ".join(rest), domains) or " ".join(rest)
        return ParsedCommand("compose", {"domain": domain}, raw, 0.9)
    return None


def _parse_infer(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse infer / inference commands.

    infer <domain>
    infer <domain> rule=transitivity
    """
    if not tokens or lower[0] not in ("infer", "inference", "transitive", "close_under"):
        return None
    rest = tokens[1:]
    rest_lower = lower[1:]
    rule = "transitivity"
    # Look for rule= keyword
    filtered = []
    for t, l in zip(rest, rest_lower):
        if l.startswith("rule="):
            rule = l.split("=", 1)[1]
        else:
            filtered.append(t)
    if filtered:
        domain = _find_domain(" ".join(filtered), domains) or " ".join(filtered)
        return ParsedCommand("infer", {"domain": domain, "rule": rule}, raw, 0.9)
    return None


def _parse_pipeline(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse pipeline commands.

    pipeline <source> <target>
    run pipeline <source> → <target>
    """
    if not tokens:
        return None

    start = 0
    if lower[0] == "pipeline":
        start = 1
    elif lower[0] == "run" and len(lower) > 1 and lower[1] == "pipeline":
        start = 2
    else:
        return None

    rest = tokens[start:]
    rest_lower = lower[start:]

    # First try normal extraction (handles → and "and" separators)
    result = _extract_two_domains(rest, rest_lower, raw, domains)
    if result:
        return ParsedCommand("pipeline", {"source": result.params["source"], "target": result.params["target"]}, raw, 0.95)

    # Fallback: resolve each token individually as domain names
    resolved = [_find_domain(t, domains) for t in rest_lower]
    resolved = [r for r in resolved if r]
    if len(resolved) >= 2:
        return ParsedCommand("pipeline", {"source": resolved[0], "target": resolved[1]}, raw, 0.85)

    return None


def _parse_save_program(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse save/register program commands.

    save program <name> <source> <target>
    register program <name> as <source> <target>
    """
    if not tokens or lower[0] not in ("save", "register"):
        return None
    if len(lower) < 2 or lower[1] != "program":
        return None
    rest = tokens[2:]
    if not rest:
        return None
    name = rest[0]
    remaining = rest[1:]
    rem_lower = [t.lower() for t in remaining]
    # Strip "as"
    if rem_lower and rem_lower[0] == "as":
        remaining = remaining[1:]
        rem_lower = rem_lower[1:]
    result = _extract_two_domains(remaining, rem_lower, raw, domains)
    if result:
        return ParsedCommand("save_program", {"name": name, "source": result.params["source"], "target": result.params["target"]}, raw, 0.9)
    # Fallback: resolve tokens individually as abbreviated domain names
    resolved = [r for r in (_find_domain(t, domains) for t in rem_lower) if r]
    return ParsedCommand("save_program", {
        "name": name,
        "source": resolved[0] if len(resolved) >= 1 else None,
        "target": resolved[1] if len(resolved) >= 2 else None,
    }, raw, 0.8)


def _parse_test_program(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse test program commands.

    test program <name>
    run tests <name>
    """
    if not tokens:
        return None
    if lower[0] == "test" and len(lower) > 1 and lower[1] == "program":
        name = " ".join(tokens[2:]) if len(tokens) > 2 else ""
        return ParsedCommand("test_program", {"program_name": name}, raw, 0.9)
    if lower[0] == "run" and len(lower) > 1 and lower[1] in ("tests", "test"):
        name = " ".join(tokens[2:]) if len(tokens) > 2 else ""
        return ParsedCommand("test_program", {"program_name": name}, raw, 0.9)
    return None


def _parse_reinforce_program(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse reinforce / confirm program commands.

    reinforce program <name>
    confirm program <name>
    """
    if not tokens or lower[0] not in ("reinforce", "confirm", "strengthen"):
        return None
    if len(lower) > 1 and lower[1] == "program":
        name = " ".join(tokens[2:]) if len(tokens) > 2 else ""
        return ParsedCommand("reinforce_program", {"program_name": name}, raw, 0.9)
    return None


def _parse_fallback_search(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Try to parse as a search if there's an arrow or two domain-matching tokens."""
    if "→" in tokens:
        parts = raw.split("→")
        if len(parts) == 2:
            src = _find_domain(parts[0].strip(), domains)
            tgt = _find_domain(parts[1].strip(), domains)
            if src and tgt:
                return ParsedCommand("search", {"source": src, "target": tgt, "method": "csp"}, raw, 0.8)

    # Try each token individually against domain resolution
    found = []
    for t in tokens:
        d = _find_domain(t.lower(), domains)
        if d and (not found or d != found[-1]):
            found.append(d)

    if len(found) >= 2:
        return ParsedCommand("search", {"source": found[0], "target": found[1], "method": "csp"}, raw, 0.6)

    return None


def _extract_two_domains(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Extract source and target domains from token list."""
    method = "csp"

    # Check for method specification
    for i, l in enumerate(lower):
        if l in _METHOD_WORDS and i + 1 < len(lower) and lower[i + 1] in _METHODS:
            method = lower[i + 1]
            tokens = tokens[:i] + tokens[i + 2:]
            lower = lower[:i] + lower[i + 2:]
            break

    # Find arrow separator
    if "→" in tokens:
        idx = tokens.index("→")
        src_part = " ".join(tokens[:idx]).strip()
        tgt_part = " ".join(tokens[idx + 1:]).strip()
        src = _find_domain(src_part, domains)
        tgt = _find_domain(tgt_part, domains)
        if src and tgt:
            return ParsedCommand("search", {"source": src, "target": tgt, "method": method}, raw, 0.9)

    # Find "and" separator
    if "and" in lower:
        idx = lower.index("and")
        src = _find_domain(" ".join(tokens[:idx]), domains)
        tgt = _find_domain(" ".join(tokens[idx + 1:]), domains)
        if src and tgt:
            return ParsedCommand("search", {"source": src, "target": tgt, "method": method}, raw, 0.8)

    # Try consecutive domain names
    found = []
    i = 0
    while i < len(tokens):
        # Try multi-word domain names (longest match first)
        matched = False
        for length in range(min(3, len(tokens) - i), 0, -1):
            candidate = "_".join(lower[i:i + length])
            if candidate in domains:
                found.append(candidate)
                i += length
                matched = True
                break
        if not matched:
            i += 1

    if len(found) >= 2:
        return ParsedCommand("search", {"source": found[0], "target": found[1], "method": method}, raw, 0.7)

    return None


def _parse_query(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse knowledge queries."""
    if not tokens:
        return None

    if lower[0] in _QUERY_VERBS:
        # "what is X", "tell me about X"
        rest = tokens[1:]
        rest_lower = lower[1:]
        # Remove filler
        fillers = {"is", "are", "me", "about", "a", "an", "the"}
        concept_tokens = [t for t, l in zip(rest, rest_lower) if l not in fillers]
        if concept_tokens:
            concept = " ".join(concept_tokens)
            return ParsedCommand("query", {"concept": concept}, raw, 0.9)

    if lower[0] == "query" and len(tokens) > 1:
        return ParsedCommand("query", {"concept": " ".join(tokens[1:])}, raw, 1.0)

    return None


def _parse_info(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse info/details commands."""
    if not tokens:
        return None
    if lower[0] in _INFO_VERBS:
        if len(tokens) > 1:
            domain_part = " ".join(tokens[1:])
            domain = _find_domain(domain_part, domains) or domain_part
            return ParsedCommand("info", {"domain": domain}, raw, 0.9)
    return None


def _parse_import(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse import commands."""
    if not tokens:
        return None
    if lower[0] in _IMPORT_VERBS:
        if len(tokens) > 1:
            target = " ".join(tokens[1:]).strip()
            if target.lower() == "all":
                return ParsedCommand("import", {"dataset": "all"}, raw, 1.0)
            # Check if it's a known dataset
            domain = _find_domain(target, domains)
            if domain:
                return ParsedCommand("import", {"dataset": domain}, raw, 0.9)
            # Could be a file path
            if "." in target:
                return ParsedCommand("import", {"file": target}, raw, 0.8)
            return ParsedCommand("import", {"dataset": target}, raw, 0.7)
    return None


def _parse_derive(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse derive commands."""
    if lower[0] != "derive" or len(tokens) < 4:
        return None
    label = tokens[1]
    source = tokens[2]
    target = tokens[3]
    rule = "user"
    premises = []
    if "via" in lower:
        idx = lower.index("via")
        if idx + 1 < len(tokens):
            rule = tokens[idx + 1]
    if "from" in lower:
        idx = lower.index("from")
        premises = tokens[idx + 1:]
    return ParsedCommand("derive", {
        "label": label, "source": source, "target": target,
        "rule": rule, "premises": premises,
    }, raw, 0.9)


def _parse_speculate(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse speculate commands."""
    if lower[0] == "speculate":
        rest = [t for t, l in zip(tokens[1:], lower[1:]) if l not in ("on", "about", "in")]
        if rest:
            domain = _find_domain(" ".join(rest), domains) or rest[0]
            return ParsedCommand("speculate", {"domain": domain}, raw, 0.9)
    return None


def _parse_evidence(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse evidence commands."""
    if lower[0] == "evidence" and len(tokens) > 1:
        return ParsedCommand("evidence", {"morphism_id": tokens[1]}, raw, 1.0)
    return None


def _parse_snapshot(tokens, lower, raw, domains) -> Optional[ParsedCommand]:
    """Parse snapshot commands."""
    if lower[0] == "snapshot" and len(tokens) > 1:
        domain = _find_domain(" ".join(tokens[1:]), domains) or tokens[1]
        return ParsedCommand("snapshot", {"domain": domain}, raw, 1.0)
    return None


# ── Domain Name Resolution ────────────────────────────

def _find_domain(text: str, domains: set[str]) -> Optional[str]:
    """Fuzzy-match a domain name."""
    text = text.strip().lower()
    if not text:
        return None

    # Exact match
    if text in domains:
        return text

    # Underscore variant
    underscored = text.replace(" ", "_")
    if underscored in domains:
        return underscored

    # Partial match (text is substring of domain)
    matches = [d for d in domains if text in d]
    if len(matches) == 1:
        return matches[0]

    # Prefix match
    prefixes = [d for d in domains if d.startswith(text)]
    if len(prefixes) == 1:
        return prefixes[0]

    # Common abbreviations
    abbrevs = {
        "bio": "biological_taxonomy", "biology": "biological_taxonomy",
        "taxonomy": "biological_taxonomy", "animals": "biological_taxonomy",
        "chem": "periodic_table", "chemistry": "periodic_table",
        "elements": "periodic_table", "table": "periodic_table",
        "music": "musical_theory", "musical": "musical_theory",
        "ipa": "ipa_phonetics", "phonetics": "ipa_phonetics",
        "phonology": "ipa_phonetics", "consonants": "ipa_phonetics",
        "vowels": "ipa_phonetics", "sounds": "ipa_phonetics",
        "pl": "programming_languages", "prog": "programming_languages",
        "langs": "programming_languages", "languages": "programming_languages",
        "programming": "programming_languages", "type-system": "programming_languages",
        "type": "programming_languages", "types": "programming_languages",
        "variance": "programming_languages",
        "celtic": "celtic_linguistics", "irish": "celtic_linguistics",
        "cornish": "celtic_linguistics", "mutation": "celtic_linguistics",
        "mutations": "celtic_linguistics", "lenition": "celtic_linguistics",
        "eclipsis": "celtic_linguistics",
        "math": "mathematical_structures", "maths": "mathematical_structures",
        "algebra": "mathematical_structures", "groups": "mathematical_structures",
        "flt": "formal_language_theory", "chomsky": "formal_language_theory",
        "automata": "formal_language_theory", "formal": "formal_language_theory",
        "turing": "formal_language_theory", "regex": "formal_language_theory",
        "color": "color_theory", "colour": "color_theory",
        "colors": "color_theory", "colours": "color_theory",
        "geo": "spatial_geometry", "geometry": "spatial_geometry",
        "spatial": "spatial_geometry", "shapes": "spatial_geometry",
        "topology": "spatial_geometry",
        "visual": "visual_relationships", "vision": "visual_relationships",
        "image": "visual_relationships", "scene": "visual_relationships",
        "world": "world_knowledge", "countries": "world_knowledge",
        "geography": "world_knowledge",
        "process": "process_chains", "processes": "process_chains",
        "cycles": "process_chains", "workflow": "process_chains",
        "commonsense": "commonsense", "common": "commonsense",
        "everyday": "commonsense",
        "physics": "physics", "equations": "physics",
        "mechanics": "physics", "thermodynamics": "physics",
        "unicode": "unicode", "scripts": "unicode", "encoding": "unicode",
        "utf": "unicode",
        "grammar": "grammar", "syntax": "grammar", "parsing": "grammar",
        "pos": "grammar", "morphology": "grammar",
        "semantics": "semantics", "meaning": "semantics",
        "pragmatics": "semantics", "roles": "semantics",
    }
    if text in abbrevs and abbrevs[text] in domains:
        return abbrevs[text]

    return None
