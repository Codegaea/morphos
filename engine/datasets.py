"""
MORPHOS Curated Knowledge Datasets

Rich, multi-relational datasets built from verified encyclopedic knowledge.
Each dataset is designed to test a different aspect of analogical reasoning:

- Periodic Table: multiple independent classification systems on same objects
- Musical Theory: transposition as literal functor, interval arithmetic
- Color Theory: complementary/analogous relationships, mixing operations
- Biological Taxonomy: deep hierarchy with convergent evolution
- Mathematical Structures: the structures category theory was built for
- Process/Causal Chains: temporal sequences with enabling relationships

All data verified against standard references (CRC Handbook, Grove Music,
Munsell color system, ITIS taxonomy, standard algebra textbooks).
"""
from __future__ import annotations


def periodic_table() -> dict:
    """
    First 36 elements with multiple independent relationship types.

    Relationship types:
    - group_member: element belongs to a periodic group
    - period_member: element belongs to a period
    - class_member: metallic classification
    - electron_config: similar valence configuration
    - reactivity_order: more reactive than (within group)
    - forms_compound: known to form compounds with

    Source: IUPAC periodic table, CRC Handbook
    """
    return {
        "name": "PeriodicTable",
        "objects": [
            "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
            "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
            "K", "Ca", "Fe", "Cu", "Zn", "Br", "Kr",
            # Groups
            "alkali_metals", "alkaline_earth", "halogens", "noble_gases",
            "transition_metals", "nonmetals", "metalloids",
            # Periods
            "period_1", "period_2", "period_3", "period_4",
            # Classifications
            "metal", "nonmetal", "metalloid_class", "gas_state", "solid_state", "liquid_state",
        ],
        "morphisms": [
            # Group membership
            ("group_member", "H", "nonmetals"),
            ("group_member", "Li", "alkali_metals"),
            ("group_member", "Na", "alkali_metals"),
            ("group_member", "K", "alkali_metals"),
            ("group_member", "Be", "alkaline_earth"),
            ("group_member", "Mg", "alkaline_earth"),
            ("group_member", "Ca", "alkaline_earth"),
            ("group_member", "F", "halogens"),
            ("group_member", "Cl", "halogens"),
            ("group_member", "Br", "halogens"),
            ("group_member", "He", "noble_gases"),
            ("group_member", "Ne", "noble_gases"),
            ("group_member", "Ar", "noble_gases"),
            ("group_member", "Kr", "noble_gases"),
            ("group_member", "Fe", "transition_metals"),
            ("group_member", "Cu", "transition_metals"),
            ("group_member", "Zn", "transition_metals"),

            # Period membership
            ("period_member", "H", "period_1"),
            ("period_member", "He", "period_1"),
            ("period_member", "Li", "period_2"),
            ("period_member", "Be", "period_2"),
            ("period_member", "C", "period_2"),
            ("period_member", "N", "period_2"),
            ("period_member", "O", "period_2"),
            ("period_member", "F", "period_2"),
            ("period_member", "Ne", "period_2"),
            ("period_member", "Na", "period_3"),
            ("period_member", "Mg", "period_3"),
            ("period_member", "Al", "period_3"),
            ("period_member", "Si", "period_3"),
            ("period_member", "Cl", "period_3"),
            ("period_member", "Ar", "period_3"),
            ("period_member", "K", "period_4"),
            ("period_member", "Ca", "period_4"),
            ("period_member", "Fe", "period_4"),
            ("period_member", "Cu", "period_4"),
            ("period_member", "Br", "period_4"),
            ("period_member", "Kr", "period_4"),

            # Metallic classification
            ("class_member", "Li", "metal"), ("class_member", "Na", "metal"),
            ("class_member", "K", "metal"), ("class_member", "Fe", "metal"),
            ("class_member", "Cu", "metal"), ("class_member", "Ca", "metal"),
            ("class_member", "Mg", "metal"), ("class_member", "Al", "metal"),
            ("class_member", "H", "nonmetal"), ("class_member", "C", "nonmetal"),
            ("class_member", "N", "nonmetal"), ("class_member", "O", "nonmetal"),
            ("class_member", "F", "nonmetal"), ("class_member", "Cl", "nonmetal"),
            ("class_member", "Si", "metalloid_class"), ("class_member", "B", "metalloid_class"),

            # Reactivity within groups (alkali: K > Na > Li)
            ("more_reactive", "K", "Na"),
            ("more_reactive", "Na", "Li"),
            # Halogens: F > Cl > Br
            ("more_reactive", "F", "Cl"),
            ("more_reactive", "Cl", "Br"),

            # Key compounds
            ("forms_compound", "Na", "Cl"),  # NaCl
            ("forms_compound", "H", "O"),    # H2O
            ("forms_compound", "H", "Cl"),   # HCl
            ("forms_compound", "Ca", "O"),   # CaO
            ("forms_compound", "Fe", "O"),   # Fe2O3
            ("forms_compound", "C", "O"),    # CO2
            ("forms_compound", "N", "H"),    # NH3

            # State at room temperature
            ("state_at_RT", "H", "gas_state"), ("state_at_RT", "He", "gas_state"),
            ("state_at_RT", "N", "gas_state"), ("state_at_RT", "O", "gas_state"),
            ("state_at_RT", "F", "gas_state"), ("state_at_RT", "Cl", "gas_state"),
            ("state_at_RT", "Ne", "gas_state"), ("state_at_RT", "Ar", "gas_state"),
            ("state_at_RT", "Fe", "solid_state"), ("state_at_RT", "Cu", "solid_state"),
            ("state_at_RT", "Na", "solid_state"), ("state_at_RT", "C", "solid_state"),
            ("state_at_RT", "Br", "liquid_state"),
        ],
    }


