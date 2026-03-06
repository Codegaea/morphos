# Intellectual Ancestry

MORPHOS sits at the intersection of cognitive science, category theory, and topological data analysis. This document traces the lineage precisely — not as a literature review, but to show which ideas are inherited, which are extensions, and which are genuinely new.

Understanding the ancestry also answers a question that comes up quickly when reading the codebase: *why functors?* The answer is not "because category theory is fashionable." It's because functors are the mathematically exact formulation of an idea that was already correct in the 1980s but lacked the right language.

---

## 1. Gentner's Structure-Mapping Theory (1983)

The foundational idea comes from cognitive scientist Dedre Gentner.

In *Structure-Mapping: A Theoretical Framework for Analogy* (1983), Gentner proposed that analogical reasoning is not about surface similarity between objects — it is about the preservation of relational structure between domains.

**The canonical example:**

> The solar system is like an atom. The sun is like the nucleus. Planets are like electrons.

This analogy works not because suns and nuclei look alike, but because the *relations* are structurally parallel:

```
solar system:   sun  ---attracts-->  planet  ---orbits-->  sun
atom:        nucleus ---attracts--> electron ---orbits--> nucleus
```

The mapping is:

```
sun       →  nucleus
planet    →  electron
gravity   →  electrostatic force
```

**The systematicity principle:** Gentner's key empirical finding was that humans prefer analogies that preserve *interconnected systems of relations* over those that match isolated properties. A deeper, more compositionally coherent mapping scores higher than a shallow one. This is the principle that MORPHOS formalizes as functor composition-preservation.

**What the theory lacked:** Gentner's framework was a cognitive science theory, not a mathematical one. It was precise about *what* a good analogy is, but not about *how to compute* one, nor what formal structure made an analogy correct.

---

## 2. The Structure-Mapping Engine (SME, 1986–present)

Kenneth Forbus (Northwestern) implemented Gentner's theory as a computational algorithm: the **Structure-Mapping Engine**.

**How SME works:**

1. Takes two structured relational descriptions — a base domain and a target domain
2. Generates *match hypotheses*: candidate pairings between predicates
3. Enforces *structural consistency*: if `sun↔nucleus`, then all relations involving sun must map consistently to relations involving nucleus
4. Assembles the highest-scoring globally consistent mapping
5. Scores by systematicity — depth of relational structure preserved

**On the solar system / atom example**, SME produces:

```
sun → nucleus,  planet → electron,  gravity → electrostatic_force
```

Without being told the answer.

**Where SME succeeded:** It became one of the most influential computational models in cognitive science. It showed that structure-preservation, implemented as a constraint-satisfaction problem, could reproduce human analogy judgments at scale. It was used in educational tutoring systems, scientific analogy discovery, and cross-domain reasoning research.

**Where SME hit its limits:**

- *Scale*: SME was designed for hand-constructed domains of 10–50 entities. It has no indexing, no prefiltering, and no fallback for large categories.
- *Static*: SME runs once and returns a mapping. There is no persistence, no program store, no accumulation over time.
- *Binary truth*: Relations either hold or they don't. There is no principled way to handle uncertain knowledge, partially correct analogies, or confidence-weighted domains.
- *No global structure*: SME never analyzes the topological shape of domains — it only compares pairs.

---

## 3. Why Functors Are the Right Mathematics

Here is the connection that makes MORPHOS more than an engineering extension of SME.

**Ask the formal question:** What is "a mapping between relational structures that takes relations to relations consistently and preserves their composition"?

That is the definition of a **functor**.

A functor F: C → D assigns objects to objects and morphisms to morphisms such that:
- **Composition preservation:** F(g∘f) = F(g)∘F(f)
- **Identity preservation:** F(id_A) = id_{F(A)}

Gentner's systematicity principle — a mapping that respects how relations chain together is a stronger analogy — is exactly the composition-preservation law. A functor that maps `A→B` and `B→C` in the source domain must map `A→C` in the target domain via the same composite path. SME's structural consistency check is a greedy approximation of this. MORPHOS enforces it exactly.

