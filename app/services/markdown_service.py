"""Utilidades de Markdown/texto para exportação (Etapas 3–7).

Funções puras e testáveis: redução de Markdown para texto simples, divisão por
tamanho máximo de caracteres respeitando parágrafos, geração de índice e
slugs seguros para nomes de arquivo.
"""

from __future__ import annotations

import re
import unicodedata


def markdown_to_plain(md: str) -> str:
    """Redução simples de Markdown para texto (sem dependências externas)."""
    text = re.sub(r"^#{1,6}\s*", "", md, flags=re.MULTILINE)            # títulos
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)                        # negrito
    text = re.sub(r"\*(.*?)\*", r"\1", text)                            # itálico
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.DOTALL)   # código
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)               # imagens
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)                # links
    return text


def split_by_max_chars(text: str, max_chars: int) -> list[str]:
    """Divide o texto em partes de até `max_chars`, quebrando em parágrafos.

    Parágrafos maiores que o limite são divididos por caracteres, garantindo
    que nenhuma parte exceda `max_chars`. Com max_chars <= 0 não há divisão.
    """
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            parts.append(current)
            current = ""

    for para in text.split("\n\n"):
        if len(para) > max_chars:
            flush()
            for i in range(0, len(para), max_chars):
                parts.append(para[i:i + max_chars])
            continue
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            flush()
            current = para
    flush()
    return parts


def build_index(entries: list[tuple[str, str]], title: str = "Índice") -> str:
    """Gera um índice Markdown a partir de pares (rótulo, caminho relativo)."""
    lines = [f"# {title}", ""]
    lines.extend(f"- [{label}]({href})" for label, href in entries)
    return "\n".join(lines) + "\n"


def slugify(name: str) -> str:
    """Nome seguro para arquivos/pastas: ASCII, minúsculo, '_' como separador."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text) or "documento"