def musical_theory() -> dict:
    """
    Musical intervals, scales, and chord structure.

    The analogy between major and minor keys is a real functor:
    every structural relationship in major has a mirror in minor
    with the third/sixth/seventh degrees flatted.

    Source: Grove Dictionary of Music, standard music theory
    """
    return {
        "name": "MusicTheory",
        "objects": [
            # Notes (chromatic)
            "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
            # Intervals
            "unison", "minor_2nd", "major_2nd", "minor_3rd", "major_3rd",
            "perfect_4th", "tritone", "perfect_5th",
            "minor_6th", "major_6th", "minor_7th", "major_7th", "octave",
            # Scale types
            "major_scale", "minor_scale", "pentatonic", "chromatic_scale",
            # Chord types
            "major_triad", "minor_triad", "diminished", "augmented",
            "dominant_7th", "major_7th_chord",
            # Functions
            "tonic", "subdominant", "dominant",
        ],
        "morphisms": [
            # Scale degrees → function
            ("has_function", "C", "tonic"),
            ("has_function", "F", "subdominant"),
            ("has_function", "G", "dominant"),

            # Chord construction: root + interval = chord tone
            ("root_of", "C", "major_triad"),
            ("root_of", "A", "minor_triad"),
            ("root_of", "G", "dominant_7th"),

            # Interval relationships
            ("inverts_to", "major_3rd", "minor_6th"),
            ("inverts_to", "minor_3rd", "major_6th"),
            ("inverts_to", "perfect_4th", "perfect_5th"),
            ("inverts_to", "major_2nd", "minor_7th"),
            ("inverts_to", "minor_2nd", "major_7th"),
            ("inverts_to", "tritone", "tritone"),

            # Interval quality relationships
            ("enlarges_to", "minor_2nd", "major_2nd"),
            ("enlarges_to", "minor_3rd", "major_3rd"),
            ("enlarges_to", "minor_6th", "major_6th"),
            ("enlarges_to", "minor_7th", "major_7th"),

            # Scale membership
            ("degree_of", "C", "major_scale"), ("degree_of", "D", "major_scale"),
            ("degree_of", "E", "major_scale"), ("degree_of", "F", "major_scale"),
            ("degree_of", "G", "major_scale"), ("degree_of", "A", "major_scale"),
            ("degree_of", "B", "major_scale"),
            ("degree_of", "C", "minor_scale"), ("degree_of", "D", "minor_scale"),
            ("degree_of", "Eb", "minor_scale"), ("degree_of", "F", "minor_scale"),
            ("degree_of", "G", "minor_scale"), ("degree_of", "Ab", "minor_scale"),
            ("degree_of", "Bb", "minor_scale"),

            # Chord-scale relationship
            ("chord_of", "major_triad", "major_scale"),
            ("chord_of", "minor_triad", "minor_scale"),
            ("chord_of", "dominant_7th", "major_scale"),

            # Chord quality
            ("quality", "major_triad", "major_3rd"),
            ("quality", "minor_triad", "minor_3rd"),
            ("quality", "diminished", "minor_3rd"),
            ("quality", "augmented", "major_3rd"),

            # Circle of fifths (partial)
            ("fifth_of", "C", "G"), ("fifth_of", "G", "D"),
            ("fifth_of", "D", "A"), ("fifth_of", "A", "E"),
            ("fifth_of", "F", "C"), ("fifth_of", "Bb", "F"),

            # Harmonic resolution
            ("resolves_to", "dominant", "tonic"),
            ("resolves_to", "subdominant", "dominant"),
        ],
    }


