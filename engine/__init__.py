"""
MORPHOS Categorical Engine

A working category theory computation engine for defining categories,
discovering functors (structural analogies), exploring compositions,
and speculating about missing structure.

Extended with quantitative morphisms, temporal ordering, scalable search,
universal data adapters, deep WordNet extraction, and curated multi-domain
knowledge datasets.
"""
from .epistemic import (
    EpistemicStatus,
    Definite,
    Probable,
    Possible,
    Speculative,
    Contradicted,
    compose_epistemic,
    parse_epistemic,
)
from .categories import Category, Morphism, create_category
from .functors import Functor, find_functors
from .scalable_search import (
    SignatureMatch,
    find_functors_scalable,
    find_best_analogy,
)
from .composition import (
    find_paths,
    detect_isomorphisms,
    find_commutative_squares,
    composition_report,
)
from .speculation import speculate_morphisms, speculation_report
from .adapters import (
    from_triples_csv,
    from_conceptnet_csv,
    from_conceptnet_neighborhood,
    from_json_triples,
    from_edge_list,
    from_dict,
    from_wordnet,
    describe_dataset,
)

__all__ = [
    # Core types
    "EpistemicStatus", "Definite", "Probable", "Possible", "Speculative",
    "Contradicted", "compose_epistemic", "parse_epistemic",
    "Category", "Morphism", "create_category",
    # Exact functor search (small categories)
    "Functor", "find_functors",
    # Scalable functor search (large categories)
    "SignatureMatch", "find_functors_scalable", "find_best_analogy",
    # Composition exploration
    "find_paths", "detect_isomorphisms", "find_commutative_squares",
    "composition_report",
    # Speculation
    "speculate_morphisms", "speculation_report",
    # Data adapters
    "from_triples_csv", "from_conceptnet_csv", "from_conceptnet_neighborhood",
    "from_json_triples", "from_edge_list", "from_dict", "from_wordnet",
    "describe_dataset",
]