This means:

> SME was always approximating functor search. It just didn't have the language for it.

MORPHOS replaces the approximation with the exact criterion. The theoretical guarantee — "this mapping is a functor" — is stronger than "this mapping scored highest by SME's heuristic." It is checkable, falsifiable, and composable.

---

## 4. The Yoneda Lemma as a Theory of Conceptual Meaning

There is a second mathematical connection that goes further than the functor observation.

The **Yoneda lemma** states: an object A in a category is completely characterized by how other objects map into it. Formally, the functor y: C → [C^op, Set] defined by y(A)(X) = Hom(X, A) is fully faithful — no information about A is lost.

This is a formal statement of the cognitive science finding that conceptual meaning is relational, not intrinsic. "Electron" doesn't have independent meaning — it means what it does through its relations to nucleus, orbital, charge, and the rest of the domain. Change the relational structure and you've changed the concept.

In MORPHOS, the Yoneda matrix Y[i,j] = hom(obj_i, obj_j) is the relational fingerprint of each object. Objects with identical Yoneda profiles are isomorphic — structurally interchangeable. Analogy at the object level is finding pairs across domains with similar Yoneda profiles. The Yoneda engine (`GET /api/topology/{domain}/yoneda`) computes this directly.

The Yoneda lemma also explains why the WL fingerprint prefilter works: Weisfeiler-Lehman hashing approximates the Yoneda profile with a compact hash. If two objects have incompatible WL hashes, their Yoneda profiles differ structurally, and no functor can map one to the other. This turns an exponential search into a polynomial screen.

---

## 5. The Enrichment: What SME Never Had

Classical SME operates over truth-valued relations. A relation holds or it doesn't. There is no principled treatment of uncertainty.

Enriching categories over **Q = ([0,1], ≤, min, 1)** gives this for free. A Q-enriched functor F: C → D satisfies:

```
min(hom_C(A,B), hom_C(B,C))  ≤  hom_D(F(A), F(C))
```

This is the enriched composition axiom. It says: a functor cannot strengthen inference across the mapping. If A→B is probable and B→C is probable in the source domain, then F(A)→F(C) in the target domain is at least as probable — but no more certain than the source chain warrants.

This formalizes something Gentner observed empirically: **analogical inference is conservative.** You use analogy to generate hypotheses, not to prove them. The enriched functor condition enforces this as a mathematical invariant, not a methodological guideline.

The Gödel implication in the truth layer (p → q = 1 if p ≤ q, else q) is the direct algebraic expression of this conservatism: you cannot derive more certainty from an implication than the conclusion already has.

---

## 6. Persistent Homology as Topological Systematicity

Gentner's systematicity principle scores analogies by depth of relational interconnection. But it operates pairwise — it compares two domains at a time, using the analogy mapping as the comparison lens.

Persistent homology allows a complementary measurement: the *global* topological structure of a domain, independently of any analogy. The filtered nerve N_τ(C) captures which relational cycles exist at each confidence threshold τ. The persistence diagram is the fingerprint of those cycles — which ones are robust (persist across a wide range of τ) and which are fragile.

The connection to SME is: **persistent homology is a pre-screening for analogical compatibility.** Two domains with similar persistence diagrams (small bottleneck distance) are candidates for strong analogies; domains with very different diagrams are unlikely to support deep functor mappings. This is why the solar system and atom examples produce identical diagrams — they have the same cycle structure, which is what makes the analogy work.

This idea does not exist in SME or any of its successors. It is the genuinely new contribution of the MORPHOS research program.

---

## 7. The Lineage

