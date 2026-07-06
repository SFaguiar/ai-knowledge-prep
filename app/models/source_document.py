"""Representação de um documento de origem."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SourceType(StrEnum):
    PDF = "pdf"
    EPUB = "epub"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


_EXT_MAP = {
    ".pdf": SourceType.PDF,
    ".epub": SourceType.EPUB,
    ".png": SourceType.IMAGE,
    ".jpg": SourceType.IMAGE,
    ".jpeg": SourceType.IMAGE,
    ".tif": SourceType.IMAGE,
    ".tiff": SourceType.IMAGE,
    ".mp3": SourceType.AUDIO,
    ".wav": SourceType.AUDIO,
    ".m4a": SourceType.AUDIO,
    ".flac": SourceType.AUDIO,
    ".ogg": SourceType.AUDIO,
    ".mp4": SourceType.VIDEO,
    ".mkv": SourceType.VIDEO,
    ".mov": SourceType.VIDEO,
    ".avi": SourceType.VIDEO,
    ".webm": SourceType.VIDEO,
    ".docx": SourceType.DOCUMENT,
    ".pptx": SourceType.DOCUMENT,
    ".html": SourceType.DOCUMENT,
    ".htm": SourceType.DOCUMENT,
    ".txt": SourceType.DOCUMENT,
    ".md": SourceType.DOCUMENT,
}


@dataclass
class SourceDocument:
    path: Path
    source_type: SourceType

    @classmethod
    def from_path(cls, path: str | Path) -> SourceDocument:
        p = Path(path)
        stype = _EXT_MAP.get(p.suffix.lower(), SourceType.UNKNOWN)
        return cls(path=p, source_type=stype)
