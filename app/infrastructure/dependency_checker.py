"""Verificação de dependências (Seção 12).

Detecta pacotes Python e binários externos, sua versão/caminho e disponibilidade,
classificando-os por criticidade e agrupando-os por módulo funcional.

Não importa bibliotecas pesadas de fato — apenas checa se estão importáveis via
importlib.util.find_spec, para manter a verificação rápida e sem efeitos colaterais.
"""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import importlib.util
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum


class Criticality(StrEnum):
    REQUIRED = "Obrigatória"
    RECOMMENDED = "Recomendada"
    OPTIONAL = "Opcional"
    EXPERIMENTAL = "Experimental"


class DepKind(StrEnum):
    PYTHON = "python"
    BINARY = "binary"
    LANGUAGE = "language"  # ex.: pacote de idioma do Tesseract


@dataclass(frozen=True)
class DependencySpec:
    key: str                 # identificador estável
    display_name: str
    kind: DepKind
    criticality: Criticality
    module_group: str        # "PDF Cleaner", "OCR", "Transcrição", "Documentos para IA"
    # Para PYTHON: nome do módulo importável. Para BINARY: nome do executável.
    probe: str
    version_args: tuple[str, ...] = ("--version",)
    # Nomes alternativos do executável (ex.: gswin64c/gs no Windows/Linux).
    alternates: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class DependencyStatus:
    spec: DependencySpec
    available: bool
    version: str | None = None
    path: str | None = None
    detail: str = ""


@dataclass
class ModuleReport:
    module_group: str
    statuses: list[DependencyStatus] = field(default_factory=list)

    @property
    def missing_required(self) -> list[DependencyStatus]:
        return [
            s
            for s in self.statuses
            if not s.available and s.spec.criticality == Criticality.REQUIRED
        ]

    @property
    def ok(self) -> bool:
        return not self.missing_required


# --- Registro central de dependências (Seção 12) -------------------------------

DEPENDENCIES: list[DependencySpec] = [
    # PDF Cleaner
    DependencySpec("pymupdf", "PyMuPDF", DepKind.PYTHON, Criticality.REQUIRED,
                   "PDF Cleaner", "fitz"),
    DependencySpec("pypdf", "pypdf", DepKind.PYTHON, Criticality.REQUIRED,
                   "PDF Cleaner", "pypdf"),
    DependencySpec("pikepdf", "pikepdf", DepKind.PYTHON, Criticality.RECOMMENDED,
                   "PDF Cleaner", "pikepdf"),
    DependencySpec("qpdf", "qpdf", DepKind.BINARY, Criticality.OPTIONAL,
                   "PDF Cleaner", "qpdf",
                   notes="Fallback externo para PDFs problemáticos."),

    # Documentos para IA
    DependencySpec("pymupdf4llm", "PyMuPDF4LLM", DepKind.PYTHON, Criticality.RECOMMENDED,
                   "Documentos para IA", "pymupdf4llm"),
    DependencySpec("markitdown", "MarkItDown", DepKind.PYTHON, Criticality.OPTIONAL,
                   "Documentos para IA", "markitdown"),
    DependencySpec("docling", "Docling", DepKind.PYTHON, Criticality.OPTIONAL,
                   "Documentos para IA", "docling"),
    DependencySpec("marker", "Marker", DepKind.PYTHON, Criticality.OPTIONAL,
                   "Documentos para IA", "marker"),
    DependencySpec("mineru", "MinerU", DepKind.PYTHON, Criticality.EXPERIMENTAL,
                   "Documentos para IA", "magic_pdf"),
    DependencySpec("ebooklib", "ebooklib (EPUB)", DepKind.PYTHON, Criticality.RECOMMENDED,
                   "Documentos para IA", "ebooklib"),
    DependencySpec("bs4", "BeautifulSoup", DepKind.PYTHON, Criticality.RECOMMENDED,
                   "Documentos para IA", "bs4"),
    DependencySpec("calibre", "Calibre (ebook-convert)", DepKind.BINARY, Criticality.OPTIONAL,
                   "Documentos para IA", "ebook-convert"),
    DependencySpec("pandoc", "Pandoc", DepKind.BINARY, Criticality.OPTIONAL,
                   "Documentos para IA", "pandoc"),

    # OCR
    DependencySpec("ocrmypdf", "OCRmyPDF", DepKind.PYTHON, Criticality.REQUIRED,
                   "OCR", "ocrmypdf"),
    DependencySpec("tesseract", "Tesseract", DepKind.BINARY, Criticality.REQUIRED,
                   "OCR", "tesseract"),
    DependencySpec("tesseract_por", "Tesseract idioma: por", DepKind.LANGUAGE,
                   Criticality.REQUIRED, "OCR", "por",
                   notes="Pacote de idioma português para OCR."),
    DependencySpec("ghostscript", "Ghostscript", DepKind.BINARY, Criticality.REQUIRED,
                   "OCR", "gswin64c", alternates=("gswin32c", "gs")),

    # Transcrição
    DependencySpec("ffmpeg", "FFmpeg", DepKind.BINARY, Criticality.REQUIRED,
                   "Transcrição", "ffmpeg"),
    DependencySpec("faster_whisper", "faster-whisper", DepKind.PYTHON,
                   Criticality.REQUIRED, "Transcrição", "faster_whisper"),
    DependencySpec("whisper_cpp", "whisper.cpp", DepKind.BINARY, Criticality.OPTIONAL,
                   "Transcrição", "whisper-cli",
                   notes="Backend alternativo de transcrição."),
]


