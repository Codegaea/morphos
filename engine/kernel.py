"""
MORPHOS Reasoning OS Kernel

Everything is a morphism, and every morphism is accountable.

Architecture:
  0. Substrate:   Persistent SQLite store (concepts, morphisms, evidence, derivations)
  1. Kernel:      Schema enforcement, inference runtime, proof attachment
  2. Tasks:       First-class reasoning jobs with lifecycle
  3. Programs:    Functors as reusable, versioned, testable programs
  4. Provenance:  Every derived fact traceable to its sources

Database schema:
  domains          — named knowledge domains (versioned snapshots)
  concepts         — typed objects within domains
  morphisms        — relationships with proof terms and truth values
  evidence         — observations supporting/contradicting morphisms
  derivations      — proof traces showing how morphisms were derived
  programs         — stored functors (cross-domain mappings)
  program_tests    — assertions a program must satisfy
  tasks            — reasoning job queue with status tracking
  task_results     — artifacts produced by completed tasks
"""
from __future__ import annotations
import sqlite3
import json
import time
import uuid
import os
from dataclasses import dataclass, field
from typing import Optional, Any
from collections import defaultdict
from pathlib import Path

from .categories import Category, Morphism, create_category
from .topos import (
    TruthValue, Modality, compose_truth, bayesian_update,
    actual, probable, possible, undetermined, TRUE, FALSE,
)
from .epistemic import Definite


# ══════════════════════════════════════════════════════════════
# 0. PERSISTENT STORE — The "filesystem" of the Reasoning OS
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════
# ProofTerm: structured, checkable, normalizable proof certificates
# ══════════════════════════════════════════════════════════════════

def _split_args(s: str) -> list[str]:
    """Split comma-separated args, respecting nested parentheses."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    return [p for p in parts if p]


@dataclass
class ProofTerm:
    """
    A structured, checkable proof certificate for a derived morphism.

    Replaces opaque string proof_terms with a normalized form that:
    - is deterministic (canonical)
    - can be type-checked against the rule
    - supports proof comparison (same proof = same canonical string)
    - can be serialized to/from JSON for storage
    """
    rule: str                    # "axiom" | "transitivity" | "composition" | "auto_compose" | ...
    premises: list               # list[morphism_id: str]
    metadata: dict = None        # rule-specific extra info

    COMMUTATIVE_RULES = {"auto_compose", "conjunction", "meet", "join"}

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def canonical(self) -> str:
        """
        Beta-normal canonical form.
        - Commutative rules: premises sorted
        - Transitivity/composition: order preserved (directed chain)
        - Nested same-rule applications are flattened (associativity)
        """
        if not self.premises:
            return f"{self.rule}()"
        ps = sorted(self.premises) if self.rule in self.COMMUTATIVE_RULES else self.premises
        # Truncate UUIDs to 8 chars for readability
        short = [p[:8] if len(p) == 36 and "-" in p else p for p in ps[:10]]
        return f"{self.rule}({', '.join(short)})"

    def to_json(self) -> str:
        return json.dumps({
            "rule": self.rule,
            "premises": self.premises,
            "metadata": self.metadata,
        })

    @classmethod
    def from_json(cls, s: str) -> "ProofTerm":
        """Parse proof term from JSON string or legacy string form."""
        if not s:
            return cls(rule="axiom", premises=[])
        try:
            d = json.loads(s)
            if isinstance(d, dict) and "rule" in d:
                return cls(
                    rule=d.get("rule", "unknown"),
                    premises=d.get("premises", []),
                    metadata=d.get("metadata", {}),
                )
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        # Legacy string form: "rule(id1, id2, ...)" or plain strings
        s = s.strip()
        if "(" in s and s.endswith(")"):
            rule = s[:s.index("(")]
            inner = s[s.index("(")+1:-1].strip()
            premises = _split_args(inner) if inner else []
        elif s:
            rule = s
            premises = []
        else:
            rule, premises = "axiom", []
        return cls(rule=rule, premises=premises)

    @classmethod
    def axiom(cls) -> "ProofTerm":
        return cls(rule="axiom", premises=[])

    @classmethod
    def transitivity(cls, *premise_ids: str) -> "ProofTerm":
        return cls(rule="transitivity", premises=list(premise_ids))

    @classmethod
    def composition(cls, *premise_ids: str) -> "ProofTerm":
        return cls(rule="composition", premises=list(premise_ids))



SCHEMA = """
-- Domains: versioned knowledge containers
CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    snapshot_hash TEXT DEFAULT '',
    parent_version INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'
);

-- Concepts: typed objects within domains
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    label TEXT NOT NULL,
    concept_type TEXT DEFAULT 'entity',
    properties TEXT DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY (domain_id) REFERENCES domains(id),
    UNIQUE(domain_id, label)
);

-- Morphisms: relationships with full accountability
CREATE TABLE IF NOT EXISTS morphisms (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    label TEXT NOT NULL,
    source_label TEXT NOT NULL,
    target_label TEXT NOT NULL,
    rel_type TEXT DEFAULT '',
    value REAL,
    temporal_order INTEGER,
    -- Proof and truth
    truth_degree REAL DEFAULT 1.0,
    truth_modality TEXT DEFAULT 'ACTUAL',
    proof_term TEXT DEFAULT '',
    derivation_depth INTEGER DEFAULT 0,
    -- Provenance
    derived_from TEXT DEFAULT '',
    evidence_ids TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    created_by TEXT DEFAULT 'user',
    -- Flags
    is_identity INTEGER DEFAULT 0,
    is_composition INTEGER DEFAULT 0,
    is_inferred INTEGER DEFAULT 0,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

-- Evidence: observations that support or contradict morphisms
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    morphism_id TEXT,
    domain_id TEXT,
    label TEXT NOT NULL,
    evidence_type TEXT DEFAULT 'observation',
    strength REAL DEFAULT 0.5,
    direction TEXT DEFAULT 'supports',
    source TEXT DEFAULT '',
    timestamp REAL NOT NULL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (morphism_id) REFERENCES morphisms(id),
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

-- Derivations: proof traces
CREATE TABLE IF NOT EXISTS derivations (
    id TEXT PRIMARY KEY,
    morphism_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    premises TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    truth_degree REAL DEFAULT 1.0,
    timestamp REAL NOT NULL,
    FOREIGN KEY (morphism_id) REFERENCES morphisms(id)
);

-- Programs: stored functors (cross-domain mappings)
CREATE TABLE IF NOT EXISTS programs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    source_domain TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    object_map TEXT NOT NULL,
    morphism_map TEXT DEFAULT '{}',
    score REAL DEFAULT 0.0,
    truth_degree REAL DEFAULT 0.5,
    truth_modality TEXT DEFAULT 'PROBABLE',
    classification TEXT DEFAULT 'functor',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    confirmations INTEGER DEFAULT 0,
    contradictions INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'
);

-- Program tests: assertions a program must satisfy
CREATE TABLE IF NOT EXISTS program_tests (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    test_type TEXT NOT NULL,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    actual_output TEXT DEFAULT '',
    passed INTEGER DEFAULT 0,
    last_run REAL,
    FOREIGN KEY (program_id) REFERENCES programs(id)
);

