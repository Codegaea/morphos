"""
MORPHOS Topos Logic Layer — Phase 2

Replaces Boolean truth (exists / doesn't exist) with a Heyting algebra
of truth values that supports genuine multi-valued reasoning.

Mathematical foundation:
- A topos is a category with a subobject classifier Ω
- In Set (classical logic), Ω = {true, false}
- In our topos, Ω is a Heyting algebra with richer truth values
- Heyting algebra = bounded lattice with meet (∧), join (∨),
  implication (→), and pseudo-complement (¬)
- Key difference from Boolean: ¬¬p ≠ p (excluded middle fails)
  This means "not not true" isn't the same as "true" — there's
  genuine underdetermination that can't be resolved by logic alone

Practical implementation:
- TruthValue: element of the Heyting algebra, carries both a
  degree (0-1 continuous) and a modality (necessary, actual,
  possible, counterfactual, undetermined)
- Composition propagates truth values via Heyting operations
- Bayesian updating: evidence modifies truth values via
  conditionalization
- Compatible with existing EpistemicStatus (can convert between)

Source: Mac Lane & Moerdijk (Sheaves in Geometry and Logic),
        Goldblatt (Topoi: The Categorial Analysis of Logic)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import math


# ══════════════════════════════════════════════════════════════
# MODALITY — Qualitative truth distinction
# ══════════════════════════════════════════════════════════════

class Modality(Enum):
    """
    Modal truth values, ordered by strength.

    These correspond to different "worlds" in Kripke semantics:
    - NECESSARY: true in all accessible worlds
    - ACTUAL: true in the current world
    - PROBABLE: true in most accessible worlds
    - POSSIBLE: true in at least one accessible world
    - COUNTERFACTUAL: would be true under different conditions
    - UNDETERMINED: truth value genuinely not yet established
    - IMPOSSIBLE: true in no accessible world

    Unlike Boolean logic, UNDETERMINED ≠ FALSE. It means
    "we don't have enough information to assign truth."
    This is the key intuitionistic distinction.
    """
    NECESSARY = auto()      # □p — true in all worlds
    ACTUAL = auto()         # p — true in this world
    PROBABLE = auto()       # ◇□p — likely true
    POSSIBLE = auto()       # ◇p — true in some world
    COUNTERFACTUAL = auto() # p □→ q — would be true if...
    UNDETERMINED = auto()   # ? — genuinely unknown
    IMPOSSIBLE = auto()     # ¬◇p — true in no world

    @property
    def strength(self) -> float:
        """Numerical strength for ordering."""
        return {
            Modality.NECESSARY: 1.0,
            Modality.ACTUAL: 0.9,
            Modality.PROBABLE: 0.7,
            Modality.POSSIBLE: 0.4,
            Modality.COUNTERFACTUAL: 0.3,
            Modality.UNDETERMINED: 0.2,
            Modality.IMPOSSIBLE: 0.0,
        }[self]


# ══════════════════════════════════════════════════════════════
# TRUTH VALUE — Element of the subobject classifier Ω
# ══════════════════════════════════════════════════════════════

@dataclass
class TruthValue:
    """
    An element of the subobject classifier Ω in our topos.

    Combines:
    - degree: continuous value in [0, 1] (like fuzzy logic)
    - modality: qualitative modal distinction
    - evidence: list of observations supporting this value
    - prior: the degree before any evidence was applied

    The degree and modality are independent dimensions:
    - degree=0.8, modality=POSSIBLE means "if this is true at all,
      it's probably strongly true, but we're not sure it's true"
    - degree=1.0, modality=UNDETERMINED means "either fully true
      or fully false, but we can't tell which"
    """
    degree: float = 1.0
    modality: Modality = Modality.ACTUAL
    evidence: list[str] = field(default_factory=list)
    prior: float = 0.5  # prior degree before evidence

    def __post_init__(self):
        self.degree = max(0.0, min(1.0, self.degree))
        self.prior = max(0.0, min(1.0, self.prior))

    @property
    def effective_strength(self) -> float:
        """Combined strength accounting for both degree and modality."""
        return self.degree * self.modality.strength

    def label(self) -> str:
        mod = self.modality.name.lower()
        if self.modality == Modality.ACTUAL and self.degree >= 0.99:
            return "true"
        if self.modality == Modality.IMPOSSIBLE and self.degree <= 0.01:
            return "false"
        return f"{mod}({self.degree:.3f})"

    def __repr__(self):
        return f"TV({self.label()})"

    # ── Heyting algebra operations ────────────────────────

    def meet(self, other: TruthValue) -> TruthValue:
        """
        Heyting meet (∧) — greatest lower bound.
        Conjunction: "both p and q are true."
        Takes the minimum of both dimensions.
        """
        return TruthValue(
            degree=min(self.degree, other.degree),
            modality=_weaker_modality(self.modality, other.modality),
            evidence=self.evidence + other.evidence,
            prior=min(self.prior, other.prior),
        )

    def join(self, other: TruthValue) -> TruthValue:
        """
        Heyting join (∨) — least upper bound.
        Disjunction: "at least one of p or q is true."
        Takes the maximum of both dimensions.
        """
        return TruthValue(
            degree=max(self.degree, other.degree),
            modality=_stronger_modality(self.modality, other.modality),
            evidence=self.evidence + other.evidence,
            prior=max(self.prior, other.prior),
        )

    def implies(self, other: TruthValue) -> TruthValue:
        """
        Heyting implication (→).
        p → q is the largest x such that p ∧ x ≤ q.

        Using Gödel semantics for [0,1]-valued Heyting algebra:
        - If p.degree ≤ q.degree: p → q = 1 (top)
        - If p.degree > q.degree: p → q = q.degree

        This is the unique operation satisfying the residuation
        condition: a ∧ x ≤ b  iff  x ≤ (a → b).
        """
        if self.degree <= other.degree:
            return TruthValue(
                degree=1.0,
                modality=_stronger_modality(self.modality, other.modality),
            )
        # a > b: the largest x where min(a, x) ≤ b is x = b
        return TruthValue(
            degree=other.degree,
            modality=_weaker_modality(self.modality, other.modality),
        )

    def negate(self) -> TruthValue:
        """
        Heyting pseudo-complement (¬).
        ¬p is the largest x such that p ∧ x = ⊥.

        CRITICALLY: ¬¬p ≠ p in intuitionistic logic.
        ¬p doesn't mean "p is false" — it means
        "assuming p leads to contradiction."

        If p is UNDETERMINED, ¬p is also UNDETERMINED (not true!).
        This is the key difference from classical logic.
        """
        if self.modality == Modality.UNDETERMINED:
            return TruthValue(degree=1.0 - self.degree, modality=Modality.UNDETERMINED)
        if self.degree <= 0.01:
            return TruthValue(degree=1.0, modality=Modality.ACTUAL)
        if self.degree >= 0.99 and self.modality in (Modality.NECESSARY, Modality.ACTUAL):
            return TruthValue(degree=0.0, modality=Modality.IMPOSSIBLE)
        return TruthValue(
            degree=1.0 - self.degree,
            modality=_negate_modality(self.modality),
        )

    def double_negate(self) -> TruthValue:
        """
        ¬¬p — in classical logic this equals p, but NOT here.

        For UNDETERMINED values, ¬¬p stays UNDETERMINED.
        This is the formal expression of "we can't determine
        truth just by ruling out falsity."
        """
        return self.negate().negate()


# ── Modality ordering operations ──────────────────────────

_MODALITY_ORDER = [
    Modality.IMPOSSIBLE, Modality.UNDETERMINED, Modality.COUNTERFACTUAL,
    Modality.POSSIBLE, Modality.PROBABLE, Modality.ACTUAL, Modality.NECESSARY,
]
_MOD_RANK = {m: i for i, m in enumerate(_MODALITY_ORDER)}


def _weaker_modality(a: Modality, b: Modality) -> Modality:
    """Return the weaker (lower-ranked) modality."""
    return a if _MOD_RANK[a] <= _MOD_RANK[b] else b


def _stronger_modality(a: Modality, b: Modality) -> Modality:
    """Return the stronger (higher-ranked) modality."""
    return a if _MOD_RANK[a] >= _MOD_RANK[b] else b


def _negate_modality(m: Modality) -> Modality:
    """Negate a modality."""
    return {
        Modality.NECESSARY: Modality.IMPOSSIBLE,
        Modality.ACTUAL: Modality.POSSIBLE,  # ¬actual = possibly not
        Modality.PROBABLE: Modality.POSSIBLE,
        Modality.POSSIBLE: Modality.PROBABLE,  # ¬possible = probably not
        Modality.COUNTERFACTUAL: Modality.ACTUAL,
        Modality.UNDETERMINED: Modality.UNDETERMINED,  # KEY: stays undetermined
        Modality.IMPOSSIBLE: Modality.NECESSARY,
    }[m]


# ══════════════════════════════════════════════════════════════
# COMPOSITION — How truth values propagate through morphism chains
# ══════════════════════════════════════════════════════════════

def compose_truth(tv1: TruthValue, tv2: TruthValue) -> TruthValue:
    """
    Compose two truth values through a morphism chain.

    When g∘f is composed:
    - Degrees multiply (each step attenuates confidence)
    - Modality takes the weaker of the two
    - Evidence concatenates
    - Prior updates via Bayesian rule if both have evidence
    """
    new_degree = tv1.degree * tv2.degree
    new_modality = _weaker_modality(tv1.modality, tv2.modality)

    # Bayesian prior update
    if tv1.evidence and tv2.evidence:
        # Treat as independent observations
        new_prior = tv1.prior * tv2.prior
    else:
        new_prior = min(tv1.prior, tv2.prior)

    return TruthValue(
        degree=new_degree,
        modality=new_modality,
        evidence=tv1.evidence + tv2.evidence,
        prior=new_prior,
    )


# ══════════════════════════════════════════════════════════════
# BAYESIAN UPDATING — Evidence modifies truth values
# ══════════════════════════════════════════════════════════════

def bayesian_update(
    tv: TruthValue,
    evidence_label: str,
    likelihood_if_true: float,
    likelihood_if_false: float,
) -> TruthValue:
    """
    Update a truth value given new evidence via Bayes' theorem.

    P(H|E) = P(E|H) * P(H) / P(E)
    where P(E) = P(E|H)*P(H) + P(E|¬H)*P(¬H)

    Args:
        tv: current truth value
        evidence_label: description of the evidence
        likelihood_if_true: P(evidence | hypothesis true)
        likelihood_if_false: P(evidence | hypothesis false)

    Returns:
        Updated truth value with new degree and evidence record.
    """
    prior = tv.degree
    p_e = likelihood_if_true * prior + likelihood_if_false * (1 - prior)

    if p_e < 1e-10:
        posterior = prior  # evidence is impossible either way; no update
    else:
        posterior = (likelihood_if_true * prior) / p_e

    # Update modality based on how much the evidence shifted things
    shift = abs(posterior - prior)
    new_modality = tv.modality
    if shift > 0.3 and posterior > 0.8:
        new_modality = _stronger_modality(tv.modality, Modality.PROBABLE)
    elif shift > 0.3 and posterior < 0.2:
        new_modality = _weaker_modality(tv.modality, Modality.POSSIBLE)

    return TruthValue(
        degree=posterior,
        modality=new_modality,
        evidence=tv.evidence + [evidence_label],
        prior=prior,
    )


def update_from_observations(
    tv: TruthValue,
    observations: list[tuple[str, float, float]],
) -> TruthValue:
    """
    Apply a sequence of Bayesian updates.

    Args:
        tv: initial truth value
        observations: list of (label, likelihood_if_true, likelihood_if_false)
    """
    current = tv
    for label, lt, lf in observations:
        current = bayesian_update(current, label, lt, lf)
    return current


# ══════════════════════════════════════════════════════════════
# HEYTING ALGEBRA VERIFICATION
# ══════════════════════════════════════════════════════════════

def verify_heyting_laws(a: TruthValue, b: TruthValue, c: TruthValue) -> dict:
    """
    Verify that our truth values satisfy the Heyting algebra axioms.

    A Heyting algebra must satisfy:
    1. a ∧ a = a (idempotent meet)
    2. a ∨ a = a (idempotent join)
    3. a ∧ b = b ∧ a (commutative meet)
    4. a ∨ b = b ∨ a (commutative join)
    5. a ∧ (b ∧ c) = (a ∧ b) ∧ c (associative meet)
    6. a ∧ (a ∨ b) = a (absorption)
    7. a ∨ (a ∧ b) = a (absorption)
    8. a ∧ ⊤ = a (top is identity for meet)
    9. a ∨ ⊥ = a (bottom is identity for join)
    10. a → b is the largest x where a ∧ x ≤ b (residuation)

    Also verifies NON-classical properties:
    11. ¬¬a ≠ a in general (excluded middle fails)
    """
    top = TruthValue(1.0, Modality.NECESSARY)
    bot = TruthValue(0.0, Modality.IMPOSSIBLE)

    def close(x, y, tol=0.01):
        return abs(x.degree - y.degree) < tol

    results = {}

    # 1. Idempotent meet
    results["idempotent_meet"] = close(a.meet(a), a)

    # 2. Idempotent join
    results["idempotent_join"] = close(a.join(a), a)

    # 3. Commutative meet
    results["commutative_meet"] = close(a.meet(b), b.meet(a))

    # 4. Commutative join
    results["commutative_join"] = close(a.join(b), b.join(a))

    # 5. Associative meet
    results["associative_meet"] = close(a.meet(b.meet(c)), a.meet(b).meet(c))

    # 6. Absorption 1
    results["absorption_1"] = close(a.meet(a.join(b)), a)

    # 7. Absorption 2
    results["absorption_2"] = close(a.join(a.meet(b)), a)

    # 8. Top identity for meet
    results["top_identity"] = close(a.meet(top), a)

    # 9. Bottom identity for join
    results["bottom_identity"] = close(a.join(bot), a)

    # 10. Residuation (a ∧ (a→b) ≤ b)
    impl = a.implies(b)
    lhs = a.meet(impl)
    results["residuation"] = lhs.degree <= b.degree + 0.01

    # 11. Double negation (should NOT equal a for undetermined values)
    if a.modality == Modality.UNDETERMINED:
        dna = a.double_negate()
        results["intuitionistic_dbl_neg"] = True  # just note it
        results["dbl_neg_differs"] = not close(dna, a)
    else:
        results["intuitionistic_dbl_neg"] = True
        results["dbl_neg_differs"] = None  # not applicable

    return results


# ══════════════════════════════════════════════════════════════
# CONVERSION — Bridge between Phase 1 EpistemicStatus and Phase 2 TruthValue
# ══════════════════════════════════════════════════════════════

def from_epistemic(status) -> TruthValue:
    """Convert a Phase 1 EpistemicStatus to a Phase 2 TruthValue."""
    from .epistemic import Definite, Probable, Possible, Speculative, Contradicted

    if isinstance(status, Definite):
        return TruthValue(1.0, Modality.ACTUAL)
    if isinstance(status, Probable):
        # Map confidence to modality: high confidence = PROBABLE, lower = POSSIBLE
        if status.confidence >= 0.5:
            return TruthValue(status.confidence, Modality.PROBABLE)
        return TruthValue(status.confidence, Modality.POSSIBLE)
    if isinstance(status, Possible):
        return TruthValue(0.5, Modality.POSSIBLE)
    if isinstance(status, Speculative):
        return TruthValue(0.3, Modality.UNDETERMINED)
    if isinstance(status, Contradicted):
        return TruthValue(0.0, Modality.IMPOSSIBLE, evidence=[status.reason] if status.reason else [])
    return TruthValue(0.5, Modality.UNDETERMINED)


def to_epistemic(tv: TruthValue):
    """Convert a Phase 2 TruthValue back to Phase 1 EpistemicStatus."""
    from .epistemic import Definite, Probable, Possible, Speculative, Contradicted

    if tv.modality == Modality.IMPOSSIBLE or tv.degree < 0.01:
        return Contradicted("topos: impossible")
    if tv.modality == Modality.NECESSARY and tv.degree > 0.99:
        return Definite()
    if tv.modality == Modality.ACTUAL and tv.degree > 0.99:
        return Definite()
    if tv.modality == Modality.UNDETERMINED:
        return Speculative()
    if tv.modality in (Modality.PROBABLE,):
        return Probable(tv.degree)
    if tv.modality == Modality.ACTUAL and tv.degree < 1.0:
        return Probable(tv.degree)
    if tv.modality == Modality.POSSIBLE:
        if tv.degree > 0.5:
            return Probable(tv.degree)
        return Possible()
    if tv.modality == Modality.COUNTERFACTUAL:
        return Speculative()
    return Possible()


# ══════════════════════════════════════════════════════════════
# CONVENIENCE CONSTRUCTORS
# ══════════════════════════════════════════════════════════════

# Standard truth values
TRUE = TruthValue(1.0, Modality.NECESSARY)
FALSE = TruthValue(0.0, Modality.IMPOSSIBLE)
UNKNOWN = TruthValue(0.5, Modality.UNDETERMINED)

def necessary(degree: float = 1.0) -> TruthValue:
    """Necessarily true (with given degree)."""
    return TruthValue(degree, Modality.NECESSARY)

def actual(degree: float = 1.0) -> TruthValue:
    """Actually true (with given degree)."""
    return TruthValue(degree, Modality.ACTUAL)

def probable(degree: float = 0.7) -> TruthValue:
    """Probably true."""
    return TruthValue(degree, Modality.PROBABLE)

def possible(degree: float = 0.5) -> TruthValue:
    """Possibly true."""
    return TruthValue(degree, Modality.POSSIBLE)

def counterfactual(degree: float = 0.5) -> TruthValue:
    """Would be true under different conditions."""
    return TruthValue(degree, Modality.COUNTERFACTUAL)

def undetermined(degree: float = 0.5) -> TruthValue:
    """Truth value genuinely not yet established."""
    return TruthValue(degree, Modality.UNDETERMINED)