def color_theory() -> dict:
    """
    Color relationships: complementary, analogous, triadic,
    warm/cool classification, and mixing operations.

    Source: Munsell color system, standard color theory
    """
    return {
        "name": "ColorTheory",
        "objects": [
            # Primary (RYB traditional)
            "red", "yellow", "blue",
            # Secondary
            "orange", "green", "purple",
            # Tertiary
            "red_orange", "yellow_orange", "yellow_green",
            "blue_green", "blue_purple", "red_purple",
            # Properties
            "warm", "cool", "neutral",
            # Mixing results
            "white", "black", "gray",
        ],
        "morphisms": [
            # Complementary pairs (opposite on wheel)
            ("complement", "red", "green"),
            ("complement", "green", "red"),
            ("complement", "blue", "orange"),
            ("complement", "orange", "blue"),
            ("complement", "yellow", "purple"),
            ("complement", "purple", "yellow"),

            # Analogous (adjacent on wheel)
            ("analogous", "red", "red_orange"),
            ("analogous", "red", "red_purple"),
            ("analogous", "yellow", "yellow_orange"),
            ("analogous", "yellow", "yellow_green"),
            ("analogous", "blue", "blue_green"),
            ("analogous", "blue", "blue_purple"),

            # Mixing (primary + primary = secondary)
            ("mixes_to", "red", "orange"),    # red + yellow
            ("mixes_to", "yellow", "orange"),
            ("mixes_to", "yellow", "green"),  # yellow + blue
            ("mixes_to", "blue", "green"),
            ("mixes_to", "red", "purple"),    # red + blue
            ("mixes_to", "blue", "purple"),

            # Temperature
            ("has_temp", "red", "warm"),
            ("has_temp", "orange", "warm"),
            ("has_temp", "yellow", "warm"),
            ("has_temp", "blue", "cool"),
            ("has_temp", "green", "cool"),
            ("has_temp", "purple", "cool"),

            # Value relationships
            ("lightens_to", "red", "white"),   # tint
            ("darkens_to", "red", "black"),    # shade
            ("mutes_to", "red", "gray"),       # tone

            ("lightens_to", "blue", "white"),
            ("darkens_to", "blue", "black"),
            ("mutes_to", "blue", "gray"),
        ],
    }


