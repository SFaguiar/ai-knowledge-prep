"""Renderização e leitura de PDF para a UI (via PyMuPDF).

Mantém um cache de documentos abertos por caminho para evitar reabrir a cada
render, além de um cache do texto por página (usado pelas legendas/snippets e
pela busca). Retorna bytes PNG — a camada de UI converte em QPixmap. Assim o
serviço permanece independente de Qt e testável.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from app.infrastructure.logging_config import get_logger

logger = get_logger(__name__)


def normalize_text(s: str) -> str:
    """Normaliza para busca: remove acentos e caixa (comparação tolerante)."""
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


class PdfRenderService:
    def __init__(self) -> None:
        self._docs: dict[str, object] = {}
        # Cache de texto por página: {caminho_resolvido: {index: texto}}.
        self._text: dict[str, dict[int, str]] = {}

    def _get_doc(self, path: Path):
        import fitz

        key = str(path.resolve())
        doc = self._docs.get(key)
        if doc is None:
            doc = fitz.open(key)
            self._docs[key] = doc
        return doc

    def page_count(self, path: str | Path) -> int:
        return self._get_doc(Path(path)).page_count

    def render_thumbnail(
        self, path: str | Path, page_index: int, max_dim: int = 220, rotation: int = 0
    ) -> bytes:
        """Renderiza uma miniatura PNG da página (0-based)."""
        import fitz

        doc = self._get_doc(Path(path))
        page = doc.load_page(page_index)
        rect = page.rect
        scale = max_dim / max(rect.width, rect.height) if max(rect.width, rect.height) else 1.0
        matrix = fitz.Matrix(scale, scale)
        if rotation:
            matrix = matrix * fitz.Matrix(rotation)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")

    def render_page(
        self, path: str | Path, page_index: int, target_width: int = 1000,
        rotation: int = 0,
    ) -> bytes:
        """Renderiza uma página grande, ajustada a uma largura-alvo (para o preview).

        `rotation` (0/90/180/270) é a rotação acumulada da edição; a largura-alvo
        considera a orientação resultante para caber no painel.
        """
        import fitz

        doc = self._get_doc(Path(path))
        page = doc.load_page(page_index)
        rect = page.rect
        base_width = rect.height if rotation in (90, 270) else rect.width
        scale = target_width / base_width if base_width else 1.0
        scale = max(0.1, min(scale, 6.0))
        matrix = fitz.Matrix(scale, scale)
        if rotation:
            matrix = matrix * fitz.Matrix(rotation)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")

    def page_text(self, path: str | Path, page_index: int) -> str:
        """Texto da página (0-based), com cache por (arquivo, índice)."""
        p = Path(path)
        key = str(p.resolve())
        cache = self._text.setdefault(key, {})
        if page_index not in cache:
            doc = self._get_doc(p)
            cache[page_index] = (doc.load_page(page_index).get_text("text") or "").strip()
        return cache[page_index]

    def page_snippet(self, path: str | Path, page_index: int, max_chars: int = 140) -> str:
        """Primeiras linhas úteis do texto da página, elididas. '' se sem texto."""
        text = self.page_text(path, page_index)
        if not text:
            return ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        joined = "  ".join(lines)
        if len(joined) > max_chars:
            return joined[:max_chars].rstrip() + "…"
        return joined

    def page_contains(self, path: str | Path, page_index: int, normalized_query: str) -> bool:
        """True se a página contém o termo (query já normalizada por normalize_text)."""
        if not normalized_query:
            return False
        return normalized_query in normalize_text(self.page_text(path, page_index))

    def has_text_layer(self, path: str | Path, sample_pages: int = 5) -> bool:
        """Heurística para OCR: verifica se há camada textual relevante.

        Útil no Módulo 3 para detectar PDFs escaneados/com pouca camada textual.
        """
        doc = self._get_doc(Path(path))
        checked = 0
        chars = 0
        for i in range(min(sample_pages, doc.page_count)):
            chars += len((doc.load_page(i).get_text("text") or "").strip())
            checked += 1
        # Média de caracteres por página amostrada.
        return checked > 0 and (chars / checked) > 40

    def close(self, path: str | Path) -> None:
        key = str(Path(path).resolve())
        self._text.pop(key, None)
        doc = self._docs.pop(key, None)
        if doc is not None:
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass

    def close_all(self) -> None:
        for key in list(self._docs):
            self.close(key)
