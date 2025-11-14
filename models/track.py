from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Any


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
    def from_file(cls, file_path: Path, metadata: Dict[str, Any]) -> 'Track':
        """Factory method to create Track from file and metadata."""
        return cls(
            title=metadata.get('title', file_path.stem),
            artist=metadata.get('artist', 'Unknown Artist'),
            album=metadata.get('album', 'Unknown Album'),
            duration=cls._format_duration(metadata.get('duration', 0)),
            file_path=str(file_path),
            duration_seconds=metadata.get('duration', 0)
        )
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"


class ViewState(Enum):
    """Enum for managing different view states in the application."""
    LIBRARY = "library"
    NOW_PLAYING = "now_playing"
    VISUALIZER = "visualizer"


@dataclass
class AppState:
    """Represents the current state of the application."""
    current_view: ViewState
    selected_track_index: int = 0
