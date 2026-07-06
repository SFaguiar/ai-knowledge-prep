"""Resultado de uma extração documental."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractionSection:
    """Uma seção lógica do documento (capítulo, página-intervalo, etc.)."""
    title: str
    content: str
    # Rastreabilidade da origem (ex.: "15-35" para páginas de PDF).
    source_ref: str = ""


@dataclass
class ExtractionResult:
    backend_name: str
    # Conteúdo completo já concatenado no formato solicitado.
    full_text: str
    sections: list[ExtractionSection] = field(default_factory=list)
    # Caminhos de imagens extraídas (relativos ou absolutos).
    images: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
