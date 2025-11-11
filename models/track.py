from dataclasses import dataclass
from enum import Enum


@dataclass
class Track:
    """Represents a music track with metadata."""
    title: str
    artist: str
    album: str
    duration: str  # Format: "MM:SS"
    file_path: str = ""  # Empty for placeholder


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
