"""Renderização de PDF para a UI (miniaturas e páginas) via PyMuPDF.

Mantém um cache de documentos abertos por caminho para evitar reabrir a cada
miniatura. Retorna bytes PNG — a camada de UI converte em QPixmap. Assim o
serviço permanece independente de Qt e testável.
"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class PdfRenderService:
    def __init__(self) -> None:
        self._docs: dict[str, object] = {}

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
        doc = self._docs.pop(key, None)
        if doc is not None:
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass

    def close_all(self) -> None:
        for key in list(self._docs):
            self.close(key)
