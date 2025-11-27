from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def format_time(seconds: float) -> str:
    """Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string in MM:SS format
    """
    if seconds < 0:
        seconds = 0
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


@dataclass
class Track:
    """Represents a music track with metadata."""
    title: str
    artist: str
    album: str
    duration: str
    file_path: str
    duration_seconds: float
    
    @classmethod
    def from_file(cls, file_path: Path, metadata: dict[str, Any]) -> Track:
        """Factory method to create Track from file and metadata."""
        return cls(
            title=metadata.get('title', file_path.stem),
            artist=metadata.get('artist', 'Unknown Artist'),
            album=metadata.get('album', 'Unknown Album'),
            duration=format_time(metadata.get('duration', 0)),
            file_path=str(file_path),
            duration_seconds=metadata.get('duration', 0)
        )
