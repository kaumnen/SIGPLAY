from pathlib import Path
from typing import List, Optional

from models.track import Track


class MusicLibrary:
    """Service for discovering and managing music files."""
    
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a'}
    DEFAULT_MUSIC_DIR = Path.home() / "Music"
    
    def __init__(self, music_dir: Optional[Path] = None):
        """Initialize MusicLibrary with optional custom music directory.
        
        Args:
            music_dir: Path to music directory. Defaults to ~/Music if not provided.
        """
        self.music_dir = music_dir or self.DEFAULT_MUSIC_DIR
        self._tracks: List[Track] = []
