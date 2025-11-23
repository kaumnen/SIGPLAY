from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from models.lyrics import LyricSegment

logger = logging.getLogger(__name__)


class LyricsService:
    """Service for managing Whisper model and lyrics transcription."""
    
    def __init__(self) -> None:
        """Initialize service with cache directory setup."""
        self._model: WhisperModel | None = None
        self._cache_dir: Path = Path.home() / ".local/share/sigplay/lyrics_cache"
        
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Lyrics cache directory: {self._cache_dir}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
    
    def _get_model(self) -> WhisperModel:
        """Lazy-load Whisper model on first use.
        
        Returns:
            WhisperModel instance configured for CPU inference with int8 quantization.
            
        Raises:
            RuntimeError: If model download or loading fails.
        """
        if self._model is None:
            try:
                logger.info("Loading Whisper large-v3 model...")
                self._model = WhisperModel(
                    "large-v3",
                    device="cpu",
                    compute_type="int8"
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
                raise RuntimeError(f"Failed to load Whisper model. Please check your internet connection and try again. Error: {e}")
        return self._model
    
    def _get_cache_key(self, track_path: str) -> str:
        """Generate cache key using MD5 hash of track path.
        
        Args:
            track_path: Path to the audio track file.
            
        Returns:
            MD5 hash of the track path as hexadecimal string.
        """
        return hashlib.md5(track_path.encode()).hexdigest()
    
    async def get_lyrics(
        self,
        track_path: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> list[LyricSegment]:
        """Get lyrics for track, from cache or by transcribing.
        
        Args:
            track_path: Path to the audio track file.
            progress_callback: Optional callback for progress updates.
            
        Returns:
            List of LyricSegment objects with timestamped lyrics.
            
        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If transcription fails.
        """
        track_file = Path(track_path)
        if not track_file.exists():
            logger.error(f"Audio file not found: {track_path}")
            raise FileNotFoundError(f"Audio file not found: {track_path}")
        
        cache_key = self._get_cache_key(track_path)
        cache_file = self._cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            logger.info(f"Loading lyrics from cache: {cache_key}")
            try:
                data = json.loads(cache_file.read_text())
                return [LyricSegment(**seg) for seg in data]
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted cache file, will re-transcribe: {e}")
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception as unlink_error:
                    logger.error(f"Failed to delete corrupted cache file: {unlink_error}", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to read cache file, will re-transcribe: {e}", exc_info=True)
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception as unlink_error:
                    logger.error(f"Failed to delete invalid cache file: {unlink_error}", exc_info=True)
        
        def _transcribe() -> list[LyricSegment]:
            """Transcribe audio in background thread.
            
            Raises:
                RuntimeError: If model loading or transcription fails.
            """
            try:
                if progress_callback:
                    progress_callback("Loading Whisper model...")
                
                model = self._get_model()
                
                if progress_callback:
                    progress_callback(f"Generating lyrics for {track_file.name}...")
                
                logger.info(f"Transcribing: {track_path}")
                
                segments, info = model.transcribe(
                    track_path,
                    word_timestamps=True,
                    beam_size=5
                )
                
                logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
                
                lyrics = []
                for segment in segments:
                    lyrics.append(LyricSegment(
                        start=segment.start,
                        end=segment.end,
                        text=segment.text.strip()
                    ))
                
                logger.info(f"Transcription complete: {len(lyrics)} segments")
                
                try:
                    cache_data = [
                        {"start": seg.start, "end": seg.end, "text": seg.text}
                        for seg in lyrics
                    ]
                    cache_file.write_text(json.dumps(cache_data, indent=2))
                    logger.info(f"Cached lyrics: {cache_key}")
                except PermissionError as e:
                    logger.error(f"Permission denied writing cache file: {e}", exc_info=True)
                except OSError as e:
                    logger.error(f"Failed to write cache file (disk full or I/O error): {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to cache lyrics: {e}", exc_info=True)
                
                return lyrics
                
            except RuntimeError:
                raise
            except FileNotFoundError as e:
                logger.error(f"Audio file not found during transcription: {e}", exc_info=True)
                raise RuntimeError(f"Audio file not found: {track_path}")
            except PermissionError as e:
                logger.error(f"Permission denied reading audio file: {e}", exc_info=True)
                raise RuntimeError(f"Permission denied: Cannot read audio file {track_file.name}")
            except Exception as e:
                logger.error(f"Transcription failed: {e}", exc_info=True)
                raise RuntimeError(f"Failed to transcribe audio. The file may be corrupted or in an unsupported format. Error: {e}")
        
        try:
            return await asyncio.to_thread(_transcribe)
        except Exception as e:
            logger.error(f"Error in transcription thread: {e}", exc_info=True)
            raise
    
    def clear_cache(self) -> None:
        """Clear all cached lyrics."""
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Lyrics cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