-- Tasks: reasoning job queue
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    params TEXT NOT NULL,
    result TEXT DEFAULT '',
    error TEXT DEFAULT '',
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    duration_ms REAL,
    artifacts TEXT DEFAULT '[]'
);

-- Analogies: discovered structural mappings between categories (AnalogyMemory persistence)
CREATE TABLE IF NOT EXISTS analogies (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    target_name TEXT NOT NULL,
    object_map TEXT NOT NULL,
    morphism_map TEXT DEFAULT '{}',
    score REAL DEFAULT 0.0,
    truth_degree REAL DEFAULT 0.5,
    truth_modality TEXT DEFAULT 'PROBABLE',
    discovered_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    confirmations INTEGER DEFAULT 0,
    contradictions INTEGER DEFAULT 0,
    evidence TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}'
);

-- Category fingerprints: structural hashes for fast similarity lookup
CREATE TABLE IF NOT EXISTS category_fingerprints (
    cat_name TEXT PRIMARY KEY,
    n_objects INTEGER NOT NULL,
    n_morphisms INTEGER NOT NULL,
    degree_sequence TEXT NOT NULL,
    n_rel_types INTEGER NOT NULL,
    freq_distribution TEXT NOT NULL,
    has_cycles INTEGER NOT NULL,
    max_chain_length INTEGER NOT NULL,
    updated_at REAL NOT NULL
);


-- Dependency index: O(1) forward lookup premise→derived (replaces LIKE scan)
CREATE TABLE IF NOT EXISTS morphism_dependencies (
    premise_id   TEXT NOT NULL,
    derived_id   TEXT NOT NULL,
    rule         TEXT DEFAULT '',
    created_at   REAL NOT NULL,
    PRIMARY KEY (premise_id, derived_id),
    FOREIGN KEY (premise_id) REFERENCES morphisms(id),
    FOREIGN KEY (derived_id) REFERENCES morphisms(id)
);
CREATE INDEX IF NOT EXISTS idx_deps_premise ON morphism_dependencies(premise_id);
CREATE INDEX IF NOT EXISTS idx_deps_derived  ON morphism_dependencies(derived_id);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_analogies_source ON analogies(source_name);
CREATE INDEX IF NOT EXISTS idx_analogies_target ON analogies(target_name);
CREATE INDEX IF NOT EXISTS idx_analogies_score ON analogies(score);
CREATE INDEX IF NOT EXISTS idx_concepts_domain ON concepts(domain_id);
CREATE INDEX IF NOT EXISTS idx_concepts_label ON concepts(label);
CREATE INDEX IF NOT EXISTS idx_morphisms_domain ON morphisms(domain_id);
CREATE INDEX IF NOT EXISTS idx_morphisms_source ON morphisms(source_label);
CREATE INDEX IF NOT EXISTS idx_morphisms_target ON morphisms(target_label);
CREATE INDEX IF NOT EXISTS idx_morphisms_reltype ON morphisms(rel_type);
CREATE INDEX IF NOT EXISTS idx_evidence_morphism ON evidence(morphism_id);
CREATE INDEX IF NOT EXISTS idx_programs_domains ON programs(source_domain, target_domain);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


