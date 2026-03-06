"""
Category Management

Define, validate, and manipulate categories. A category consists of:
- Objects (typed entities)
- Morphisms (typed relationships between objects)
- Composition table (how morphisms chain together)
- Identity morphisms (every object has one)

All categories are validated against the categorical laws:
1. Composition closure: composable pairs have a defined composite
2. Associativity: h∘(g∘f) = (h∘g)∘f
3. Identity: id_B ∘ f = f = f ∘ id_A for any f: A → B
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid

from .epistemic import (
    EpistemicStatus, Definite, Probable, Possible, Speculative, Contradicted,
    compose_epistemic, parse_epistemic,
)


@dataclass
class Morphism:
    """A morphism (arrow) in a MORPHOS category.

    Extended fields:
    - rel_type: categorical relationship type (hypernym, causes, etc.)
    - value: quantitative value carried by the morphism
    - temporal_order: integer ordering for sequential morphisms
    - truth_value: Phase 2 topos logic truth value (TruthValue from topos.py)
                   When set, this takes precedence over the Phase 1 status field
                   for all logical operations.
    - metadata: arbitrary key-value data for domain-specific attributes
    """

    id: str
    label: str
    source: str
    target: str
    status: EpistemicStatus = field(default_factory=Definite)
    is_identity: bool = False
    is_composition: bool = False
    composed_from: Optional[tuple[str, str]] = None
    rel_type: str = ""
    value: Optional[float] = None
    temporal_order: Optional[int] = None
    truth_value: object = None  # TruthValue from topos.py (Phase 2)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "label": self.label,
            "source": self.source,
            "target": self.target,
            "epistemic_status": self.status.label(),
            "is_identity": self.is_identity,
            "is_composition": self.is_composition,
        }
        if self.composed_from:
            d["composed_from"] = list(self.composed_from)
        if self.rel_type:
            d["rel_type"] = self.rel_type
        if self.value is not None:
            d["value"] = self.value
        if self.temporal_order is not None:
            d["temporal_order"] = self.temporal_order
        if self.truth_value is not None:
            d["truth_value"] = self.truth_value.label()
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class Category:
    """
    A MORPHOS category with objects, morphisms, composition table,
    and epistemic tracking.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    objects: list[str] = field(default_factory=list)
    morphisms: list[Morphism] = field(default_factory=list)
    # composition table: (f_id, g_id) -> composed_id meaning g∘f
    compositions: dict[tuple[str, str], str] = field(default_factory=dict)

    def add_object(self, label: str) -> None:
        """Add an object and its identity morphism."""
        if label in self.objects:
            return
        self.objects.append(label)
        id_morph = Morphism(
            id=str(uuid.uuid4()),
            label=f"id_{label}",
            source=label,
            target=label,
            status=Definite(),
            is_identity=True,
        )
        self.morphisms.append(id_morph)

    def add_morphism(
        self,
        label: str,
        source: str,
        target: str,
        status: EpistemicStatus | None = None,
        rel_type: str = "",
        value: float | None = None,
        temporal_order: int | None = None,
        metadata: dict | None = None,
    ) -> Morphism:
        """Add a morphism. Source and target must already exist."""
        if source not in self.objects:
            raise ValueError(f"Source object '{source}' not in category '{self.name}'")
        if target not in self.objects:
            raise ValueError(f"Target object '{target}' not in category '{self.name}'")
        m = Morphism(
            id=str(uuid.uuid4()),
            label=label,
            source=source,
            target=target,
            status=status or Definite(),
            rel_type=rel_type or label,
            value=value,
            temporal_order=temporal_order,
            metadata=metadata or {},
        )
        self.morphisms.append(m)
        return m

    def get_morphism_by_id(self, mid: str) -> Optional[Morphism]:
        for m in self.morphisms:
            if m.id == mid:
                return m
        return None

    def get_morphism_by_label(self, label: str) -> Optional[Morphism]:
        for m in self.morphisms:
            if m.label == label:
                return m
        return None

    def non_identity_morphisms(self) -> list[Morphism]:
        return [m for m in self.morphisms if not m.is_identity]

    def user_morphisms(self) -> list[Morphism]:
        """Morphisms that are neither identities nor auto-compositions."""
        return [m for m in self.morphisms if not m.is_identity and not m.is_composition]

    def morphisms_from(self, obj: str) -> list[Morphism]:
        return [m for m in self.morphisms if m.source == obj]

    def morphisms_to(self, obj: str) -> list[Morphism]:
        return [m for m in self.morphisms if m.target == obj]

    def hom(self, source: str, target: str) -> list[Morphism]:
        """All morphisms from source to target (the hom-set)."""
        return [m for m in self.morphisms if m.source == source and m.target == target]

    def identity_for(self, obj: str) -> Optional[Morphism]:
        for m in self.morphisms:
            if m.is_identity and m.source == obj:
                return m
        return None

    def auto_compose(self) -> list[Morphism]:
        """
        Generate compositions for all composable pairs.
        For f: A→B and g: B→C, creates g∘f: A→C if one doesn't exist.
        Runs to fixpoint so chains of any length are fully composed.
        Returns list of all newly created morphisms.
        """
        all_new: list[Morphism] = []
        max_passes = len(self.objects) + 1  # longest possible chain

        for _ in range(max_passes):
            new_morphisms: list[Morphism] = []

            for f in list(self.morphisms):  # snapshot to avoid mutation during iteration
                for g in list(self.morphisms):
                    if f.target != g.source:
                        continue
                    key = (f.id, g.id)
                    if key in self.compositions:
                        continue

                    # Identity compositions: id_B ∘ f = f, g ∘ id_B = g
                    if f.is_identity:
                        self.compositions[key] = g.id
                        continue
                    if g.is_identity:
                        self.compositions[key] = f.id
                        continue

                    # Check if any morphism A→C already exists (user or composed)
                    existing = None
                    for m in self.morphisms:
                        if (
                            m.source == f.source
                            and m.target == g.target
                            and not m.is_identity
                            and m.id != f.id
                            and m.id != g.id
                        ):
                            existing = m
                            break

                    # Also check morphisms created in this pass
                    if not existing:
                        for m in new_morphisms:
                            if m.source == f.source and m.target == g.target:
                                existing = m
                                break

                    if existing:
                        self.compositions[key] = existing.id
                    else:
                        comp_status = compose_epistemic(f.status, g.status)
                        # Propagate quantitative values through composition
                        comp_value = None
                        if f.value is not None and g.value is not None:
                            comp_value = f.value * g.value  # multiplicative
                        elif f.value is not None:
                            comp_value = f.value
                        elif g.value is not None:
                            comp_value = g.value
                        # Temporal order: composition spans both
                        comp_temporal = None
                        if f.temporal_order is not None or g.temporal_order is not None:
                            comp_temporal = max(
                                f.temporal_order or 0,
                                g.temporal_order or 0,
                            )
                        # Compose truth values (Phase 2 topos logic)
                        comp_truth = None
                        if f.truth_value is not None and g.truth_value is not None:
                            try:
                                from .topos import compose_truth
                                comp_truth = compose_truth(f.truth_value, g.truth_value)
                            except ImportError:
                                pass
                        elif f.truth_value is not None:
                            comp_truth = f.truth_value
                        elif g.truth_value is not None:
                            comp_truth = g.truth_value

                        comp = Morphism(
                            id=str(uuid.uuid4()),
                            label=f"{g.label}∘{f.label}",
                            source=f.source,
                            target=g.target,
                            status=comp_status,
                            is_composition=True,
                            composed_from=(f.id, g.id),
                            rel_type="composition",
                            value=comp_value,
                            temporal_order=comp_temporal,
                            truth_value=comp_truth,
                        )
                        new_morphisms.append(comp)
                        self.compositions[key] = comp.id

            self.morphisms.extend(new_morphisms)
            all_new.extend(new_morphisms)
            if not new_morphisms:
                break  # fixpoint reached

        return all_new

    def verify(self) -> dict:
        """
        Verify the categorical laws. Returns a report dict with:
        - is_valid: bool
        - issues: list of violation descriptions
        - stats: object/morphism counts
        """
        issues: list[str] = []

        # 1. Every object has an identity morphism
        for obj in self.objects:
            if not self.identity_for(obj):
                issues.append(f"Object '{obj}' missing identity morphism")

        # 2. Composition closure — every composable pair must have a composite
        for f in self.morphisms:
            for g in self.morphisms:
                if f.target != g.source:
                    continue
                key = (f.id, g.id)
                if key not in self.compositions:
                    if not any(
                        m.source == f.source and m.target == g.target
                        for m in self.morphisms
                    ):
                        issues.append(
                            f"Missing composition: {g.label} ∘ {f.label} : "
                            f"{f.source} → {g.target}"
                        )

        # 3. Associativity check
        for f in self.morphisms:
            for g in self.morphisms:
                if f.target != g.source:
                    continue
                for h in self.morphisms:
                    if g.target != h.source:
                        continue
                    gf = self.compositions.get((f.id, g.id))
                    hg = self.compositions.get((g.id, h.id))
                    if gf and hg:
                        h_gf = self.compositions.get((gf, h.id))
                        hg_f = self.compositions.get((f.id, hg))
                        if h_gf and hg_f and h_gf != hg_f:
                            issues.append(
                                f"Associativity violation: {h.label}∘({g.label}∘{f.label}) "
                                f"≠ ({h.label}∘{g.label})∘{f.label}"
                            )

        user_m = self.user_morphisms()
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "stats": {
                "n_objects": len(self.objects),
                "n_user_morphisms": len(user_m),
                "n_total_morphisms": len(self.non_identity_morphisms()),
                "n_compositions": len(self.compositions),
            },
        }

    def to_dict(self) -> dict:
        return {
            "category_id": self.id,
            "name": self.name,
            "description": self.description,
            "objects": list(self.objects),
            "morphisms": [m.to_dict() for m in self.morphisms],
            "compositions": [
                {"f": k[0], "g": k[1], "composed": v}
                for k, v in self.compositions.items()
            ],
        }