def biological_taxonomy() -> dict:
    """
    Taxonomic classification with convergent evolution examples.

    The key test: bats and birds both fly, but bats are mammals
    and birds are not. Can the engine distinguish taxonomic
    similarity (bat ≈ whale) from functional similarity (bat ≈ bird)?

    Source: ITIS (Integrated Taxonomic Information System)
    """
    return {
        "name": "BiologicalTaxonomy",
        "objects": [
            # Species
            "dog", "wolf", "cat", "lion", "bat", "whale",
            "eagle", "penguin", "sparrow",
            "salmon", "shark",
            "frog", "snake",
            "ant", "butterfly",
            # Higher taxa
            "mammal", "bird", "fish", "reptile", "amphibian", "insect",
            "vertebrate", "invertebrate", "animal",
            "carnivore", "herbivore", "omnivore",
            # Functional traits
            "flies", "swims", "walks", "warm_blooded", "cold_blooded",
            "has_fur", "has_feathers", "has_scales",
            "live_birth", "lays_eggs",
        ],
        "morphisms": [
            # Taxonomic hierarchy
            ("is_a", "dog", "mammal"), ("is_a", "wolf", "mammal"),
            ("is_a", "cat", "mammal"), ("is_a", "lion", "mammal"),
            ("is_a", "bat", "mammal"), ("is_a", "whale", "mammal"),
            ("is_a", "eagle", "bird"), ("is_a", "penguin", "bird"),
            ("is_a", "sparrow", "bird"),
            ("is_a", "salmon", "fish"), ("is_a", "shark", "fish"),
            ("is_a", "frog", "amphibian"), ("is_a", "snake", "reptile"),
            ("is_a", "ant", "insect"), ("is_a", "butterfly", "insect"),
            ("is_a", "mammal", "vertebrate"), ("is_a", "bird", "vertebrate"),
            ("is_a", "fish", "vertebrate"), ("is_a", "reptile", "vertebrate"),
            ("is_a", "amphibian", "vertebrate"),
            ("is_a", "insect", "invertebrate"),
            ("is_a", "vertebrate", "animal"),
            ("is_a", "invertebrate", "animal"),

            # Diet
            ("diet", "dog", "omnivore"), ("diet", "wolf", "carnivore"),
            ("diet", "cat", "carnivore"), ("diet", "lion", "carnivore"),
            ("diet", "eagle", "carnivore"), ("diet", "shark", "carnivore"),
            ("diet", "sparrow", "omnivore"), ("diet", "frog", "carnivore"),

            # Locomotion (convergent evolution!)
            ("capable_of", "bat", "flies"),      # mammal that flies
            ("capable_of", "eagle", "flies"),     # bird that flies
            ("capable_of", "sparrow", "flies"),
            ("capable_of", "butterfly", "flies"), # insect that flies
            ("capable_of", "whale", "swims"),     # mammal that swims
            ("capable_of", "penguin", "swims"),   # bird that swims
            ("capable_of", "salmon", "swims"),
            ("capable_of", "shark", "swims"),
            ("capable_of", "dog", "walks"), ("capable_of", "cat", "walks"),
            ("capable_of", "lion", "walks"), ("capable_of", "wolf", "walks"),

            # Body covering
            ("has_covering", "dog", "has_fur"), ("has_covering", "cat", "has_fur"),
            ("has_covering", "bat", "has_fur"), ("has_covering", "whale", "has_fur"),
            ("has_covering", "eagle", "has_feathers"), ("has_covering", "penguin", "has_feathers"),
            ("has_covering", "shark", "has_scales"), ("has_covering", "snake", "has_scales"),

            # Thermoregulation
            ("thermo", "mammal", "warm_blooded"),
            ("thermo", "bird", "warm_blooded"),
            ("thermo", "reptile", "cold_blooded"),
            ("thermo", "fish", "cold_blooded"),
            ("thermo", "amphibian", "cold_blooded"),

            # Reproduction
            ("reproduction", "mammal", "live_birth"),
            ("reproduction", "bird", "lays_eggs"),
            ("reproduction", "reptile", "lays_eggs"),
            ("reproduction", "fish", "lays_eggs"),
            ("reproduction", "insect", "lays_eggs"),
        ],
    }


def process_chains() -> dict:
    """
    Sequential processes from different domains.
    Tests whether the engine can discover that processes
    with the same step structure are analogous even when
    the domains are completely different.

    Source: standard textbook descriptions of each process
    """
    return {
        "name": "ProcessChains",
        "objects": [
            # Photosynthesis steps
            "light_absorption", "water_splitting", "electron_transport_ps",
            "NADPH_production", "carbon_fixation", "glucose_output",
            # Software development
            "requirements", "design", "implementation",
            "testing", "deployment", "maintenance",
            # Scientific method
            "observation", "hypothesis", "experiment",
            "analysis", "conclusion_sci", "publication",
            # Cooking a meal
            "recipe_selection", "ingredient_prep", "cooking_process",
            "taste_testing", "plating", "serving",
            # Learning cycle
            "encounter", "struggle", "insight",
            "practice", "mastery", "teaching_others",
        ],
        "morphisms": [
            # Photosynthesis sequence
            ("enables", "light_absorption", "water_splitting"),
            ("enables", "water_splitting", "electron_transport_ps"),
            ("enables", "electron_transport_ps", "NADPH_production"),
            ("enables", "NADPH_production", "carbon_fixation"),
            ("enables", "carbon_fixation", "glucose_output"),
            ("feedback", "glucose_output", "light_absorption"),

            # Software development sequence
            ("enables", "requirements", "design"),
            ("enables", "design", "implementation"),
            ("enables", "implementation", "testing"),
            ("enables", "testing", "deployment"),
            ("enables", "deployment", "maintenance"),
            ("feedback", "maintenance", "requirements"),

            # Scientific method sequence
            ("enables", "observation", "hypothesis"),
            ("enables", "hypothesis", "experiment"),
            ("enables", "experiment", "analysis"),
            ("enables", "analysis", "conclusion_sci"),
            ("enables", "conclusion_sci", "publication"),
            ("feedback", "publication", "observation"),

            # Cooking sequence
            ("enables", "recipe_selection", "ingredient_prep"),
            ("enables", "ingredient_prep", "cooking_process"),
            ("enables", "cooking_process", "taste_testing"),
            ("enables", "taste_testing", "plating"),
            ("enables", "plating", "serving"),
            ("feedback", "serving", "recipe_selection"),

            # Learning cycle
            ("enables", "encounter", "struggle"),
            ("enables", "struggle", "insight"),
            ("enables", "insight", "practice"),
            ("enables", "practice", "mastery"),
            ("enables", "mastery", "teaching_others"),
            ("feedback", "teaching_others", "encounter"),
        ],
    }


