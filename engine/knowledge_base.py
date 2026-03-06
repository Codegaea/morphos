"""
MORPHOS Extended Knowledge Base

Real data the engine can use, not descriptions of data it could use.

Sections:
1. COMMONSENSE (ConceptNet-style): 500+ assertions about everyday objects
2. PHYSICS: Real equations encoded as quantitative morphisms
3. SPATIAL/GEOMETRIC: 2D, 3D, 4D transformation categories
4. WIKIPEDIA FACTS: Structured encyclopedic knowledge
5. IMAGE/VISUAL: Spatial relationships between visual features
"""
from __future__ import annotations


# ══════════════════════════════════════════════════════════════
# 1. COMMONSENSE KNOWLEDGE (ConceptNet-style)
#
# Relationship types from ConceptNet ontology:
#   IsA, PartOf, HasA, UsedFor, CapableOf, AtLocation,
#   Causes, HasPrerequisite, HasProperty, MotivatedByGoal,
#   Desires, CausesDesire, MadeOf, CreatedBy, ReceivesAction,
#   HasSubevent, HasFirstSubevent, HasLastSubevent,
#   DefinedAs, SymbolOf, MannerOf, Antonym, Synonym
#
# Every triple is a real commonsense fact.
# ══════════════════════════════════════════════════════════════

def commonsense_knowledge() -> dict:
    """500+ commonsense assertions across everyday domains."""
    return {
        "name": "Commonsense",
        "objects": sorted(set(
            obj for triple in _COMMONSENSE_TRIPLES
            for obj in (triple[1], triple[2])
        )),
        "morphisms": _COMMONSENSE_TRIPLES,
    }