def create_category(
    name: str,
    objects: list[str],
    morphisms: list[tuple],
    description: str = "",
    statuses: dict[str, str] | None = None,
    auto_close: bool = True,
) -> Category:
    """
    Convenience constructor.

    Args:
        name: category name
        objects: list of object labels
        morphisms: list of tuples. Supported formats:
            - (label, source, target)
            - (label, source, target, rel_type)
            - (label, source, target, rel_type, value)
            - (label, source, target, rel_type, value, temporal_order)
        description: optional description
        statuses: optional dict mapping morphism label to epistemic status string
        auto_close: if True, auto-generate compositions
    """
    statuses = statuses or {}
    cat = Category(name=name, description=description)
    for obj in objects:
        cat.add_object(obj)
    for morph_tuple in morphisms:
        label = morph_tuple[0]
        src = morph_tuple[1]
        tgt = morph_tuple[2]
        rel_type = morph_tuple[3] if len(morph_tuple) > 3 else ""
        value = morph_tuple[4] if len(morph_tuple) > 4 else None
        temporal = morph_tuple[5] if len(morph_tuple) > 5 else None
        status = parse_epistemic(statuses.get(label, "definite"))
        cat.add_morphism(
            label, src, tgt,
            status=status,
            rel_type=rel_type or label,
            value=value,
            temporal_order=temporal,
        )
    if auto_close:
        cat.auto_compose()
    return cat
