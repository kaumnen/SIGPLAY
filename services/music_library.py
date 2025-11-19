from __future__ import annotations

from pathlib import Path
import logging

from mutagen import File as MutagenFile

from models.track import Track

logger = logging.getLogger(__name__)


class MusicLibrary:
    """Service for discovering and managing music files."""
    
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a'}
    DEFAULT_MUSIC_DIR = Path.home() / "Music"
    
    def __init__(self, music_dir: Path | None = None):
        """Initialize MusicLibrary with optional custom music directory.
        
        Args:
            music_dir: Path to music directory. Defaults to ~/Music if not provided.
        """
        self.music_dir = music_dir or self.DEFAULT_MUSIC_DIR
        self._tracks: list[Track] = []
    
    def scan(self) -> list[Track]:
        """Scan music directory for audio files and build track list.
        
        Returns:
            List of Track objects sorted by artist, album, then title.
        
        Raises:
            FileNotFoundError: If music directory doesn't exist.
            PermissionError: If music directory cannot be accessed.
        """
        self._tracks = []
        
        if not self.music_dir.exists():
            logger.warning(f"Music directory does not exist: {self.music_dir}")
            raise FileNotFoundError(
                f"Music directory not found: {self.music_dir}\n\n"
                f"Please ensure your music files are in the default location,\n"
                f"or the directory exists and is accessible."
            )
        
        if not self.music_dir.is_dir():
            logger.error(f"Music path is not a directory: {self.music_dir}")
            raise NotADirectoryError(f"{self.music_dir} is not a directory")
        
        try:
            audio_files = []
            for ext in self.SUPPORTED_EXTENSIONS:
                audio_files.extend(self.music_dir.rglob(f"*{ext}"))
            
            logger.info(f"Found {len(audio_files)} audio files in {self.music_dir}")
            
            skipped_files = 0
            for file_path in audio_files:
                try:
                    metadata = self._extract_metadata(file_path)
                    track = Track.from_file(file_path, metadata)
                    self._tracks.append(track)
                except Exception as e:
                    skipped_files += 1
                    logger.warning(f"Skipped corrupted file {file_path}: {e}")
                    continue
            
            if skipped_files > 0:
                logger.info(f"Skipped {skipped_files} corrupted or unreadable files")
            
            self._tracks.sort(key=lambda t: (t.artist.lower(), t.album.lower(), t.title.lower()))
            logger.info(f"Successfully loaded {len(self._tracks)} tracks")
            
            return self._tracks
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing music directory: {self.music_dir}")
            raise PermissionError(
                f"Cannot access music directory: {self.music_dir}\n\n"
                f"Please check directory permissions."
            ) from e
    
    def get_tracks(self) -> list[Track]:
        """Return cached track list.
        
        Returns:
            List of Track objects from last scan.
        """
        return self._tracks
    
    @staticmethod
    def _extract_metadata(file_path: Path) -> dict[str, any]:
        """Extract metadata from audio file using mutagen.
        
        Args:
            file_path: Path to audio file.
            
        Returns:
            Dictionary containing title, artist, album, and duration.
            Uses fallbacks for missing tags.
            
        Raises:
            ValueError: If file is corrupted or cannot be read.
            FileNotFoundError: If file doesn't exist.
        """
        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        try:
            audio = MutagenFile(file_path, easy=True)
            
            if audio is None:
                logger.warning(f"Mutagen could not read file: {file_path}")
                raise ValueError(f"Corrupted or unsupported audio file: {file_path.name}")
            
            title = file_path.stem
            if audio.tags:
                if 'title' in audio.tags:
                    title = str(audio.tags['title'][0]) if isinstance(audio.tags['title'], list) else str(audio.tags['title'])
                elif 'TIT2' in audio.tags:
                    title = str(audio.tags['TIT2'])
            
            artist = "Unknown Artist"
            if audio.tags:
                if 'artist' in audio.tags:
                    artist = str(audio.tags['artist'][0]) if isinstance(audio.tags['artist'], list) else str(audio.tags['artist'])
                elif 'TPE1' in audio.tags:
                    artist = str(audio.tags['TPE1'])
            
            album = "Unknown Album"
            if audio.tags:
                if 'album' in audio.tags:
                    album = str(audio.tags['album'][0]) if isinstance(audio.tags['album'], list) else str(audio.tags['album'])
                elif 'TALB' in audio.tags:
                    album = str(audio.tags['TALB'])
            
            duration = 0.0
            if audio.info and hasattr(audio.info, 'length'):
                duration = float(audio.info.length)
            
            logger.debug(f"Extracted metadata from {file_path.name}: {title} by {artist}")
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {type(e).__name__}: {e}")
            raise ValueError(f"Cannot read audio file {file_path.name}: {type(e).__name__}") from e
