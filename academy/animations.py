from pathlib import Path
import streamlit.components.v1 as components

_concept = components.declare_component(
    "concept_animation", path=str(Path(__file__).parent / "components/concept")
)


def concept_animation(level):
    """Only version-controlled curriculum data is passed to the animation frame."""
    return _concept(animation=level.animation, level=level.id, key=f"concept-{level.id}", default=None)
