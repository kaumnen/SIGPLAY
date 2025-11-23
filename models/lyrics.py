from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LyricSegment:
    """Represents a single timestamped lyric segment."""
    start: float
    end: float
    text: str
