"""
Epistemic Status Tracking

Every morphism in MORPHOS carries an epistemic tag indicating confidence level.
When morphisms are composed, epistemic status propagates according to rules
that mirror how certainty degrades through inference chains.
"""
from __future__ import annotations
from dataclasses import dataclass
import re


class EpistemicStatus:
    """Base class for epistemic statuses."""

    def strength(self) -> float:
        raise NotImplementedError

    def label(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Definite(EpistemicStatus):
    """Verified or axiomatic — known with certainty."""

    def strength(self) -> float:
        return 1.0

    def label(self) -> str:
        return "definite"


@dataclass(frozen=True)
class Probable(EpistemicStatus):
    """Statistical confidence — known with probability p in (0, 1]."""

    confidence: float

    def __post_init__(self):
        if not (0.0 < self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in (0, 1], got {self.confidence}")

    def strength(self) -> float:
        return self.confidence

    def label(self) -> str:
        return f"probable({self.confidence:.3f})"


@dataclass(frozen=True)
class Possible(EpistemicStatus):
    """Structurally consistent but not yet evaluated."""

    def strength(self) -> float:
        return 0.3

    def label(self) -> str:
        return "possible"


@dataclass(frozen=True)
class Speculative(EpistemicStatus):
    """System-generated candidate — requires user validation."""

    def strength(self) -> float:
        return 0.1

    def label(self) -> str:
        return "speculative"


@dataclass(frozen=True)
class Contradicted(EpistemicStatus):
    """Inconsistent with existing structure — flagged for resolution."""

    reason: str = ""

    def strength(self) -> float:
        return 0.0

    def label(self) -> str:
        return f"contradicted: {self.reason}" if self.reason else "contradicted"


def compose_epistemic(s1: EpistemicStatus, s2: EpistemicStatus) -> EpistemicStatus:
    """
    Determine epistemic status of a composed morphism g∘f given statuses of f and g.
    Certainty can only degrade through composition, never improve.
    """
    if isinstance(s1, Contradicted):
        return s1
    if isinstance(s2, Contradicted):
        return s2
    if isinstance(s1, Speculative) or isinstance(s2, Speculative):
        return Speculative()
    if isinstance(s1, Possible) or isinstance(s2, Possible):
        return Possible()
    if isinstance(s1, Definite) and isinstance(s2, Definite):
        return Definite()
    if isinstance(s1, Definite) and isinstance(s2, Probable):
        return Probable(s2.confidence)
    if isinstance(s1, Probable) and isinstance(s2, Definite):
        return Probable(s1.confidence)
    if isinstance(s1, Probable) and isinstance(s2, Probable):
        return Probable(s1.confidence * s2.confidence)
    return Possible()


def parse_epistemic(s: str) -> EpistemicStatus:
    """Parse an epistemic status from its string label."""
    if not s:
        return Definite()
    s = s.strip()
    if not s or s == "definite":
        return Definite()
    m = re.match(r"probable\(([0-9.]+)\)", s)
    if m:
        return Probable(float(m.group(1)))
    if s == "possible":
        return Possible()
    if s == "speculative":
        return Speculative()
    if s.startswith("contradicted"):
        reason = s.replace("contradicted:", "").replace("contradicted", "").strip()
        return Contradicted(reason)
    return Possible()
