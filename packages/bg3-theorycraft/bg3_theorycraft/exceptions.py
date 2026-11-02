"""
bg3_theorycraft.exceptions
--------------------------
Domain exception hierarchy for Baldur's Gate 3 theorycraft combat simulation and build progression.
"""

from __future__ import annotations

from bg3_core.exceptions import BG3Error


class BG3TheorycraftError(BG3Error, RuntimeError):
    """Base domain exception for character build simulation and progression calculation."""


class BG3BuildValidationError(BG3TheorycraftError, ValueError):
    """Raised when character class, progression, or resource pool constraints are invalid."""


class BG3SimulationError(BG3TheorycraftError):
    """Raised when turn-1 DPR or combat simulation encounters unrecoverable calculation errors."""


__all__ = [
    "BG3BuildValidationError",
    "BG3SimulationError",
    "BG3TheorycraftError",
]