```
Gentner (1983)
"Analogy = relational structure preservation"
"Systematicity = depth of compositional alignment"
             │
             ▼
SME — Forbus & Gentner (1986)
Correct insight, greedy algorithm, small-scale, binary truth
             │
             ├─── cognitive science analogy research (LISA, ACME, FAR...)
             │    Analogy as cognitive mechanism — studied but not built
             │
             ▼
Category theory — Lawvere (1973), Kelly (1982), Mac Lane (1998)
Functor = composition-preserving map (SME made exact)
Enrichment over [0,1] = principled uncertainty
Yoneda = relational characterization of meaning
             │
             ▼
TDA — Cohen-Steiner, Edelsbrunner, Harer (2007)
Persistence stability: small belief changes → small diagram changes
             │
             ▼
MORPHOS (2026)
SME's insight + categorical formalization + persistence + topology + runtime
```

---

## 8. The Four Divergences from SME

| Property | SME | MORPHOS |
|---|---|---|
| Analogy algorithm | Greedy structural heuristic | Exact functor search (AC-3 + WL prefilter) |
| Knowledge model | Binary-valued relations | Q-enriched morphisms with truth degrees |
| Persistence | None — runs once | Full runtime with program store and derivation log |
| Global structure | Not analyzed | Persistent homology of the categorical nerve |

The first three divergences are engineering extensions — important but in principle achievable within SME's framework. The fourth is a conceptual departure. SME has no notion of the *shape* of a knowledge domain. MORPHOS proposes that this shape is measurable, stable, and informative — and that topology is the right tool for measuring it.

---

## 9. The Three Systems That Tried the Same Problem Differently

**Cyc (1984):** Tried to encode common-sense knowledge as first-order logic facts. Hit combinatorial inference explosion. The mistake was treating reasoning as logical derivation rather than structural mapping.

**Wolfram (symbolic engine):** Built universal symbolic computation via rewrite rules. Excellent at deterministic transformation, weak at structural analogy across domains. Symbolic rewrite systems don't discover relational mappings; they transform expressions.

**OpenCog:** Tried to build a general AI framework by mixing probabilistic logic, pattern matching, and evolutionary algorithms in an AtomSpace graph. The problem: no single organizing abstraction. Without a unifying mathematical principle, reasoning became unpredictable at scale.

**What each was missing:**
- Cyc was missing: the idea that reasoning is structure-finding, not rule-following
- Wolfram was missing: relational structure as a first-class object
- OpenCog was missing: a unifying mathematical language

MORPHOS inherits the problem statement from SME and the mathematics from category theory. Whether those two things are sufficient to avoid the scaling limits that stopped the earlier systems is the central open question.

---

## 10. What Remains to Be Proved

The intellectual case for the MORPHOS approach is strong. The practical case depends on answers to questions the project has not yet resolved:

1. **Does functor search scale to real knowledge sizes?** SME's practical limit was ~50 objects. MORPHOS extends this to ~150 with WL prefiltering. Real knowledge domains have thousands. The gap is not closed.

2. **Is persistent homology *useful* for knowledge, or just computable?** The stability theorem holds. The bottleneck distance between the solar system and atom is 0.0. But demonstrating that topology provides actionable insight — not just interesting numbers — requires domain experiments that haven't been run yet.

3. **Does the Heyting algebra truth model correspond to anything real?** The model is internally consistent. Whether it captures how uncertainty actually propagates in knowledge domains — whether the Gödel implication is the right choice over Łukasiewicz or product for real applications — is an empirical question.

These are open problems, not objections. They are the reason this is a research project and not a product.

---

## References

- Gentner, D. (1983). Structure-mapping: A theoretical framework for analogy. *Cognitive Science*, 7(2), 155–170.
- Forbus, K.D., Gentner, D., & Law, K. (1994). MAC/FAC: A model of similarity-based retrieval. *Cognitive Science*, 19(2), 141–205.
- Lawvere, F.W. (1973). Metric spaces, generalized logic, and closed categories.
- Kelly, G.M. (1982). *Basic Concepts of Enriched Category Theory*.
- Cohen-Steiner, D., Edelsbrunner, H., & Harer, J. (2007). Stability of persistence diagrams. *Discrete & Computational Geometry*, 37(1), 103–120.
- Falkenhainer, B., Forbus, K.D., & Gentner, D. (1989). The structure-mapping engine: Algorithm and examples. *Artificial Intelligence*, 41(1), 1–63.
