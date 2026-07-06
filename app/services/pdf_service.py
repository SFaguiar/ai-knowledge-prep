"""Serviço de manipulação estrutural de PDF (Módulo 1 — PDF Cleaner).

Modelo de trabalho: um documento é uma lista ordenada de `PageRef`, cada uma
apontando para uma página de um PDF de origem, com uma rotação acumulada. Todas
as operações (remover, extrair, girar, reordenar, juntar, dividir) apenas
manipulam essa lista em memória. O arquivo original NUNCA é modificado; salvar
gera um PDF novo a partir das origens (Seção 14 — preservar originais).

Escrita via pypdf; leitura de metadados via PyMuPDF. qpdf pode ser usado como
fallback externo para PDFs problemáticos (Seção 4).
"""

from __future__ import annotations

import copy
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.infrastructure.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PageRef:
    """Referência a uma página de origem, com rotação acumulada (0/90/180/270)."""
    source_path: Path
    source_index: int  # índice 0-based na origem
    rotation: int = 0

    def with_rotation(self, delta: int) -> "PageRef":
        return PageRef(self.source_path, self.source_index, (self.rotation + delta) % 360)


@dataclass
class PdfDocumentModel:
    """Estado editável de um documento PDF com histórico de undo/redo."""
    primary_path: Path
    pages: list[PageRef] = field(default_factory=list)
    _undo: list[list[PageRef]] = field(default_factory=list)
    _redo: list[list[PageRef]] = field(default_factory=list)
    # Rastreabilidade: páginas originais (por índice 0-based da origem primária).
    original_page_count: int = 0

    # --- histórico ---
    def _snapshot(self) -> None:
        self._undo.append(copy.deepcopy(self.pages))
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(copy.deepcopy(self.pages))
            self.pages = self._undo.pop()

    def redo(self) -> None:
        if self._redo:
            self._undo.append(copy.deepcopy(self.pages))
            self.pages = self._redo.pop()

    # --- operações (índices referem-se à posição atual na lista) ---
    def remove_pages(self, indices: set[int]) -> None:
        self._snapshot()
        self.pages = [p for i, p in enumerate(self.pages) if i not in indices]

    def keep_only(self, indices: set[int]) -> None:
        """Mantém apenas as páginas selecionadas (usado por 'extrair')."""
        self._snapshot()
        self.pages = [p for i, p in enumerate(self.pages) if i in indices]

    def rotate_pages(self, indices: set[int], delta: int) -> None:
        self._snapshot()
        self.pages = [
            p.with_rotation(delta) if i in indices else p
            for i, p in enumerate(self.pages)
        ]

    def move_page(self, from_idx: int, to_idx: int) -> None:
        if from_idx == to_idx:
            return
        self._snapshot()
        page = self.pages.pop(from_idx)
        self.pages.insert(to_idx, page)

    def append_pages(self, pages: list[PageRef]) -> None:
        """Junta páginas de outro PDF ao final (merge)."""
        self._snapshot()
        self.pages.extend(pages)


# --- construção / leitura ------------------------------------------------------

def _page_count(path: Path) -> int:
    import fitz  # PyMuPDF

    with fitz.open(str(path)) as doc:
        return doc.page_count


def load_model(path: str | Path) -> PdfDocumentModel:
    p = Path(path)
    count = _page_count(p)
    pages = [PageRef(p, i) for i in range(count)]
    return PdfDocumentModel(primary_path=p, pages=pages, original_page_count=count)


def pages_from_pdf(path: str | Path) -> list[PageRef]:
    p = Path(path)
    return [PageRef(p, i) for i in range(_page_count(p))]


def detect_blank_pages(path: str | Path, text_threshold: int = 4) -> list[int]:
    """Heurística leve para páginas em branco: pouco texto e sem imagens.

    Retorna índices 0-based. Não é infalível (páginas escaneadas em branco podem
    ter ruído), por isso é uma funcionalidade auxiliar, não destrutiva.
    """
    import fitz

    blanks: list[int] = []
    with fitz.open(str(path)) as doc:
        for i, page in enumerate(doc):
            text = (page.get_text("text") or "").strip()
            images = page.get_images(full=False)
            if len(text) <= text_threshold and not images:
                blanks.append(i)
    return blanks


# --- escrita -------------------------------------------------------------------

def save_pdf(model: PdfDocumentModel, output_path: str | Path, overwrite: bool = False) -> Path:
    """Escreve um novo PDF a partir das páginas do modelo.

    Levanta FileExistsError se o destino existir e overwrite=False (Seção 14 —
    não sobrescrever sem confirmação). Nunca escreve sobre a origem.
    """
    from pypdf import PdfReader, PdfWriter

    out = Path(output_path)
    if out.exists() and not overwrite:
        raise FileExistsError(f"Arquivo de saída já existe: {out}")
    if not model.pages:
        raise ValueError("Nenhuma página para salvar.")

    # Proteção: não permitir salvar por cima de um arquivo de origem.
    sources = {pr.source_path.resolve() for pr in model.pages}
    if out.resolve() in sources:
        raise ValueError("O destino coincide com um arquivo de origem. Escolha outro nome.")

    readers: dict[Path, PdfReader] = {}
    writer = PdfWriter()
    try:
        for pref in model.pages:
            reader = readers.get(pref.source_path)
            if reader is None:
                reader = PdfReader(str(pref.source_path))
                readers[pref.source_path] = reader
            page = reader.pages[pref.source_index]
            if pref.rotation:
                page.rotate(pref.rotation)
            writer.add_page(page)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as fh:
            writer.write(fh)
    finally:
        writer.close()

    logger.info("PDF salvo: %s (%d páginas)", out.name, len(model.pages))
    return out


def split_pdf(
    source_path: str | Path,
    ranges: list[tuple[int, int]],
    output_dir: str | Path,
    stem: str | None = None,
) -> list[Path]:
    """Divide um PDF em vários arquivos por intervalos (1-based, inclusivos)."""
    from pypdf import PdfReader, PdfWriter

    src = Path(source_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = stem or src.stem
    reader = PdfReader(str(src))
    total = len(reader.pages)
    outputs: list[Path] = []

    for idx, (start, end) in enumerate(ranges, start=1):
        s = max(1, start)
        e = min(total, end)
        if s > e:
            continue
        writer = PdfWriter()
        for page_num in range(s - 1, e):
            writer.add_page(reader.pages[page_num])
        target = out_dir / f"{base}_parte{idx:02d}_{s}-{e}.pdf"
        with open(target, "wb") as fh:
            writer.write(fh)
        writer.close()
        outputs.append(target)

    logger.info("Split de %s gerou %d arquivos", src.name, len(outputs))
    return outputs


def qpdf_repair(source_path: str | Path, output_path: str | Path) -> Path:
    """Fallback: usa o binário qpdf para reparar PDFs problemáticos, se disponível."""
    qpdf = shutil.which("qpdf")
    if not qpdf:
        raise RuntimeError("qpdf não está instalado.")
    src, out = Path(source_path), Path(output_path)
    subprocess.run([qpdf, "--replace-input", str(src)] if src == out
                   else [qpdf, str(src), str(out)], check=True, timeout=120)
    return out