# --- Sondas --------------------------------------------------------------------

def _probe_python(spec: DependencySpec) -> DependencyStatus:
    try:
        found = importlib.util.find_spec(spec.probe) is not None
    except (ImportError, ValueError):
        found = False
    version = None
    path = None
    if found:
        # tenta metadata pelo display/dist name mais provável
        for dist in (spec.key, spec.probe, spec.display_name):
            try:
                version = importlib_metadata.version(dist)
                break
            except importlib_metadata.PackageNotFoundError:
                continue
        spec_obj = importlib.util.find_spec(spec.probe)
        if spec_obj and spec_obj.origin:
            path = spec_obj.origin
    return DependencyStatus(spec=spec, available=found, version=version, path=path)


def _run_version(executable_path: str, args: tuple[str, ...]) -> str | None:
    try:
        out = subprocess.run(
            [executable_path, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = (out.stdout or out.stderr or "").strip()
        return text.splitlines()[0] if text else None
    except (OSError, subprocess.SubprocessError):
        return None


def _probe_binary(spec: DependencySpec) -> DependencyStatus:
    path = None
    for name in (spec.probe, *spec.alternates):
        path = shutil.which(name)
        if path:
            break
    if not path:
        return DependencyStatus(spec=spec, available=False)
    version = _run_version(path, spec.version_args)
    return DependencyStatus(spec=spec, available=True, version=version, path=path)


def _probe_tesseract_language(spec: DependencySpec) -> DependencyStatus:
    tess = shutil.which("tesseract")
    if not tess:
        return DependencyStatus(
            spec=spec, available=False, detail="Tesseract não encontrado."
        )
    try:
        out = subprocess.run(
            [tess, "--list-langs"], capture_output=True, text=True, timeout=10
        )
        langs = (out.stdout or out.stderr or "").splitlines()
        available = spec.probe in {line.strip() for line in langs}
        return DependencyStatus(spec=spec, available=available, path=tess)
    except (OSError, subprocess.SubprocessError):
        return DependencyStatus(spec=spec, available=False)


def check_dependency(spec: DependencySpec) -> DependencyStatus:
    if spec.kind == DepKind.PYTHON:
        return _probe_python(spec)
    if spec.kind == DepKind.LANGUAGE:
        return _probe_tesseract_language(spec)
    return _probe_binary(spec)


def check_all() -> list[ModuleReport]:
    """Retorna relatórios agrupados por módulo, preservando a ordem de registro."""
    groups: dict[str, ModuleReport] = {}
    order: list[str] = []
    for spec in DEPENDENCIES:
        if spec.module_group not in groups:
            groups[spec.module_group] = ModuleReport(module_group=spec.module_group)
            order.append(spec.module_group)
        groups[spec.module_group].statuses.append(check_dependency(spec))
    return [groups[name] for name in order]
