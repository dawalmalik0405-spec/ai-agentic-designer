from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ============================================================
# Global Motion
# ============================================================

class GlobalMotion(BaseModel):
    """Overall motion language for the website."""

    motion_style: Literal[
        "minimal",
        "premium",
        "cinematic",
        "playful",
        "dynamic",
        "immersive",
    ] = Field(...)

    storytelling_style: Literal[
        "linear",
        "progressive",
        "interactive",
        "guided",
    ] = Field(...)

    animation_intensity: Literal[
        "low",
        "medium",
        "high",
    ] = Field(...)

    scrolling_behavior: Literal[
        "native",
        "smooth",
        "snap",
    ] = Field(...)

    page_transition: Literal[
        "fade",
        "slide",
        "scale",
        "none",
    ] = Field(...)

    prefers_reduced_motion: bool = True


# ============================================================
# Asset Motion
# ============================================================

class AssetMotion(BaseModel):
    """Motion applied to a generated/downloaded asset."""

    asset_id: str

    motion_type: Literal[
        "none",
        "parallax",
        "rotate",
        "float",
        "zoom",
        "scale",
        "fade",
        "reveal",
    ]

    trigger: Literal[
        "load",
        "scroll",
        "hover",
        "click",
    ]

    direction: Literal[
        "vertical",
        "horizontal",
        "both",
        "none",
    ] = "none"

    intensity: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"


# ============================================================
# Component Motion
# ============================================================

class ComponentMotion(BaseModel):
    """Motion assigned to a UI component."""

    component_name: str

    animation: Literal[
        "none",
        "fade_up",
        "fade_down",
        "fade_left",
        "fade_right",
        "lift",
        "glow",
        "scale",
        "rotate",
        "stagger",
    ]

    trigger: Literal[
        "load",
        "scroll",
        "hover",
        "click",
        "focus",
    ]

    emphasis: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"


# ============================================================
# Interaction Motion
# ============================================================

class InteractionMotion(BaseModel):
    """Interactive behaviors."""

    interaction: Literal[
        "button_hover",
        "card_hover",
        "navbar",
        "modal",
        "carousel",
        "tabs",
        "accordion",
        "form",
    ]

    animation: Literal[
        "lift",
        "glow",
        "fade",
        "scale",
        "underline",
        "slide",
        "expand",
    ]

    duration_ms: int = Field(
        ge=50,
        le=5000,
        default=300,
    )

    priority: int = Field(
        ge=1,
        le=5,
        default=3,
    )


# ============================================================
# Section Motion
# ============================================================

class SectionMotion(BaseModel):
    """Motion plan for a single section."""

    section_name: str

    entrance_animation: Literal[
        "none",
        "fade_up",
        "fade_down",
        "fade_left",
        "fade_right",
        "cinematic_reveal",
        "scale_in",
    ]

    scroll_behavior: Literal[
        "none",
        "parallax",
        "pin",
        "scrub",
        "sticky",
    ]

    hover_behavior: Literal[
        "none",
        "lift",
        "glow",
        "scale",
    ]

    emphasis: Literal[
        "low",
        "medium",
        "high",
    ]

    animation_priority: int = Field(
        ge=1,
        le=10,
    )

    notes: str = ""

    component_motion: list[ComponentMotion] = Field(default_factory=list)

    asset_motion: list[AssetMotion] = Field(default_factory=list)

    interaction_motion: list[InteractionMotion] = Field(default_factory=list)


# ============================================================
# Page Motion
# ============================================================

class PageMotion(BaseModel):
    """Motion specification for one page."""

    page_name: str

    sections: list[SectionMotion]


# ============================================================
# Implementation Preferences
# ============================================================

class ImplementationPreferences(BaseModel):
    """Preferred implementation technology."""

    page_transitions: Literal[
        "css",
        "framer_motion",
        "gsap",
    ]

    scroll_animations: Literal[
        "css",
        "framer_motion",
        "gsap",
    ]

    hover_effects: Literal[
        "css",
        "framer_motion",
        "gsap",
    ]

    micro_interactions: Literal[
        "css",
        "framer_motion",
        "gsap",
    ]



class ScrollSequence(BaseModel):
    sequence_name: str

    sections: list[str]

    behavior: Literal[
        "progressive",
        "timeline",
        "chapter",
    ]
# ============================================================
# Final Output
# ============================================================

class MotionSpecification(BaseModel):
    """Final output of the Motion Agent."""

    global_motion: GlobalMotion

    pages: list[PageMotion]

    implementation_preferences: ImplementationPreferences

    scroll_sequences: list[ScrollSequence] = Field(default_factory=list)