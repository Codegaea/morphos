# Mathematical Foundations

All implementations derive from these definitions. Don't change them without opening a discussion.

## Enriched Category

A MORPHOS category is enriched over **Q = ([0,1], ≤, min, 1)**.

- **Identity axiom:** `hom(A,A) = 1` for all A
- **Composition axiom:** `min(hom(A,B), hom(B,C)) ≤ hom(A,C)` for all A,B,C

By Lawvere (1973), a category enriched over this quantale is a generalized metric space:
`d(A,B) = −log(hom(A,B))`

The t-norm is configurable per computation: Gödel (min, default), product (×), or Łukasiewicz (max(0, p+q-1)).

## Heyting Algebra

Truth values form a Heyting algebra with meet (∧), join (∨), Gödel implication (→), and pseudo-complement (¬).

**Gödel implication:** `p → q = 1` if `p.degree ≤ q.degree`, else `= q.degree`

**Double-negation failure (intentional):** `¬¬p ≠ p` for UNDETERMINED values.
Classical logic assumes every proposition is true or false. MORPHOS does not.

## Graded Definitions

### Isomorphism
```
iso_degree(A,B) = sup_{f:A→B, g:B→A} min(μ(f), μ(g), [g∘f=id_A], [f∘g=id_B])
```
where `[·] ∈ {0,1}` tests identity morphism existence.

### Functor Properties
```
faithful_degree(F) = fraction of hom-sets on which F is injective
full_degree(F)     = fraction of hom-sets on which F is surjective
ess_surj_degree(F) = fraction of target objects with iso_degree(FC, D) > 0
equiv_degree(F)    = min(faithful, full, ess_surjective)
```

### Adjunction
```
adj_degree(F,G) = inf_{A,B} biresiduation(hom_D(FA,B), hom_C(A,GB))
biresiduation(p,q) = min(p→q, q→p)  [Gödel biconditional]
```

### Natural Isomorphism
```
nat_iso_degree(F,G) = inf_{A∈Ob(C)} iso_degree(F(A), G(A)) in D
```

## Filtered Nerve

Filtration convention: `filtration_value = 1 − truth_degree`

- **N(C)₀**: one 0-simplex per object, filtration value 0
- **N(C)₁**: one 1-simplex per non-identity morphism, filtration value `1 − truth_degree`
- **N(C)_k**: one k-simplex per composable k-tuple where the direct morphism also exists, filtration value `1 − min(truth degrees)`

## Homology over GF(2)

For chain complex `0 ← C₀ ←∂₁ C₁ ←∂₂ C₂ ← ...`:

**β_n = dim(C_n) − rank(∂_n) − rank(∂_{n+1})** computed over GF(2).

**Critical:** rank must use `_rank_gf2()` (Gaussian elimination mod 2), not `np.linalg.matrix_rank` (real rank). The answers differ. See `engine/topology.py`.

## Persistence Diagram

Diagram Dgm(C) = multiset of (birth, death) pairs in filtration space.
Convert to truth space: `birth_truth = 1 − birth`, `death_truth = 1 − death`.

**Stability theorem** (Cohen-Steiner, Edelsbrunner, Harer 2007):
`W∞(Dgm(C), Dgm(C')) ≤ ‖μ_C − μ_C'‖∞`

Small belief perturbations cause at most proportional changes to the diagram.

## Lawvere Metric

`d(A,B) = −log(hom(A,B))` with `d(A,B) = ∞` where no morphism exists.

This is a Lawvere metric — possibly asymmetric (directed knowledge). Symmetry degree measures `1 − avg|hom(A,B) − hom(B,A)|`.

## References

1. **Lawvere, F.W.** (1973). Metric spaces, generalized logic, and closed categories.
2. **Kelly, G.M.** (1982). Basic Concepts of Enriched Category Theory.
3. **Mac Lane, S.** (1998). Categories for the Working Mathematician (2nd ed.).
4. **Cohen-Steiner, Edelsbrunner, Harer** (2007). Stability of persistence diagrams.
5. **Goldblatt, R.** (1984). Topoi: The Categorial Analysis of Logic.
6. **Stubbe, I.** (2013). An introduction to quantaloid-enriched categories.