class ReasoningStore:
    """
    Persistent knowledge store — the filesystem of the Reasoning OS.

    All knowledge survives sessions. Every fact is traceable to its source.
    Every derivation is recorded. Every update is versioned.
    """

    def __init__(self, db_path: str = "morphos.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._backfill_dependency_index()

    def _backfill_dependency_index(self):
        """Populate morphism_dependencies from existing derivations (idempotent migration)."""
        rows = self.conn.execute("SELECT morphism_id, rule, premises FROM derivations").fetchall()
        added = 0
        for row in rows:
            try:
                premises = json.loads(row["premises"])
                for pid in premises:
                    if isinstance(pid, str) and len(pid) >= 8:
                        self.conn.execute(
                            "INSERT OR IGNORE INTO morphism_dependencies "
                            "(premise_id, derived_id, rule, created_at) VALUES (?,?,?,?)",
                            (pid, row["morphism_id"], row["rule"] or "backfill", time.time()))
                        added += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if added:
            self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Domain Management ─────────────────────────────────

    def create_domain(self, name: str, description: str = "") -> str:
        """Create a new knowledge domain. Returns domain ID."""
        did = str(uuid.uuid4())
        now = time.time()
        self.conn.execute(
            "INSERT INTO domains (id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)",
            (did, name, description, now, now))
        self.conn.commit()
        return did

    def get_domain(self, name: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM domains WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()
        return dict(row) if row else None

    def list_domains(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM domains ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def snapshot_domain(self, domain_id: str) -> str:
        """Create a versioned snapshot of a domain."""
        domain = self.conn.execute("SELECT * FROM domains WHERE id=?", (domain_id,)).fetchone()
        if not domain:
            raise ValueError(f"Domain {domain_id} not found")
        new_id = str(uuid.uuid4())
        now = time.time()
        new_version = domain["version"] + 1
        # Compute hash from content
        morphisms = self.conn.execute(
            "SELECT label, source_label, target_label FROM morphisms WHERE domain_id=? ORDER BY label",
            (domain_id,)).fetchall()
        content_hash = str(hash(str([(r["label"], r["source_label"], r["target_label"]) for r in morphisms])))
        self.conn.execute(
            "INSERT INTO domains (id, name, version, description, created_at, updated_at, snapshot_hash, parent_version) VALUES (?,?,?,?,?,?,?,?)",
            (new_id, domain["name"], new_version, domain["description"], now, now, content_hash, domain["version"]))
        # Copy concepts and morphisms
        for row in self.conn.execute("SELECT * FROM concepts WHERE domain_id=?", (domain_id,)):
            self.conn.execute(
                "INSERT INTO concepts (id, domain_id, label, concept_type, properties, created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), new_id, row["label"], row["concept_type"], row["properties"], now))
        for row in self.conn.execute("SELECT * FROM morphisms WHERE domain_id=?", (domain_id,)):
            self.conn.execute(
                "INSERT INTO morphisms (id, domain_id, label, source_label, target_label, rel_type, value, truth_degree, truth_modality, proof_term, derivation_depth, derived_from, evidence_ids, created_at, created_by, is_identity, is_composition, is_inferred) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), new_id, row["label"], row["source_label"], row["target_label"], row["rel_type"], row["value"], row["truth_degree"], row["truth_modality"], row["proof_term"], row["derivation_depth"], row["derived_from"], row["evidence_ids"], now, row["created_by"], row["is_identity"], row["is_composition"], row["is_inferred"]))
        self.conn.commit()
        return new_id

    # ── Concept Operations ────────────────────────────────

    def add_concept(self, domain_id: str, label: str, concept_type: str = "entity", **props) -> str:
        cid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT OR IGNORE INTO concepts (id, domain_id, label, concept_type, properties, created_at) VALUES (?,?,?,?,?,?)",
            (cid, domain_id, label, concept_type, json.dumps(props), time.time()))
        self.conn.commit()
        return cid

    def get_concepts(self, domain_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM concepts WHERE domain_id=?", (domain_id,)).fetchall()
        return [dict(r) for r in rows]

    # ── Morphism Operations (proof-carrying) ──────────────

    def add_morphism(
        self,
        domain_id: str,
        label: str,
        source: str,
        target: str,
        rel_type: str = "",
        value: float = None,
        truth_degree: float = 1.0,
        truth_modality: str = "ACTUAL",
        proof_term: str = "",
        created_by: str = "user",
        evidence_ids: list[str] = None,
    ) -> str:
        """Add a proof-carrying morphism to the store."""
        mid = str(uuid.uuid4())
        # Ensure concepts exist
        self.add_concept(domain_id, source)
        self.add_concept(domain_id, target)
        self.conn.execute(
            """INSERT INTO morphisms
               (id, domain_id, label, source_label, target_label, rel_type, value,
                truth_degree, truth_modality, proof_term, evidence_ids, created_at, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid, domain_id, label, source, target, rel_type or label, value,
             truth_degree, truth_modality, proof_term,
             json.dumps(evidence_ids or []), time.time(), created_by))
        self.conn.commit()
        return mid

    def add_derived_morphism(
        self,
        domain_id: str,
        label: str,
        source: str,
        target: str,
        rel_type: str,
        rule: str,
        premises: list[str],
        truth_degree: float = 1.0,
        truth_modality: str = "PROBABLE",
    ) -> str:
        """Add a morphism derived by inference, with full proof trace."""
        mid = self.add_morphism(
            domain_id, label, source, target, rel_type,
            truth_degree=truth_degree, truth_modality=truth_modality,
            proof_term=f"{rule}({', '.join(premises)})",
            created_by=f"inference:{rule}",
        )
        # Update flags
        self.conn.execute("UPDATE morphisms SET is_inferred=1, derivation_depth=? WHERE id=?",
                          (len(premises), mid))
        # Record derivation
        did = str(uuid.uuid4())
        now = time.time()
        pt = ProofTerm(rule=rule, premises=premises)
        self.conn.execute(
            "INSERT INTO derivations (id, morphism_id, rule, premises, conclusion, truth_degree, timestamp) VALUES (?,?,?,?,?,?,?)",
            (did, mid, rule, json.dumps(premises), f"{source}→{target}", truth_degree, now))
        # Update proof_term with structured canonical form
        self.conn.execute("UPDATE morphisms SET proof_term=? WHERE id=?", (pt.to_json(), mid))
        # Populate forward dependency index (skip if premise doesn't exist — e.g. test fixtures)
        for premise_id in premises:
            if isinstance(premise_id, str) and len(premise_id) >= 8:
                exists = self.conn.execute(
                    "SELECT 1 FROM morphisms WHERE id=?", (premise_id,)).fetchone()
                if exists:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO morphism_dependencies "
                        "(premise_id, derived_id, rule, created_at) VALUES (?,?,?,?)",
                        (premise_id, mid, rule, now))
        self.conn.commit()
        return mid

    def get_morphisms(self, domain_id: str, source: str = None, target: str = None, rel_type: str = None) -> list[dict]:
        """Query morphisms with optional filters."""
        query = "SELECT * FROM morphisms WHERE domain_id=? AND is_identity=0"
        params = [domain_id]
        if source:
            query += " AND source_label=?"
            params.append(source)
        if target:
            query += " AND target_label=?"
            params.append(target)
        if rel_type:
            query += " AND rel_type=?"
            params.append(rel_type)
        return [dict(r) for r in self.conn.execute(query, params).fetchall()]

    def update_truth(self, morphism_id: str, degree: float, modality: str):
        """Update truth value of a morphism."""
        self.conn.execute(
            "UPDATE morphisms SET truth_degree=?, truth_modality=?, domain_id=domain_id WHERE id=?",
            (degree, modality, morphism_id))
        self.conn.commit()

    # ── Evidence Operations ───────────────────────────────

    def add_evidence(
        self,
        morphism_id: str,
        label: str,
        direction: str = "supports",
        strength: float = 0.8,
        source: str = "",
    ) -> str:
        """Add evidence for/against a morphism and update its truth value."""
        eid = str(uuid.uuid4())
        domain_id = self.conn.execute("SELECT domain_id FROM morphisms WHERE id=?", (morphism_id,)).fetchone()
        did = domain_id["domain_id"] if domain_id else ""
        self.conn.execute(
            "INSERT INTO evidence (id, morphism_id, domain_id, label, strength, direction, source, timestamp) VALUES (?,?,?,?,?,?,?,?)",
            (eid, morphism_id, did, label, strength, direction, source, time.time()))
        # Bayesian update on the morphism's truth
        morph = self.conn.execute("SELECT truth_degree, truth_modality, evidence_ids FROM morphisms WHERE id=?", (morphism_id,)).fetchone()
        if morph:
            tv = TruthValue(morph["truth_degree"], Modality[morph["truth_modality"]])
            if direction == "supports":
                tv = bayesian_update(tv, label, likelihood_if_true=strength, likelihood_if_false=1-strength)
            else:
                tv = bayesian_update(tv, label, likelihood_if_true=1-strength, likelihood_if_false=strength)
            ev_ids = json.loads(morph["evidence_ids"])
            ev_ids.append(eid)
            self.conn.execute(
                "UPDATE morphisms SET truth_degree=?, truth_modality=?, evidence_ids=? WHERE id=?",
                (tv.degree, tv.modality.name, json.dumps(ev_ids), morphism_id))
        self.conn.commit()

        # Belief revision propagation: push updated truth through derivation children
        self._propagate_belief(morphism_id)

        return eid

    def _propagate_belief(self, morphism_id: str, depth: int = 0, max_depth: int = 10):
        """
        Propagate a truth-value change forward through the dependency graph.

        Uses morphism_dependencies index for O(k) lookup (k = direct dependents)
        instead of O(n) LIKE scan over all morphisms.

        Each derived morphism's truth is recomputed as the composition of ALL
        its premises (weakest-premise rule), then propagated recursively.
        """
        if depth >= max_depth:
            return
        from .topos import TruthValue, Modality, compose_truth

        # O(k) index lookup: only morphisms that directly depend on this one
        child_rows = self.conn.execute(
            "SELECT derived_id FROM morphism_dependencies WHERE premise_id=?",
            (morphism_id,)).fetchall()

        for crow in child_rows:
            child_id = crow["derived_id"]

            # Get ALL premises of this derived morphism from the dependency index
            all_prem_rows = self.conn.execute(
                "SELECT premise_id FROM morphism_dependencies WHERE derived_id=?",
                (child_id,)).fetchall()
            premise_ids = [r["premise_id"] for r in all_prem_rows]
            if not premise_ids:
                continue

            # Fetch truth values for all premises
            premise_tvs = []
            skip = False
            for pid in premise_ids:
                pm = self.conn.execute(
                    "SELECT truth_degree, truth_modality FROM morphisms WHERE id=?", (pid,)).fetchone()
                if pm is None:
                    skip = True
                    break
                premise_tvs.append(TruthValue(pm["truth_degree"], Modality[pm["truth_modality"]]))
            if skip:
                continue

            # Weakest-premise: compose all premise truth values
            composed = premise_tvs[0]
            for tv in premise_tvs[1:]:
                composed = compose_truth(composed, tv)

            # Write only if truth actually changed (prevents spurious recursion)
            current = self.conn.execute(
                "SELECT truth_degree, truth_modality FROM morphisms WHERE id=?",
                (child_id,)).fetchone()
            if current and (
                abs(composed.degree - current["truth_degree"]) > 1e-6
                or composed.modality.name != current["truth_modality"]
            ):
                self.conn.execute(
                    "UPDATE morphisms SET truth_degree=?, truth_modality=? WHERE id=?",
                    (composed.degree, composed.modality.name, child_id))
                self.conn.commit()
                self._propagate_belief(child_id, depth + 1, max_depth)

    def get_dependents(self, morphism_id: str, recursive: bool = False) -> list[str]:
        """
        Return IDs of all morphisms derived from this one.
        recursive=True returns the full transitive closure.
        """
        direct = [r["derived_id"] for r in self.conn.execute(
            "SELECT derived_id FROM morphism_dependencies WHERE premise_id=?",
            (morphism_id,)).fetchall()]
        if not recursive:
            return direct
        seen = set(direct)
        queue = list(direct)
        while queue:
            mid = queue.pop(0)
            for r in self.conn.execute(
                "SELECT derived_id FROM morphism_dependencies WHERE premise_id=?", (mid,)).fetchall():
                c = r["derived_id"]
                if c not in seen:
                    seen.add(c)
                    queue.append(c)
        return list(seen)

    def check_proof(self, morphism_id: str) -> dict:
        """
        Verify that a derived morphism's proof is valid.

        Checks:
          - All premises exist
          - The rule-specific structural constraints hold
          - For transitivity: the chain is unbroken
          - For composition: endpoints match the conclusion

        Returns {valid, rule, premises, errors}.
        """
        morph = self.conn.execute("SELECT * FROM morphisms WHERE id=?", (morphism_id,)).fetchone()
        if not morph:
            return {"valid": False, "errors": ["Morphism not found"]}
        m = dict(morph)
        if not m["is_inferred"]:
            return {"valid": True, "rule": "axiom", "premises": 0, "errors": []}

        deriv = self.conn.execute(
            "SELECT * FROM derivations WHERE morphism_id=? ORDER BY timestamp DESC LIMIT 1",
            (morphism_id,)).fetchone()
        if not deriv:
            return {"valid": False, "rule": "unknown", "premises": 0,
                    "errors": ["No derivation record found"]}

        rule = deriv["rule"]
        premises = json.loads(deriv["premises"])
        errors = []

        # Check all premises exist
        pm_rows = []
        for pid in premises:
            pm = self.conn.execute("SELECT * FROM morphisms WHERE id=?", (pid,)).fetchone()
            if pm is None:
                errors.append(f"Premise {pid[:12]}… not found in store")
            else:
                pm_rows.append(dict(pm))

        if errors:
            return {"valid": False, "rule": rule, "premises": len(premises), "errors": errors}

        # Rule-specific structural checks
        if rule == "transitivity":
            if len(pm_rows) < 2:
                errors.append(f"transitivity requires ≥2 premises, got {len(pm_rows)}")
            else:
                # Chain must be unbroken: p[i].target == p[i+1].source
                for i in range(len(pm_rows) - 1):
                    if pm_rows[i]["target_label"] != pm_rows[i+1]["source_label"]:
                        errors.append(
                            f"Chain break at step {i}: {pm_rows[i]['target_label']} ≠ {pm_rows[i+1]['source_label']}")
                # Conclusion must span full chain
                if pm_rows[0]["source_label"] != m["source_label"]:
                    errors.append(f"Conclusion source mismatch: expected {pm_rows[0]['source_label']}, got {m['source_label']}")
                if pm_rows[-1]["target_label"] != m["target_label"]:
                    errors.append(f"Conclusion target mismatch: expected {pm_rows[-1]['target_label']}, got {m['target_label']}")

        elif rule in ("composition", "auto_compose"):
            if len(pm_rows) < 2:
                errors.append(f"{rule} requires ≥2 premises")
            else:
                # Source of conclusion should match source of first premise
                if pm_rows[0]["source_label"] != m["source_label"]:
                    errors.append(f"Composition source mismatch")
                if pm_rows[-1]["target_label"] != m["target_label"]:
                    errors.append(f"Composition target mismatch")

        elif rule == "bayesian_update":
            ev = self.conn.execute(
                "SELECT id FROM evidence WHERE morphism_id=? LIMIT 1", (morphism_id,)).fetchone()
            if not ev:
                errors.append("bayesian_update: no evidence record found for this morphism")

        # Truth degree check: derived truth should be ≤ weakest premise
        from .topos import TruthValue, Modality, compose_truth
        if pm_rows:
            composed = TruthValue(pm_rows[0]["truth_degree"], Modality[pm_rows[0]["truth_modality"]])
            for pmr in pm_rows[1:]:
                composed = compose_truth(composed, TruthValue(pmr["truth_degree"], Modality[pmr["truth_modality"]]))
            if abs(m["truth_degree"] - composed.degree) > 0.05:
                errors.append(
                    f"Truth degree drift: stored={m['truth_degree']:.3f}, "
                    f"recomputed={composed.degree:.3f} (delta={abs(m['truth_degree']-composed.degree):.3f})")

        return {
            "valid": len(errors) == 0,
            "rule": rule,
            "premises": len(premises),
            "conclusion": f"{m['source_label']}→{m['target_label']}",
            "truth_degree": m["truth_degree"],
            "errors": errors,
        }

    def normalize_proof_term(self, morphism_id: str) -> str:
        """
        Compute the canonical (beta-normal) proof term for a morphism.

        Properties:
        - Associativity-invariant: (A∘B)∘C == A∘(B∘C)
        - Commutative-rule-invariant: join(A,B) == join(B,A)
        - Deterministic: same derivation always produces the same string
        - Suitable as a cache key for proof deduplication

        Axiom leaf nodes are represented as axiom(source→target) for readability.
        """
        _COMMUTATIVE = {"auto_compose", "conjunction", "meet", "join"}

        def _canonical(mid: str, depth: int = 0) -> str:
            if depth > 25:
                return f"…({mid[:8]})"
            morph = self.conn.execute(
                "SELECT is_inferred, source_label, target_label FROM morphisms WHERE id=?",
                (mid,)).fetchone()
            if not morph or not morph["is_inferred"]:
                if morph:
                    return f"axiom({morph['source_label']}→{morph['target_label']})"
                return f"axiom({mid[:8]})"

            deriv = self.conn.execute(
                "SELECT rule, premises FROM derivations WHERE morphism_id=? ORDER BY timestamp DESC LIMIT 1",
                (mid,)).fetchone()
            if not deriv:
                return f"derived({mid[:8]})"

            rule = deriv["rule"]
            premises = json.loads(deriv["premises"])
            # Recurse
            normalized = [_canonical(p, depth + 1) for p in premises]
            # Sort commutative rules
            if rule in _COMMUTATIVE:
                normalized = sorted(normalized)
            # Flatten nested same-rule (associativity elimination)
            flat = []
            for p in normalized:
                if p.startswith(f"{rule}(") and p.endswith(")"):
                    inner = p[len(rule)+1:-1]
                    flat.extend(_split_args(inner))
                else:
                    flat.append(p)
            return f"{rule}({', '.join(flat)})"

        return _canonical(morphism_id)

    def get_evidence(self, morphism_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM evidence WHERE morphism_id=? ORDER BY timestamp", (morphism_id,)).fetchall()
        return [dict(r) for r in rows]

    def explain_morphism(self, morphism_id: str, depth: int = 0, max_depth: int = 10) -> dict:
        """
        Produce a human-readable proof explanation for a morphism.

        Follows the derivation chain recursively, producing a tree of:
            { morphism, rule, premises: [explain(p1), explain(p2), ...], evidence }

        This is the "scientific notebook" capability: every result can be
        traced back to its axioms and evidence.
        """
        morph = self.conn.execute("SELECT * FROM morphisms WHERE id=?", (morphism_id,)).fetchone()
        if not morph:
            return {"error": f"Morphism {morphism_id} not found"}

        m = dict(morph)
        ev_list = self.get_evidence(morphism_id)

        node = {
            "id": m["id"],
            "label": m["label"],
            "source": m["source_label"],
            "target": m["target_label"],
            "rel_type": m["rel_type"],
            "truth": f"{m['truth_modality']}({m['truth_degree']:.3f})",
            "proof_term": m["proof_term"],
            "is_inferred": bool(m["is_inferred"]),
            "evidence": [
                {"label": e["label"], "direction": e["direction"], "strength": e["strength"]}
                for e in ev_list
            ],
            "premises": [],
        }

        if depth < max_depth and m["is_inferred"]:
            # Look up derivation record for this morphism
            deriv = self.conn.execute(
                "SELECT * FROM derivations WHERE morphism_id=? ORDER BY timestamp DESC LIMIT 1",
                (morphism_id,)).fetchone()
            if deriv:
                node["rule"] = deriv["rule"]
                premise_ids = json.loads(deriv["premises"])
                for pid in premise_ids:
                    child_node = self.explain_morphism(pid, depth + 1, max_depth)
                    node["premises"].append(child_node)

        return node

    def explain_path(self, source_label: str, target_label: str, domain_id: str) -> list[dict]:
        """
        Explain every morphism on a path from source to target in a domain.
        Returns a list of explanation nodes.
        """
        morphisms = self.conn.execute(
            """SELECT * FROM morphisms
               WHERE domain_id=? AND source_label=? AND target_label=?
               AND is_identity=0 ORDER BY truth_degree DESC""",
            (domain_id, source_label, target_label)).fetchall()
        return [self.explain_morphism(m["id"]) for m in morphisms]

    # ── Load/Export Category ───────────────────────────────

    def import_category(self, category: Category, domain_name: str = None) -> str:
        """Import a MORPHOS Category into the persistent store."""
        name = domain_name or category.name
        domain = self.get_domain(name)
        if domain:
            did = domain["id"]
        else:
            did = self.create_domain(name, category.description)
        for obj in category.objects:
            self.add_concept(did, obj)
        for m in category.user_morphisms():
            td = 1.0
            tm = "ACTUAL"
            if m.truth_value:
                td = m.truth_value.degree
                tm = m.truth_value.modality.name
            self.add_morphism(did, m.label, m.source, m.target,
                              rel_type=m.rel_type, value=m.value,
                              truth_degree=td, truth_modality=tm)
        return did

    def export_category(self, domain_id: str) -> Category:
        """Export a domain from the store as a MORPHOS Category."""
        domain = self.conn.execute("SELECT * FROM domains WHERE id=?", (domain_id,)).fetchone()
        if not domain:
            raise ValueError(f"Domain {domain_id} not found")
        concepts = [r["label"] for r in self.get_concepts(domain_id)]
        morphisms = self.get_morphisms(domain_id)
        morph_tuples = [
            (m["label"], m["source_label"], m["target_label"], m["rel_type"], m["value"])
            for m in morphisms if not m["is_identity"]
        ]
        cat = create_category(domain["name"], concepts, morph_tuples, auto_close=False)
        # Attach truth values
        for m_data in morphisms:
            for m in cat.morphisms:
                if m.label == m_data["label"] and m.source == m_data["source_label"] and m.target == m_data["target_label"]:
                    m.truth_value = TruthValue(m_data["truth_degree"], Modality[m_data["truth_modality"]])
                    break
        return cat

    # ── Program (Functor) Registry ────────────────────────

    def register_program(
        self,
        name: str,
        source_domain: str,
        target_domain: str,
        object_map: dict,
        morphism_map: dict = None,
        score: float = 0.0,
        classification: str = "functor",
    ) -> str:
        """Register a discovered functor as a reusable program."""
        # Check for existing version
        existing = self.conn.execute(
            "SELECT * FROM programs WHERE name=? ORDER BY version DESC LIMIT 1",
            (name,)).fetchone()
        version = (existing["version"] + 1) if existing else 1
        pid = str(uuid.uuid4())
        now = time.time()
        self.conn.execute(
            """INSERT INTO programs
               (id, name, version, source_domain, target_domain, object_map, morphism_map,
                score, classification, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, name, version, source_domain, target_domain,
             json.dumps(object_map), json.dumps(morphism_map or {}),
             score, classification, now, now))
        self.conn.commit()
        return pid

    def get_program(self, name: str, version: int = None) -> Optional[dict]:
        if version:
            row = self.conn.execute("SELECT * FROM programs WHERE name=? AND version=?", (name, version)).fetchone()
        else:
            row = self.conn.execute("SELECT * FROM programs WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()
        if row:
            d = dict(row)
            d["object_map"] = json.loads(d["object_map"])
            d["morphism_map"] = json.loads(d["morphism_map"])
            return d
        return None

    def list_programs(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM programs ORDER BY name, version DESC").fetchall()
        return [dict(r) for r in rows]

    def add_program_test(self, program_id: str, test_type: str, input_data: dict, expected: dict) -> str:
        """Add a test assertion for a program."""
        tid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO program_tests (id, program_id, test_type, input_data, expected_output) VALUES (?,?,?,?,?)",
            (tid, program_id, test_type, json.dumps(input_data), json.dumps(expected)))
        self.conn.commit()
        return tid

    def run_program_tests(self, program_id: str) -> dict:
        """Run all tests for a program and return results."""
        program = self.conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
        if not program:
            return {"error": "Program not found"}
        tests = self.conn.execute("SELECT * FROM program_tests WHERE program_id=?", (program_id,)).fetchall()
        obj_map = json.loads(program["object_map"])
        passed = 0
        failed = 0
        results = []
        for test in tests:
            input_data = json.loads(test["input_data"])
            expected = json.loads(test["expected_output"])
            test_type = test["test_type"]
            actual_output = {}
            test_passed = False
            if test_type == "maps_object":
                src = input_data.get("source")
                actual_output = {"target": obj_map.get(src)}
                test_passed = actual_output["target"] == expected.get("target")
            elif test_type == "preserves_morphism":
                src_morph = input_data.get("source_morphism")
                exp_tgt = expected.get("target_morphism")
                # Check if mapping source/target of morphism gives expected
                actual_output = {"mapped": f"{obj_map.get(src_morph.get('source',''))}→{obj_map.get(src_morph.get('target',''))}"}
                test_passed = (obj_map.get(src_morph.get("source")) == exp_tgt.get("source") and
                               obj_map.get(src_morph.get("target")) == exp_tgt.get("target"))
            if test_passed:
                passed += 1
            else:
                failed += 1
            now = time.time()
            self.conn.execute(
                "UPDATE program_tests SET actual_output=?, passed=?, last_run=? WHERE id=?",
                (json.dumps(actual_output), 1 if test_passed else 0, now, test["id"]))
            results.append({"test": test_type, "passed": test_passed, "actual": actual_output})
        self.conn.commit()
        return {"passed": passed, "failed": failed, "total": passed + failed, "results": results}

    def reinforce_program(self, program_id: str):
        """Strengthen a program based on successful test/use."""
        self.conn.execute(
            "UPDATE programs SET confirmations = confirmations + 1, updated_at=? WHERE id=?",
            (time.time(), program_id))
        self.conn.commit()

    # ── Analogy Memory Persistence ────────────────────────

    def store_analogy(
        self,
        analogy_id: str,
        source_name: str,
        target_name: str,
        object_map: dict,
        morphism_map: dict,
        score: float,
        truth_degree: float,
        truth_modality: str,
        discovered_at: float,
        confirmations: int,
        contradictions: int,
        evidence: list,
    ) -> str:
        """Upsert a discovered analogy into persistent storage."""
        now = time.time()
        existing = self.conn.execute(
            "SELECT id FROM analogies WHERE source_name=? AND target_name=?",
            (source_name, target_name)).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE analogies SET object_map=?, morphism_map=?, score=?,
                   truth_degree=?, truth_modality=?, updated_at=?,
                   confirmations=?, contradictions=?, evidence=?
                   WHERE id=?""",
                (json.dumps(object_map), json.dumps(morphism_map), score,
                 truth_degree, truth_modality, now,
                 confirmations, contradictions, json.dumps(evidence),
                 existing["id"]))
            self.conn.commit()
            return existing["id"]
        else:
            self.conn.execute(
                """INSERT INTO analogies
                   (id, source_name, target_name, object_map, morphism_map, score,
                    truth_degree, truth_modality, discovered_at, updated_at,
                    confirmations, contradictions, evidence)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (analogy_id, source_name, target_name,
                 json.dumps(object_map), json.dumps(morphism_map), score,
                 truth_degree, truth_modality, discovered_at, now,
                 confirmations, contradictions, json.dumps(evidence)))
            self.conn.commit()
            return analogy_id

    def load_analogies(
        self,
        source_name: str = None,
        target_name: str = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Load analogies from persistent storage, optionally filtered."""
        if source_name and target_name:
            rows = self.conn.execute(
                "SELECT * FROM analogies WHERE source_name=? AND target_name=? AND score>=?",
                (source_name, target_name, min_score)).fetchall()
        elif source_name:
            rows = self.conn.execute(
                "SELECT * FROM analogies WHERE source_name=? AND score>=?",
                (source_name, min_score)).fetchall()
        elif target_name:
            rows = self.conn.execute(
                "SELECT * FROM analogies WHERE target_name=? AND score>=?",
                (target_name, min_score)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM analogies WHERE score>=? ORDER BY score DESC",
                (min_score,)).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            d["object_map"] = json.loads(d["object_map"])
            d["morphism_map"] = json.loads(d["morphism_map"])
            d["evidence"] = json.loads(d["evidence"])
            results.append(d)
        return results

    def delete_analogy(self, analogy_id: str):
        """Remove an analogy from persistent storage."""
        self.conn.execute("DELETE FROM analogies WHERE id=?", (analogy_id,))
        self.conn.commit()

    def store_fingerprint(
        self,
        cat_name: str,
        n_objects: int,
        n_morphisms: int,
        degree_sequence: list,
        n_rel_types: int,
        freq_distribution: list,
        has_cycles: bool,
        max_chain_length: int,
    ):
        """Upsert a category fingerprint."""
        now = time.time()
        self.conn.execute(
            """INSERT OR REPLACE INTO category_fingerprints
               (cat_name, n_objects, n_morphisms, degree_sequence, n_rel_types,
                freq_distribution, has_cycles, max_chain_length, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (cat_name, n_objects, n_morphisms,
             json.dumps(degree_sequence), n_rel_types,
             json.dumps(freq_distribution), int(has_cycles), max_chain_length, now))
        self.conn.commit()

    def load_fingerprints(self) -> dict[str, dict]:
        """Load all stored fingerprints. Returns {cat_name: fingerprint_dict}."""
        rows = self.conn.execute("SELECT * FROM category_fingerprints").fetchall()
        result = {}
        for row in rows:
            d = dict(row)
            d["degree_sequence"] = json.loads(d["degree_sequence"])
            d["freq_distribution"] = json.loads(d["freq_distribution"])
            d["has_cycles"] = bool(d["has_cycles"])
            result[d["cat_name"]] = d
        return result


    def extract_common_core(
        self,
        source_domain_id: str,
        target_domain_id: str,
        object_map: dict,
        new_domain_name: str = None,
    ) -> Optional[str]:
        """
        Extract the structural core shared by two domains under an analogy.

        Given a functor F (as an object_map: source_obj → target_obj), finds
        all source morphisms s→t where both s and t are mapped by F AND where
        a corresponding morphism F(s)→F(t) exists in the target domain.

        These invariant pairs form the "common core" — a new category that
        represents the abstract structure shared by both domains, independent
        of domain-specific labels.

        This is the categorical pullback of the two domains over F:
            P = source ×_F target

        Returns the new domain ID, or None if no common morphisms exist.
        """
        src_morphs = self.get_morphisms(source_domain_id)
        tgt_morphs = self.get_morphisms(target_domain_id)

        # Build target lookup by (source_label, target_label)
        tgt_lookup: dict[tuple, dict] = {}
        for m in tgt_morphs:
            tgt_lookup[(m["source_label"], m["target_label"])] = m

        # Find invariant pairs: source morphisms preserved under F
        invariant = []
        for sm in src_morphs:
            if sm["is_identity"]:
                continue
            src_key = sm["source_label"]
            tgt_key = sm["target_label"]
            if src_key in object_map and tgt_key in object_map:
                mapped_src = object_map[src_key]
                mapped_tgt = object_map[tgt_key]
                tm = tgt_lookup.get((mapped_src, mapped_tgt))
                if tm:
                    invariant.append({"source_morph": sm, "target_morph": tm})

        if not invariant:
            return None

        # Create new domain for the common core
        src_dom = self.conn.execute("SELECT name FROM domains WHERE id=?", (source_domain_id,)).fetchone()
        tgt_dom = self.conn.execute("SELECT name FROM domains WHERE id=?", (target_domain_id,)).fetchone()
        src_name = src_dom["name"] if src_dom else source_domain_id[:8]
        tgt_name = tgt_dom["name"] if tgt_dom else target_domain_id[:8]
        name = new_domain_name or f"core_{src_name}∩{tgt_name}"
        new_did = self.create_domain(
            name,
            f"Common structural core: {src_name} ∩ {tgt_name} under functor F")

        # Populate with invariant morphisms (labelled from source domain)
        for pair in invariant:
            sm = pair["source_morph"]
            tm = pair["target_morph"]
            # Average truth degree — both domains agree on this structure
            avg_truth = (sm["truth_degree"] + tm["truth_degree"]) / 2
            pt = ProofTerm(
                rule="extraction",
                premises=[sm["id"], tm["id"]],
                metadata={"method": "categorical_pullback",
                          "source_domain": src_name, "target_domain": tgt_name},
            )
            mid = self.add_morphism(
                new_did, sm["label"], sm["source_label"], sm["target_label"],
                sm["rel_type"],
                truth_degree=avg_truth,
                truth_modality="PROBABLE" if avg_truth < 1.0 else "ACTUAL",
                proof_term=pt.to_json(),
                created_by="structure_extraction",
            )
            # Record derivation for the extracted morphism
            deriv_id = str(uuid.uuid4())
            premises = [sm["id"], tm["id"]]
            self.conn.execute(
                "INSERT INTO derivations (id, morphism_id, rule, premises, conclusion, truth_degree, timestamp) "
                "VALUES (?,?,?,?,?,?,?)",
                (deriv_id, mid, "extraction", json.dumps(premises),
                 f"{sm['source_label']}→{sm['target_label']}", avg_truth, time.time()))
            for prem_id in premises:
                exists = self.conn.execute("SELECT 1 FROM morphisms WHERE id=?", (prem_id,)).fetchone()
                if exists:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO morphism_dependencies "
                        "(premise_id, derived_id, rule, created_at) VALUES (?,?,?,?)",
                        (prem_id, mid, "extraction", time.time()))
        self.conn.commit()
        return new_did

    # ── Stats ─────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        domains = self.conn.execute("SELECT COUNT(*) as c FROM domains").fetchone()["c"]
        concepts = self.conn.execute("SELECT COUNT(*) as c FROM concepts").fetchone()["c"]
        morphisms = self.conn.execute("SELECT COUNT(*) as c FROM morphisms WHERE is_identity=0").fetchone()["c"]
        evidence = self.conn.execute("SELECT COUNT(*) as c FROM evidence").fetchone()["c"]
        derivations = self.conn.execute("SELECT COUNT(*) as c FROM derivations").fetchone()["c"]
        programs = self.conn.execute("SELECT COUNT(*) as c FROM programs").fetchone()["c"]
        tasks = self.conn.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
        dependencies = self.conn.execute("SELECT COUNT(*) as c FROM morphism_dependencies").fetchone()["c"]
        return {
            "domains": domains, "concepts": concepts, "morphisms": morphisms,
            "evidence": evidence, "derivations": derivations,
            "dependencies": dependencies,
            "programs": programs, "tasks": tasks,
        }


# ══════════════════════════════════════════════════════════════
# 2. TASK SCHEDULER — Reasoning jobs as first-class processes
# ══════════════════════════════════════════════════════════════

TASK_TYPES = {
    "compose":    "Compute compositions in a domain",
    "speculate":  "Generate candidate morphisms",
    "map":        "Find structural analogy between domains",
    "learn":      "Store and reinforce an analogy",
    "infer":      "Run typed inference (transitive closure, etc.)",
    "verify":     "Check categorical laws",
    "snapshot":   "Create versioned snapshot of a domain",
    "test":       "Run program test suite",
}


class TaskScheduler:
    """
    Schedules and executes reasoning tasks.

    Each task produces artifacts (new morphisms, functors, evidence)
    that are recorded in the persistent store.
    """

    def __init__(self, store: ReasoningStore):
        self.store = store
        self._handlers: dict[str, callable] = {}

    def register_handler(self, task_type: str, handler: callable):
        """Register a handler function for a task type."""
        self._handlers[task_type] = handler

    def submit(self, task_type: str, params: dict, priority: int = 0) -> str:
        """Submit a reasoning task. Returns task ID."""
        if task_type not in TASK_TYPES and task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")
        tid = str(uuid.uuid4())
        self.store.conn.execute(
            "INSERT INTO tasks (id, task_type, status, priority, params, created_at) VALUES (?,?,?,?,?,?)",
            (tid, task_type, "pending", priority, json.dumps(params), time.time()))
        self.store.conn.commit()
        return tid

    def execute(self, task_id: str) -> dict:
        """Execute a task immediately. Returns result."""
        row = self.store.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"Task {task_id} not found")
        if row["status"] != "pending":
            return {"error": f"Task already {row['status']}"}

        task_type = row["task_type"]
        params = json.loads(row["params"])

        # Mark as running
        start = time.time()
        self.store.conn.execute(
            "UPDATE tasks SET status='running', started_at=? WHERE id=?",
            (start, task_id))

        try:
            handler = self._handlers.get(task_type)
            if handler:
                result = handler(self.store, params)
            else:
                result = self._builtin_handler(task_type, params)

            duration = (time.time() - start) * 1000
            self.store.conn.execute(
                "UPDATE tasks SET status='completed', result=?, completed_at=?, duration_ms=? WHERE id=?",
                (json.dumps(result, default=str), time.time(), duration, task_id))
            self.store.conn.commit()
            return result

        except Exception as e:
            self.store.conn.execute(
                "UPDATE tasks SET status='failed', error=?, completed_at=? WHERE id=?",
                (str(e), time.time(), task_id))
            self.store.conn.commit()
            return {"error": str(e)}

    def run_next(self) -> Optional[dict]:
        """Execute the highest-priority pending task."""
        row = self.store.conn.execute(
            "SELECT id FROM tasks WHERE status='pending' ORDER BY priority DESC, created_at ASC LIMIT 1"
        ).fetchone()
        if row:
            return self.execute(row["id"])
        return None

    def run_all_pending(self) -> list[dict]:
        """Execute all pending tasks in priority order."""
        results = []
        while True:
            result = self.run_next()
            if result is None:
                break
            results.append(result)
        return results

    def get_task(self, task_id: str) -> Optional[dict]:
        row = self.store.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, status: str = None) -> list[dict]:
        if status:
            rows = self.store.conn.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = self.store.conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def _builtin_handler(self, task_type: str, params: dict) -> dict:
        """Handle built-in task types."""
        if task_type == "verify":
            domain_name = params.get("domain_name") or params.get("domain_id")
            d = (self.store.get_domain(domain_name) if domain_name and not domain_name.startswith(("0","1","2","3","4","5","6","7","8","9","a","b","c","d","e","f"))
                 else None)
            domain_id = d["id"] if d else domain_name
            cat = self.store.export_category(domain_id)
            return cat.verify()

        elif task_type == "snapshot":
            domain_name = params.get("domain_name") or params.get("domain_id")
            d = self.store.get_domain(domain_name)
            domain_id = d["id"] if d else domain_name
            new_id = self.store.snapshot_domain(domain_id)
            return {"snapshot_id": new_id}

        elif task_type == "test":
            program_id = params.get("program_id")
            return self.store.run_program_tests(program_id)

        elif task_type == "compose":
            domain_name = params.get("domain_name") or params.get("domain_id")
            d = self.store.get_domain(domain_name)
            if not d:
                return {"error": f"Domain '{domain_name}' not found"}
            cat = self.store.export_category(d["id"])
            new_morphs = cat.auto_compose()
            # Persist new compositions back to the store
            stored = 0
            for m in cat.morphisms:
                if m.is_composition:
                    existing = self.store.conn.execute(
                        "SELECT id FROM morphisms WHERE domain_id=? AND label=? AND source_label=? AND target_label=?",
                        (d["id"], m.label, m.source, m.target)).fetchone()
                    if not existing:
                        self.store.add_derived_morphism(
                            d["id"], m.label, m.source, m.target, m.rel_type or "composition",
                            "auto_compose", [], truth_degree=0.9, truth_modality="PROBABLE")
                        stored += 1
            return {"new_compositions": len(new_morphs), "stored_to_kernel": stored,
                    "total_morphisms": len(cat.morphisms)}

        elif task_type == "speculate":
            domain_name = params.get("domain_name") or params.get("domain_id")
            d = self.store.get_domain(domain_name)
            if not d:
                return {"error": f"Domain '{domain_name}' not found"}
            from engine.speculation import speculate_morphisms, speculation_report
            cat = self.store.export_category(d["id"])
            candidates = speculate_morphisms(cat)
            return {
                "speculated": len(candidates),
                "report": speculation_report(cat),
                "candidates": [
                    {"label": c["label"], "source": c["source"], "target": c["target"],
                     "score": c.get("value")}
                    for c in candidates[:10]
                ],
            }

        elif task_type == "infer":
            domain_name = params.get("domain_name") or params.get("domain_id")
            rule = params.get("rule", "transitivity")
            d = self.store.get_domain(domain_name)
            if not d:
                return {"error": f"Domain '{domain_name}' not found"}
            cat = self.store.export_category(d["id"])
            inferred = 0
            if rule == "transitivity":
                # Find all a→b and b→c with same rel_type, infer a→c
                um = cat.user_morphisms()
                # Build id lookup: (source, target, rel_type) → morphism_id
                morph_id_map = {}
                for row in self.store.get_morphisms(d["id"]):
                    key = (row["source_label"], row["target_label"], row["rel_type"])
                    morph_id_map[key] = row["id"]

                for m1 in um:
                    for m2 in um:
                        if m1.target == m2.source and m1.rel_type == m2.rel_type:
                            exists = self.store.conn.execute(
                                "SELECT id FROM morphisms WHERE domain_id=? AND source_label=? AND target_label=? AND rel_type=? AND is_inferred=1",
                                (d["id"], m1.source, m2.target, m1.rel_type)).fetchone()
                            if not exists and m1.source != m2.target:
                                from .topos import compose_truth
                                td = compose_truth(
                                    m1.truth_value or actual(1.0),
                                    m2.truth_value or actual(1.0))

                                # Look up premise morphism IDs for belief propagation
                                m1_id = morph_id_map.get((m1.source, m1.target, m1.rel_type))
                                m2_id = morph_id_map.get((m2.source, m2.target, m2.rel_type))
                                premises = [p for p in [m1_id, m2_id] if p]

                                derived_id = self.store.add_morphism(
                                    d["id"],
                                    f"{m1.label}∘{m2.label}",
                                    m1.source, m2.target, m1.rel_type,
                                    truth_degree=td.degree,
                                    truth_modality=td.modality.name,
                                    proof_term=f"transitivity({'_'.join(premises)[:60]})",
                                    created_by="inference:transitivity",
                                )
                                # Mark inferred and write derivation with morphism IDs
                                self.store.conn.execute(
                                    "UPDATE morphisms SET is_inferred=1, derivation_depth=2 WHERE id=?",
                                    (derived_id,))
                                deriv_id = str(uuid.uuid4())
                                now_t = time.time()
                                self.store.conn.execute(
                                    "INSERT INTO derivations (id, morphism_id, rule, premises, conclusion, truth_degree, timestamp) VALUES (?,?,?,?,?,?,?)",
                                    (deriv_id, derived_id, "transitivity",
                                     json.dumps(premises),
                                     f"{m1.source}→{m2.target}", td.degree, now_t))
                                # Populate dependency index
                                for prem_id in premises:
                                    self.store.conn.execute(
                                        "INSERT OR IGNORE INTO morphism_dependencies "
                                        "(premise_id, derived_id, rule, created_at) VALUES (?,?,?,?)",
                                        (prem_id, derived_id, "transitivity", now_t))
                                self.store.conn.commit()
                                inferred += 1
            return {"rule": rule, "new_inferences": inferred}

        elif task_type == "map":
            source_name = params.get("source_domain") or params.get("source_domain_id")
            target_name = params.get("target_domain") or params.get("target_domain_id")
            method = params.get("method", "csp")

            # Accept either a domain name (str) or a domain ID (UUID)
            def _resolve_domain(name_or_id):
                d = self.store.get_domain(name_or_id)
                if d:
                    return d
                # Maybe it's a UUID / direct domain_id
                row = self.store.conn.execute("SELECT * FROM domains WHERE id=?", (name_or_id,)).fetchone()
                return dict(row) if row else None

            src_domain = _resolve_domain(source_name) if source_name else None
            tgt_domain = _resolve_domain(target_name) if target_name else None
            if not src_domain:
                return {"error": f"Domain '{source_name}' not found"}
            if not tgt_domain:
                return {"error": f"Domain '{target_name}' not found"}
            source_cat = self.store.export_category(src_domain["id"])
            target_cat = self.store.export_category(tgt_domain["id"])
            from .scale import find_analogies_csp, embedding_assisted_search
            if method == "embedding":
                results = embedding_assisted_search(source_cat, target_cat)
            else:
                results = find_analogies_csp(source_cat, target_cat, max_results=3)
            if results:
                best = results[0]
                pid = self.store.register_program(
                    f"{source_cat.name}→{target_cat.name}",
                    source_cat.name, target_cat.name,
                    best["object_map"], score=best["score"])
                return {"analogies": len(results), "best_score": best["score"],
                        "structural_score": best.get("structural_score"),
                        "semantic_score": best.get("semantic_score"),
                        "program_id": pid, "object_map": best["object_map"]}
            return {"analogies": 0}

        elif task_type == "learn":
            source_name = params.get("source_domain")
            target_name = params.get("target_domain")
            from .learning import AnalogyMemory, learn_and_search
            # Use an in-memory memory here; the server wires a persistent one
            mem = AnalogyMemory()
            src_domain = self.store.get_domain(source_name)
            tgt_domain = self.store.get_domain(target_name)
            if not src_domain or not tgt_domain:
                return {"error": "Domain not found"}
            sc = self.store.export_category(src_domain["id"])
            tc = self.store.export_category(tgt_domain["id"])
            analogies = learn_and_search(sc, tc, mem, min_score=0.0)
            return {"analogies": len(analogies), "memory_stats": mem.stats}

        return {"error": f"No handler for {task_type}"}