def mathematical_structures() -> dict:
    """
    Mathematical objects and their relationships.
    This is what category theory was literally designed to describe.

    Source: standard algebra textbooks (Hungerford, Lang)
    """
    return {
        "name": "MathStructures",
        "objects": [
            # Number systems
            "naturals", "integers", "rationals", "reals", "complex",
            # Algebraic structures
            "monoid", "group", "abelian_group", "ring", "field",
            "vector_space", "algebra",
            # Properties
            "closure", "associativity", "identity_element",
            "inverse_element", "commutativity",
            "distributivity",
            # Operations
            "addition", "multiplication", "composition_op",
            # Specific groups
            "Z_mod_n", "symmetric_group", "dihedral_group",
            "GL_n", "cyclic_group",
        ],
        "morphisms": [
            # Number system inclusions (embeddings)
            ("embeds_in", "naturals", "integers"),
            ("embeds_in", "integers", "rationals"),
            ("embeds_in", "rationals", "reals"),
            ("embeds_in", "reals", "complex"),

            # Structure hierarchy
            ("is_a", "group", "monoid"),
            ("is_a", "abelian_group", "group"),
            ("is_a", "ring", "abelian_group"),
            ("is_a", "field", "ring"),
            ("is_a", "vector_space", "abelian_group"),
            ("is_a", "algebra", "vector_space"),
            ("is_a", "algebra", "ring"),

            # Number systems as algebraic structures
            ("instance_of", "naturals", "monoid"),
            ("instance_of", "integers", "ring"),
            ("instance_of", "rationals", "field"),
            ("instance_of", "reals", "field"),
            ("instance_of", "complex", "field"),

            # Required axioms
            ("requires", "monoid", "closure"),
            ("requires", "monoid", "associativity"),
            ("requires", "monoid", "identity_element"),
            ("requires", "group", "inverse_element"),
            ("requires", "abelian_group", "commutativity"),
            ("requires", "ring", "distributivity"),

            # Operations
            ("has_operation", "group", "composition_op"),
            ("has_operation", "ring", "addition"),
            ("has_operation", "ring", "multiplication"),
            ("has_operation", "field", "addition"),
            ("has_operation", "field", "multiplication"),

            # Specific instances
            ("instance_of", "Z_mod_n", "group"),
            ("instance_of", "symmetric_group", "group"),
            ("instance_of", "dihedral_group", "group"),
            ("instance_of", "GL_n", "group"),
            ("instance_of", "cyclic_group", "abelian_group"),
        ],
    }


ALL_DATASETS = {
    "periodic_table": periodic_table,
    "musical_theory": musical_theory,
    "color_theory": color_theory,
    "biological_taxonomy": biological_taxonomy,
    "process_chains": process_chains,
    "mathematical_structures": mathematical_structures,
}


def load_all():
    """Load all datasets and return as dict of category-ready data."""
    return {name: fn() for name, fn in ALL_DATASETS.items()}


def stats():
    """Print statistics for all curated datasets."""
    total_objects = 0
    total_morphisms = 0
    for name, fn in ALL_DATASETS.items():
        data = fn()
        n_obj = len(data["objects"])
        n_morph = len(data["morphisms"])
        total_objects += n_obj
        total_morphisms += n_morph

        # Count relationship types
        rel_types = set(m[0] for m in data["morphisms"])
        print(f"  {name:25s}: {n_obj:3d} objects, {n_morph:3d} morphisms, {len(rel_types):2d} rel types")

    print(f"  {'TOTAL':25s}: {total_objects:3d} objects, {total_morphisms:3d} morphisms")