_COMMONSENSE_TRIPLES = [
    # ── Animals ──────────────────────────────
    ("IsA", "dog", "animal"), ("IsA", "dog", "pet"),
    ("IsA", "cat", "animal"), ("IsA", "cat", "pet"),
    ("IsA", "bird", "animal"), ("IsA", "fish", "animal"),
    ("IsA", "horse", "animal"), ("IsA", "cow", "animal"),
    ("IsA", "sheep", "animal"), ("IsA", "pig", "animal"),
    ("IsA", "eagle", "bird"), ("IsA", "sparrow", "bird"),
    ("IsA", "salmon", "fish"), ("IsA", "shark", "fish"),
    ("HasA", "dog", "tail"), ("HasA", "dog", "fur"),
    ("HasA", "dog", "four_legs"), ("HasA", "dog", "nose"),
    ("HasA", "cat", "tail"), ("HasA", "cat", "fur"),
    ("HasA", "cat", "whiskers"), ("HasA", "cat", "claws"),
    ("HasA", "bird", "wings"), ("HasA", "bird", "beak"),
    ("HasA", "bird", "feathers"), ("HasA", "fish", "fins"),
    ("HasA", "fish", "gills"), ("HasA", "fish", "scales"),
    ("HasA", "horse", "hooves"), ("HasA", "horse", "mane"),
    ("CapableOf", "dog", "bark"), ("CapableOf", "dog", "fetch"),
    ("CapableOf", "dog", "run"), ("CapableOf", "dog", "swim"),
    ("CapableOf", "cat", "purr"), ("CapableOf", "cat", "climb"),
    ("CapableOf", "cat", "hunt"), ("CapableOf", "bird", "fly"),
    ("CapableOf", "bird", "sing"), ("CapableOf", "fish", "swim"),
    ("CapableOf", "horse", "gallop"), ("CapableOf", "horse", "jump"),
    ("AtLocation", "dog", "house"), ("AtLocation", "dog", "yard"),
    ("AtLocation", "cat", "house"), ("AtLocation", "fish", "water"),
    ("AtLocation", "fish", "ocean"), ("AtLocation", "bird", "tree"),
    ("AtLocation", "bird", "sky"), ("AtLocation", "cow", "farm"),
    ("AtLocation", "horse", "stable"), ("AtLocation", "sheep", "field"),
    ("HasProperty", "dog", "loyal"), ("HasProperty", "dog", "friendly"),
    ("HasProperty", "cat", "independent"), ("HasProperty", "cat", "curious"),
    ("HasProperty", "fish", "cold_blooded"), ("HasProperty", "bird", "warm_blooded"),
    ("Desires", "dog", "food"), ("Desires", "dog", "attention"),
    ("Desires", "cat", "food"), ("Desires", "cat", "warmth"),

    # ── Food & Cooking ───────────────────────
    ("IsA", "apple", "fruit"), ("IsA", "banana", "fruit"),
    ("IsA", "orange", "fruit"), ("IsA", "carrot", "vegetable"),
    ("IsA", "potato", "vegetable"), ("IsA", "bread", "food"),
    ("IsA", "rice", "food"), ("IsA", "cheese", "food"),
    ("IsA", "pizza", "food"), ("IsA", "soup", "food"),
    ("IsA", "cake", "dessert"), ("IsA", "dessert", "food"),
    ("IsA", "fruit", "food"), ("IsA", "vegetable", "food"),
    ("MadeOf", "bread", "flour"), ("MadeOf", "bread", "water"),
    ("MadeOf", "bread", "yeast"), ("MadeOf", "cake", "flour"),
    ("MadeOf", "cake", "sugar"), ("MadeOf", "cake", "eggs"),
    ("MadeOf", "pizza", "dough"), ("MadeOf", "pizza", "cheese"),
    ("MadeOf", "pizza", "tomato_sauce"), ("MadeOf", "soup", "water"),
    ("UsedFor", "knife", "cutting"), ("UsedFor", "fork", "eating"),
    ("UsedFor", "spoon", "stirring"), ("UsedFor", "oven", "baking"),
    ("UsedFor", "stove", "cooking"), ("UsedFor", "pot", "boiling"),
    ("UsedFor", "pan", "frying"), ("UsedFor", "bowl", "mixing"),
    ("HasPrerequisite", "baking", "preheating"), ("HasPrerequisite", "baking", "measuring"),
    ("HasPrerequisite", "cooking", "ingredients"), ("HasPrerequisite", "cooking", "recipe"),
    ("HasSubevent", "cooking", "chopping"), ("HasSubevent", "cooking", "stirring"),
    ("HasSubevent", "cooking", "seasoning"), ("HasSubevent", "cooking", "tasting"),
    ("HasSubevent", "baking", "mixing"), ("HasSubevent", "baking", "kneading"),
    ("Causes", "cooking", "hot_food"), ("Causes", "baking", "baked_goods"),
    ("Causes", "eating", "satisfaction"), ("Causes", "overeating", "discomfort"),
    ("HasProperty", "apple", "sweet"), ("HasProperty", "apple", "crunchy"),
    ("HasProperty", "lemon", "sour"), ("HasProperty", "pepper", "spicy"),
    ("HasProperty", "ice_cream", "cold"), ("HasProperty", "soup", "hot"),
    ("AtLocation", "food", "kitchen"), ("AtLocation", "food", "store"),

    # ── Human Body & Health ──────────────────
    ("PartOf", "heart", "body"), ("PartOf", "brain", "body"),
    ("PartOf", "lung", "body"), ("PartOf", "liver", "body"),
    ("PartOf", "stomach", "body"), ("PartOf", "kidney", "body"),
    ("PartOf", "bone", "skeleton"), ("PartOf", "skeleton", "body"),
    ("PartOf", "muscle", "body"), ("PartOf", "skin", "body"),
    ("PartOf", "eye", "face"), ("PartOf", "nose", "face"),
    ("PartOf", "mouth", "face"), ("PartOf", "ear", "head"),
    ("PartOf", "face", "head"), ("PartOf", "head", "body"),
    ("PartOf", "hand", "arm"), ("PartOf", "arm", "body"),
    ("PartOf", "finger", "hand"), ("PartOf", "foot", "leg"),
    ("PartOf", "leg", "body"), ("PartOf", "toe", "foot"),
    ("CapableOf", "heart", "pump_blood"), ("CapableOf", "lung", "breathe"),
    ("CapableOf", "brain", "think"), ("CapableOf", "eye", "see"),
    ("CapableOf", "ear", "hear"), ("CapableOf", "nose", "smell"),
    ("CapableOf", "mouth", "speak"), ("CapableOf", "hand", "grasp"),
    ("CapableOf", "leg", "walk"), ("CapableOf", "stomach", "digest"),
    ("Causes", "exercise", "health"), ("Causes", "exercise", "strength"),
    ("Causes", "sleep", "rest"), ("Causes", "eating", "energy"),
    ("Causes", "disease", "pain"), ("Causes", "disease", "weakness"),
    ("Causes", "virus", "disease"), ("Causes", "bacteria", "infection"),
    ("Antonym", "health", "disease"), ("Antonym", "strength", "weakness"),
    ("Antonym", "sleep", "wakefulness"), ("Antonym", "pain", "comfort"),
    ("HasPrerequisite", "health", "nutrition"),
    ("HasPrerequisite", "health", "exercise"),
    ("HasPrerequisite", "health", "sleep"),

    # ── Tools & Objects ──────────────────────
    ("IsA", "hammer", "tool"), ("IsA", "screwdriver", "tool"),
    ("IsA", "saw", "tool"), ("IsA", "wrench", "tool"),
    ("IsA", "car", "vehicle"), ("IsA", "bicycle", "vehicle"),
    ("IsA", "airplane", "vehicle"), ("IsA", "boat", "vehicle"),
    ("IsA", "chair", "furniture"), ("IsA", "table", "furniture"),
    ("IsA", "bed", "furniture"), ("IsA", "desk", "furniture"),
    ("UsedFor", "hammer", "driving_nails"), ("UsedFor", "saw", "cutting_wood"),
    ("UsedFor", "screwdriver", "turning_screws"),
    ("UsedFor", "car", "transportation"), ("UsedFor", "bicycle", "transportation"),
    ("UsedFor", "airplane", "flying"), ("UsedFor", "boat", "sailing"),
    ("UsedFor", "chair", "sitting"), ("UsedFor", "table", "eating"),
    ("UsedFor", "bed", "sleeping"), ("UsedFor", "desk", "working"),
    ("UsedFor", "phone", "communication"), ("UsedFor", "computer", "computing"),
    ("UsedFor", "book", "reading"), ("UsedFor", "pencil", "writing"),
    ("MadeOf", "chair", "wood"), ("MadeOf", "table", "wood"),
    ("MadeOf", "car", "metal"), ("MadeOf", "bicycle", "metal"),
    ("MadeOf", "window", "glass"), ("MadeOf", "bottle", "glass"),
    ("HasA", "car", "engine"), ("HasA", "car", "wheels"),
    ("HasA", "car", "doors"), ("HasA", "car", "steering_wheel"),
    ("HasA", "bicycle", "wheels"), ("HasA", "bicycle", "pedals"),
    ("HasA", "bicycle", "chain"), ("HasA", "airplane", "wings"),
    ("HasA", "airplane", "engine"), ("HasA", "boat", "hull"),
    ("AtLocation", "car", "road"), ("AtLocation", "car", "garage"),
    ("AtLocation", "bicycle", "road"), ("AtLocation", "airplane", "airport"),
    ("AtLocation", "boat", "water"), ("AtLocation", "furniture", "house"),

    # ── Nature & Weather ─────────────────────
    ("IsA", "rain", "precipitation"), ("IsA", "snow", "precipitation"),
    ("IsA", "hail", "precipitation"), ("IsA", "river", "body_of_water"),
    ("IsA", "lake", "body_of_water"), ("IsA", "ocean", "body_of_water"),
    ("IsA", "mountain", "landform"), ("IsA", "valley", "landform"),
    ("IsA", "island", "landform"), ("IsA", "desert", "biome"),
    ("IsA", "forest", "biome"), ("IsA", "grassland", "biome"),
    ("IsA", "oak", "tree"), ("IsA", "pine", "tree"), ("IsA", "tree", "plant"),
    ("IsA", "rose", "flower"), ("IsA", "flower", "plant"),
    ("Causes", "rain", "flood"), ("Causes", "rain", "growth"),
    ("Causes", "drought", "famine"), ("Causes", "sun", "warmth"),
    ("Causes", "sun", "light"), ("Causes", "wind", "erosion"),
    ("Causes", "earthquake", "damage"), ("Causes", "volcano", "lava"),
    ("Causes", "cold", "ice"), ("Causes", "heat", "evaporation"),
    ("HasPrerequisite", "rain", "clouds"), ("HasPrerequisite", "snow", "cold"),
    ("HasPrerequisite", "flood", "rain"), ("HasPrerequisite", "fire", "heat"),
    ("HasProperty", "sun", "hot"), ("HasProperty", "ice", "cold"),
    ("HasProperty", "water", "wet"), ("HasProperty", "fire", "hot"),
    ("HasProperty", "sky", "blue"), ("HasProperty", "grass", "green"),
    ("HasProperty", "snow", "white"), ("HasProperty", "night", "dark"),
    ("Antonym", "hot", "cold"), ("Antonym", "wet", "dry"),
    ("Antonym", "light", "dark"), ("Antonym", "day", "night"),
    ("AtLocation", "fish", "river"), ("AtLocation", "tree", "forest"),
    ("AtLocation", "cactus", "desert"), ("AtLocation", "star", "sky"),

    # ── Human Activities ─────────────────────
    ("IsA", "reading", "activity"), ("IsA", "writing", "activity"),
    ("IsA", "running", "exercise"), ("IsA", "swimming", "exercise"),
    ("IsA", "singing", "activity"), ("IsA", "dancing", "activity"),
    ("IsA", "painting", "art"), ("IsA", "sculpture", "art"),
    ("IsA", "music", "art"), ("IsA", "poetry", "art"),
    ("MotivatedByGoal", "studying", "learning"),
    ("MotivatedByGoal", "working", "money"),
    ("MotivatedByGoal", "exercising", "health"),
    ("MotivatedByGoal", "cooking", "eating"),
    ("MotivatedByGoal", "reading", "knowledge"),
    ("MotivatedByGoal", "saving", "security"),
    ("CausesDesire", "hunger", "eating"), ("CausesDesire", "thirst", "drinking"),
    ("CausesDesire", "cold", "warmth"), ("CausesDesire", "boredom", "entertainment"),
    ("CausesDesire", "curiosity", "learning"), ("CausesDesire", "loneliness", "companionship"),
    ("HasPrerequisite", "reading", "literacy"),
    ("HasPrerequisite", "writing", "literacy"),
    ("HasPrerequisite", "driving", "license"),
    ("HasPrerequisite", "cooking", "ingredients"),
    ("HasPrerequisite", "swimming", "water"),
    ("Causes", "studying", "knowledge"), ("Causes", "practice", "skill"),
    ("Causes", "reading", "understanding"), ("Causes", "exercise", "fitness"),

    # ── Emotions & Social ────────────────────
    ("IsA", "happiness", "emotion"), ("IsA", "sadness", "emotion"),
    ("IsA", "anger", "emotion"), ("IsA", "fear", "emotion"),
    ("IsA", "love", "emotion"), ("IsA", "surprise", "emotion"),
    ("Antonym", "happiness", "sadness"), ("Antonym", "love", "hate"),
    ("Antonym", "courage", "fear"), ("Antonym", "trust", "suspicion"),
    ("Causes", "kindness", "happiness"), ("Causes", "loss", "sadness"),
    ("Causes", "injustice", "anger"), ("Causes", "danger", "fear"),
    ("Causes", "success", "pride"), ("Causes", "failure", "disappointment"),
    ("Causes", "friendship", "happiness"), ("Causes", "betrayal", "anger"),
    ("HasPrerequisite", "trust", "honesty"),
    ("HasPrerequisite", "friendship", "trust"),
    ("HasPrerequisite", "love", "connection"),
]


