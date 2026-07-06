"""Resultado genérico de uma conversão/exportação em disco."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConversionResult:
    success: bool
    # Arquivos gerados (o primeiro é o principal, quando aplicável).
    output_files: list[Path] = field(default_factory=list)
    manifest_path: Path | None = None
    backend_name: str = ""
    message: str = ""
    warnings: list[str] = field(default_factory=list)