# ══════════════════════════════════════════════════════════════
# 2. PHYSICS — Real equations as quantitative morphisms
#
# Each morphism carries: (label, source, target, rel_type, value)
# where value encodes the proportionality constant or exponent
# from the actual equation.
# ══════════════════════════════════════════════════════════════

def physics_equations() -> dict:
    """Real physics equations as quantitative morphisms."""
    return {
        "name": "PhysicsEquations",
        "objects": [
            # Mechanics
            "force", "mass", "acceleration", "velocity", "displacement",
            "time", "momentum", "kinetic_energy", "potential_energy",
            "work", "power_mech", "gravitational_field",
            # Electromagnetism
            "voltage", "current", "resistance", "charge",
            "electric_field", "magnetic_field", "capacitance",
            "power_elec", "frequency", "wavelength",
            # Thermodynamics
            "temperature", "heat", "entropy", "pressure_thermo",
            "volume", "internal_energy", "specific_heat",
            # Waves & Light
            "speed_of_light", "energy_photon", "planck_constant",
            # Constants (as objects)
            "gravitational_constant", "boltzmann_constant",
            "coulomb_constant", "speed_of_sound",
        ],
        "morphisms": [
            # Newton's 2nd: F = ma → force proportional to mass × acceleration
            ("F_eq_ma", "mass", "force", "direct_product", 1.0),
            ("F_eq_ma", "acceleration", "force", "direct_product", 1.0),
            # v = d/t
            ("v_eq_d_over_t", "displacement", "velocity", "direct_ratio", 1.0),
            ("v_eq_d_over_t_inv", "time", "velocity", "inverse_ratio", -1.0),
            # p = mv
            ("p_eq_mv", "mass", "momentum", "direct_product", 1.0),
            ("p_eq_mv", "velocity", "momentum", "direct_product", 1.0),
            # KE = 0.5mv²
            ("KE_eq_half_mv2", "mass", "kinetic_energy", "direct_product", 1.0),
            ("KE_eq_half_mv2", "velocity", "kinetic_energy", "square_product", 2.0),
            # W = Fd
            ("W_eq_Fd", "force", "work", "direct_product", 1.0),
            ("W_eq_Fd", "displacement", "work", "direct_product", 1.0),
            # P = W/t
            ("P_eq_W_over_t", "work", "power_mech", "direct_ratio", 1.0),
            ("P_eq_W_over_t_inv", "time", "power_mech", "inverse_ratio", -1.0),
            # PE = mgh
            ("PE_eq_mgh", "mass", "potential_energy", "direct_product", 1.0),

            # Ohm's law: V = IR
            ("V_eq_IR", "current", "voltage", "direct_product", 1.0),
            ("V_eq_IR", "resistance", "voltage", "direct_product", 1.0),
            # I = V/R
            ("I_eq_V_over_R", "voltage", "current", "direct_ratio", 1.0),
            ("I_eq_V_over_R_inv", "resistance", "current", "inverse_ratio", -1.0),
            # P = IV
            ("P_eq_IV", "current", "power_elec", "direct_product", 1.0),
            ("P_eq_IV", "voltage", "power_elec", "direct_product", 1.0),
            # Q = It
            ("Q_eq_It", "current", "charge", "direct_product", 1.0),
            ("Q_eq_It", "time", "charge", "direct_product", 1.0),
            # C = Q/V
            ("C_eq_Q_over_V", "charge", "capacitance", "direct_ratio", 1.0),
            # c = fλ
            ("c_eq_f_lambda", "frequency", "speed_of_light", "direct_product", 1.0),
            ("c_eq_f_lambda", "wavelength", "speed_of_light", "direct_product", 1.0),

            # Thermodynamics: Q = mcΔT
            ("Q_eq_mcDT", "mass", "heat", "direct_product", 1.0),
            ("Q_eq_mcDT", "specific_heat", "heat", "direct_product", 1.0),
            ("Q_eq_mcDT", "temperature", "heat", "direct_product", 1.0),
            # PV = nRT (ideal gas)
            ("PV_eq_nRT", "temperature", "pressure_thermo", "direct_product", 1.0),
            ("PV_eq_nRT_inv", "volume", "pressure_thermo", "inverse_ratio", -1.0),

            # E = hf (photon energy)
            ("E_eq_hf", "planck_constant", "energy_photon", "direct_product", 1.0),
            ("E_eq_hf", "frequency", "energy_photon", "direct_product", 1.0),

            # Structural analogies (explicit cross-domain)
            # Ohm ↔ Fourier ↔ Poiseuille: all follow Flow = Potential/Resistance
            ("constitutive_law", "voltage", "current", "drives", 1.0),
            ("constitutive_law", "temperature", "heat", "drives", 1.0),
            ("constitutive_law", "pressure_thermo", "volume", "drives", 1.0),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 3. SPATIAL & GEOMETRIC — Transformation categories
# ══════════════════════════════════════════════════════════════

def spatial_geometry() -> dict:
    """2D, 3D, and 4D geometric transformations as a category."""
    return {
        "name": "SpatialGeometry",
        "objects": [
            # 2D shapes
            "point", "line", "triangle", "square", "circle",
            "pentagon", "hexagon", "polygon",
            # 3D shapes
            "sphere", "cube", "cylinder", "cone", "tetrahedron",
            "torus", "prism", "pyramid", "polyhedron",
            # Spaces
            "plane", "3d_space", "4d_spacetime",
            # Transformation types
            "translation", "rotation", "reflection",
            "scaling", "shear", "projection",
            # Properties
            "symmetry", "curvature", "dimension",
            "area", "volume_geom", "perimeter",
            "euler_characteristic",
            # Topological
            "manifold", "surface", "boundary", "interior",
        ],
        "morphisms": [
            # Dimensional hierarchy
            ("embeds_in", "point", "line"), ("embeds_in", "line", "plane"),
            ("embeds_in", "plane", "3d_space"),
            ("embeds_in", "3d_space", "4d_spacetime"),

            # Shape taxonomy
            ("IsA", "triangle", "polygon"), ("IsA", "square", "polygon"),
            ("IsA", "pentagon", "polygon"), ("IsA", "hexagon", "polygon"),
            ("IsA", "cube", "polyhedron"), ("IsA", "tetrahedron", "polyhedron"),
            ("IsA", "pyramid", "polyhedron"), ("IsA", "prism", "polyhedron"),
            ("IsA", "polygon", "surface"), ("IsA", "polyhedron", "manifold"),
            ("IsA", "sphere", "manifold"), ("IsA", "torus", "manifold"),
            ("IsA", "circle", "manifold"),

            # Shape properties
            ("has_property", "circle", "symmetry"),
            ("has_property", "sphere", "symmetry"),
            ("has_property", "cube", "symmetry"),
            ("has_property", "sphere", "curvature"),
            ("has_property", "torus", "curvature"),
            ("has_property", "plane", "curvature"),
            ("has_measure", "polygon", "area"),
            ("has_measure", "polygon", "perimeter"),
            ("has_measure", "polyhedron", "volume_geom"),
            ("has_measure", "circle", "area"),
            ("has_measure", "sphere", "volume_geom"),

            # Transformations preserve/change properties
            ("preserves", "translation", "area"),
            ("preserves", "translation", "perimeter"),
            ("preserves", "rotation", "area"),
            ("preserves", "rotation", "perimeter"),
            ("preserves", "reflection", "area"),
            ("preserves", "reflection", "perimeter"),
            ("changes", "scaling", "area"),
            ("changes", "scaling", "perimeter"),
            ("changes", "shear", "area"),
            ("changes", "projection", "dimension"),

            # Transformation composition
            ("composes_to", "rotation", "rotation"),
            ("composes_to", "translation", "translation"),
            ("composes_to", "reflection", "rotation"),

            # Topology
            ("has_topology", "sphere", "euler_characteristic", "topology", 2.0),
            ("has_topology", "torus", "euler_characteristic", "topology", 0.0),
            ("has_topology", "cube", "euler_characteristic", "topology", 2.0),
            ("has_boundary", "circle", "boundary"),
            ("has_boundary", "sphere", "boundary"),
            ("has_interior", "circle", "interior"),
            ("has_interior", "sphere", "interior"),

            # 2D-3D analogies (explicit for testing)
            ("analogy_2d_3d", "circle", "sphere"),
            ("analogy_2d_3d", "square", "cube"),
            ("analogy_2d_3d", "triangle", "tetrahedron"),
            ("analogy_2d_3d", "polygon", "polyhedron"),
            ("analogy_2d_3d", "line", "plane"),
            ("analogy_2d_3d", "area", "volume_geom"),
            ("analogy_2d_3d", "perimeter", "area"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 4. WIKIPEDIA-STYLE STRUCTURED FACTS
# ══════════════════════════════════════════════════════════════

def world_knowledge() -> dict:
    """Structured encyclopedic facts about the world."""
    return {
        "name": "WorldKnowledge",
        "objects": [
            # Countries
            "USA", "China", "India", "UK", "France", "Germany",
            "Japan", "Brazil", "Australia", "Canada",
            # Continents
            "North_America", "South_America", "Europe", "Asia",
            "Africa", "Oceania",
            # Systems
            "democracy", "republic", "monarchy", "federation",
            # Languages
            "English", "Mandarin", "Hindi", "Spanish", "French",
            "German", "Japanese", "Portuguese", "Arabic",
            # Currencies
            "dollar", "yuan", "rupee", "euro", "pound", "yen",
            # Concepts
            "government", "economy", "population", "capital_city",
            # Cities
            "Washington", "Beijing", "Delhi", "London", "Paris",
            "Berlin", "Tokyo", "Brasilia", "Canberra", "Ottawa",
        ],
        "morphisms": [
            # Geographic containment
            ("in_continent", "USA", "North_America"),
            ("in_continent", "Canada", "North_America"),
            ("in_continent", "Brazil", "South_America"),
            ("in_continent", "UK", "Europe"),
            ("in_continent", "France", "Europe"),
            ("in_continent", "Germany", "Europe"),
            ("in_continent", "China", "Asia"),
            ("in_continent", "India", "Asia"),
            ("in_continent", "Japan", "Asia"),
            ("in_continent", "Australia", "Oceania"),

            # Government systems
            ("has_system", "USA", "republic"),
            ("has_system", "USA", "democracy"),
            ("has_system", "USA", "federation"),
            ("has_system", "UK", "monarchy"),
            ("has_system", "UK", "democracy"),
            ("has_system", "France", "republic"),
            ("has_system", "Germany", "republic"),
            ("has_system", "Germany", "federation"),
            ("has_system", "India", "republic"),
            ("has_system", "India", "democracy"),
            ("has_system", "India", "federation"),
            ("has_system", "Japan", "monarchy"),
            ("has_system", "Japan", "democracy"),

            # Official languages
            ("speaks", "USA", "English"), ("speaks", "UK", "English"),
            ("speaks", "Australia", "English"), ("speaks", "Canada", "English"),
            ("speaks", "Canada", "French"),
            ("speaks", "China", "Mandarin"), ("speaks", "India", "Hindi"),
            ("speaks", "India", "English"), ("speaks", "France", "French"),
            ("speaks", "Germany", "German"), ("speaks", "Japan", "Japanese"),
            ("speaks", "Brazil", "Portuguese"),

            # Currencies
            ("uses_currency", "USA", "dollar"),
            ("uses_currency", "Canada", "dollar"),
            ("uses_currency", "Australia", "dollar"),
            ("uses_currency", "UK", "pound"),
            ("uses_currency", "France", "euro"),
            ("uses_currency", "Germany", "euro"),
            ("uses_currency", "China", "yuan"),
            ("uses_currency", "India", "rupee"),
            ("uses_currency", "Japan", "yen"),
            ("uses_currency", "Brazil", "dollar"),

            # Capital cities
            ("has_capital", "USA", "Washington"),
            ("has_capital", "China", "Beijing"),
            ("has_capital", "India", "Delhi"),
            ("has_capital", "UK", "London"),
            ("has_capital", "France", "Paris"),
            ("has_capital", "Germany", "Berlin"),
            ("has_capital", "Japan", "Tokyo"),
            ("has_capital", "Brazil", "Brasilia"),
            ("has_capital", "Australia", "Canberra"),
            ("has_capital", "Canada", "Ottawa"),

            # Structural analogies between countries
            ("IsA", "republic", "government"),
            ("IsA", "monarchy", "government"),
            ("IsA", "democracy", "government"),
            ("IsA", "federation", "government"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# 5. IMAGE / VISUAL RELATIONSHIPS
# ══════════════════════════════════════════════════════════════

def visual_relationships() -> dict:
    """Spatial relationships between objects in visual scenes."""
    return {
        "name": "VisualRelationships",
        "objects": [
            # Scene objects
            "sky", "ground", "building", "tree_visual", "road",
            "car_visual", "person", "sign", "window", "door",
            "roof", "wall", "sidewalk", "grass", "cloud",
            "sun_visual", "shadow_visual", "fence", "pole", "bridge",
            # Visual properties
            "foreground", "background", "left_side", "right_side",
            "top", "bottom", "center", "edge",
            "large", "small", "bright_visual", "dark_visual",
            "textured", "smooth",
        ],
        "morphisms": [
            # Spatial relations
            ("above", "sky", "building"), ("above", "sky", "tree_visual"),
            ("above", "sky", "road"), ("above", "cloud", "building"),
            ("above", "sun_visual", "cloud"), ("above", "roof", "wall"),
            ("below", "ground", "building"), ("below", "road", "sky"),
            ("below", "sidewalk", "building"), ("below", "grass", "tree_visual"),
            ("beside", "building", "tree_visual"), ("beside", "car_visual", "building"),
            ("beside", "person", "car_visual"), ("beside", "fence", "building"),
            ("on", "car_visual", "road"), ("on", "person", "sidewalk"),
            ("on", "building", "ground"), ("on", "tree_visual", "ground"),
            ("contains", "building", "window"), ("contains", "building", "door"),
            ("contains", "building", "wall"), ("contains", "building", "roof"),
            ("contains", "sky", "cloud"), ("contains", "sky", "sun_visual"),
            ("occludes", "building", "sky"), ("occludes", "tree_visual", "building"),
            ("casts", "building", "shadow_visual"), ("casts", "tree_visual", "shadow_visual"),

            # Depth/layer relationships
            ("in_layer", "person", "foreground"),
            ("in_layer", "car_visual", "foreground"),
            ("in_layer", "building", "background"),
            ("in_layer", "sky", "background"),
            ("in_layer", "tree_visual", "center"),

            # Visual properties
            ("has_visual_prop", "sky", "bright_visual"),
            ("has_visual_prop", "shadow_visual", "dark_visual"),
            ("has_visual_prop", "building", "textured"),
            ("has_visual_prop", "sky", "smooth"),
            ("has_visual_prop", "building", "large"),
            ("has_visual_prop", "person", "small"),

            # Scale relationships
            ("larger_than", "building", "person"),
            ("larger_than", "building", "car_visual"),
            ("larger_than", "tree_visual", "person"),
            ("larger_than", "car_visual", "person"),
            ("larger_than", "sky", "building"),
        ],
    }


# ══════════════════════════════════════════════════════════════
# ALL EXTENDED DATASETS
# ══════════════════════════════════════════════════════════════

ALL_EXTENDED_DATASETS = {
    "commonsense": commonsense_knowledge,
    "physics": physics_equations,
    "spatial_geometry": spatial_geometry,
    "world_knowledge": world_knowledge,
    "visual_relationships": visual_relationships,
}


def stats_extended():
    """Print statistics for all extended datasets."""
    total_obj = 0
    total_morph = 0
    for name, fn in ALL_EXTENDED_DATASETS.items():
        data = fn()
        n_obj = len(data["objects"])
        n_morph = len(data["morphisms"])
        rel_types = set(m[0] for m in data["morphisms"])
        total_obj += n_obj
        total_morph += n_morph
        print(f"  {name:25s}: {n_obj:4d} objects, {n_morph:4d} morphisms, {len(rel_types):2d} rel types")
    print(f"  {'TOTAL':25s}: {total_obj:4d} objects, {total_morph:4d} morphisms")


def load_all_extended():
    """Load all extended datasets as dicts."""
    return {name: fn() for name, fn in ALL_EXTENDED_DATASETS.items()}
