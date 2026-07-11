# AI Knowledge Prep Suite

Suíte **FOSS, local e offline** para transformar material bruto — PDFs, e-books,
imagens escaneadas, áudio e vídeo — em **fontes limpas, estruturadas e legíveis
para IA** (NotebookLM, ChatGPT, Claude, Gemini e similares).

> A pergunta que o produto responde não é *"para qual formato converter?"*, e sim
> **"como transformar este material bruto em uma fonte limpa e confiável para IA?"**

- 🔒 **Local-first / offline** — nenhum upload, nenhuma conta, nenhuma telemetria.
- 🧩 **Modular e extensível** — backends de extração e transcrição intercambiáveis.
- 🖥️ **GUI-first** (PySide6/Qt), orientada por tarefas.
- 🐍 Python 3.12+.
- 📄 Licença **Apache-2.0**.

---

## Estado atual (v0.1.0)

Correspondem às **Etapas 1 a 5** do roadmap:

| Recurso | Status |
|---|---|
| Janela principal PySide6 + tela inicial por tarefas (tema escuro) | ✅ |
| Verificador de dependências (Configurações) | ✅ |
| **PDF Cleaner** (abrir, miniaturas, selecionar, remover, extrair, girar, juntar, dividir, salvar) | ✅ |
| **Documento para IA** — PDF/EPUB → Markdown/TXT, com fonte completa, capítulos/partes, índice | ✅ |
| **OCR** — PDF escaneado/imagem → PDF pesquisável + Markdown/TXT | ✅ |
| Backends de extração intercambiáveis (PyMuPDF4LLM, PyMuPDF fallback, EPUB) | ✅ |
| Presets de exportação (NotebookLM, Obsidian, LLM genérico) | ✅ |
| Preservação do arquivo original + `manifest.json` + log | ✅ |
| Jobs em background (UI não trava) | ✅ |
| Transcrição / Lote / Histórico | 🚧 planejado (Etapas 6–9) |

A arquitetura já contempla os módulos futuros (transcrição, pacotes para IA),
com interfaces claras e *stubs* onde apropriado.

### Documento para IA (Etapas 3–4)

Converte **PDF com texto nativo** e **EPUB** em Markdown/TXT, gerando um pacote
organizado com `fonte_completa`, `capitulos/` ou `partes/` (conforme o preset),
`indice.md` e `manifest.json`. O backend é escolhido automaticamente pelo tipo de
arquivo — se `pymupdf4llm` não estiver instalado, o PDF ainda é convertido com a
extração básica do PyMuPDF (dependência obrigatória). Para EPUB e para Markdown de
PDF mais estruturado, instale o grupo opcional `docs`:

```powershell
uv sync --extra docs      # ou:  pip install -e ".[docs]"
```

### OCR (Etapa 5)

Transforma **PDF escaneado** ou **imagem** (PNG/JPG/TIFF/BMP) em **PDF pesquisável**
e em Markdown/TXT com o texto reconhecido, usando OCRmyPDF + Tesseract + Ghostscript.
Detecta automaticamente se um PDF parece escaneado (pouca camada textual); por
padrão preserva páginas que já têm texto nativo (`skip_text`) — a opção **Forçar
OCR** reprocessa tudo, útil quando o texto existente está corrompido. Idioma padrão
**português**, com seleção entre os idiomas instalados no Tesseract.

Requer o pacote Python `ocrmypdf` (grupo opcional `ocr`) **e** os binários externos
Tesseract e Ghostscript:

```powershell
uv sync --extra ocr        # ou:  pip install -e ".[ocr]"
winget install UB-Mannheim.TesseractOCR   # marque o idioma "Portuguese" no instalador
winget install ArtifexSoftware.GhostScript
```

Confira o status de cada dependência em **Configurações → Verificar dependências**.

---

## Requisitos

- **Python 3.12 ou superior** (testado em 3.12/3.13).
- Windows 10/11 (alvo principal). A arquitetura permite Linux futuramente.
- Dependências externas **opcionais** conforme o módulo (ver *Dependências externas*).

---

## Instalação (Windows)

### Opção A — com `uv` (recomendado)

```powershell
# 1. Instale o Python 3.12+ (https://www.python.org/downloads/ ou: winget install Python.Python.3.12)
# 2. Instale o uv (https://docs.astral.sh/uv/):
winget install astral-sh.uv

# 3. Clone o repositório e entre na pasta
git clone https://github.com/samuel/ai-knowledge-prep
cd ai-knowledge-prep

# 4. Crie o ambiente e instale as dependências do MVP
uv sync

# 5. Rode o aplicativo
uv run python -m app.main
```

### Opção B — com venv + pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m app.main
```

### Opção C — script de setup

O script detecta Python/uv e prepara o ambiente automaticamente:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

Depois de abrir, vá em **Configurações** → **Verificar dependências** para ver o
que está instalado e o que falta para cada módulo.

### Grupos de dependências opcionais

O MVP instala apenas o essencial (PySide6, PyMuPDF, pypdf, pikepdf). Os backends
mais pesados ficam em grupos separados para manter a instalação leve:

```powershell
uv sync --extra docs         # Documento para IA (PyMuPDF4LLM, MarkItDown, EPUB)
uv sync --extra ocr          # OCRmyPDF
uv sync --extra media        # faster-whisper (transcrição)
uv sync --extra docs-advanced # Docling, Marker (avançado/experimental)
# com pip:  pip install -e ".[docs,ocr,media]"
```

---

## Dependências externas (binários)

Alguns módulos dependem de ferramentas externas. O app **detecta e avisa** quando
faltam; ele nunca falha silenciosamente.

| Ferramenta | Usado por | Instalação sugerida (Windows) |
|---|---|---|
| **qpdf** | PDF Cleaner (fallback) | `winget install qpdf.qpdf` |
| **Tesseract** (+ idioma `por`) | OCR | `winget install UB-Mannheim.TesseractOCR` |
| **Ghostscript** | OCR | `winget install ArtifexSoftware.GhostScript` |
| **FFmpeg** | Transcrição áudio/vídeo | `winget install Gyan.FFmpeg` |
| **Calibre** | E-books (fallback) | `winget install calibre.calibre` |
| **Pandoc** | Conversões textuais | `winget install JohnMacFarlane.Pandoc` |

> Para OCR em português, instale também o pacote de idioma `por` do Tesseract
> (o instalador UB-Mannheim permite selecioná-lo durante a instalação).

---

## Como usar o PDF Cleaner

1. Clique em **Limpar PDF** na tela inicial (ou na barra lateral).
2. **Abra um PDF** (botão ou arraste o arquivo para a janela).
3. **Selecione páginas** clicando nas miniaturas, ou use **Selecionar intervalo…**
   (ex.: `1-5, 8, 10-12`).
4. Aplique operações: **Remover**, **Extrair**, **Girar**, **Juntar** outro PDF,
   **Dividir** por intervalos.
5. **Desfazer/Refazer** antes de salvar.
6. **Salvar como…** gera um **novo** PDF (o original nunca é alterado), junto de
   um `manifest.json` com o que foi mantido/removido.

---

## Como usar o OCR

1. Clique em **OCR** na tela inicial (ou na barra lateral).
2. **Abra um PDF escaneado ou uma imagem** (botão ou arraste o arquivo para a janela) —
   o app avisa se o PDF já parece ter texto nativo ou se faltam dependências.
3. Escolha **idioma**, **formato** (Markdown/TXT) e **preset** de exportação.
4. Ajuste as opções se necessário: **Corrigir inclinação**, **Corrigir rotação**,
   **Forçar OCR** (reprocessa páginas que já têm texto).
5. **Aplicar OCR e exportar…** gera um **PDF pesquisável** + o texto reconhecido em
   Markdown/TXT + `manifest.json`, numa pasta organizada (o original é preservado).

---

## Estrutura do projeto

```
app/
  main.py                 # ponto de entrada (python -m app.main)
  ui/                     # PySide6 — uma view por tarefa + componentes
  services/               # lógica sem Qt: pdf, render, manifest, markdown,
                          # export, epub, ocr, e stub de transcrição (Etapa 6)
  backends/
    documents/            # motores intercambiáveis: PyMuPDF4LLM (ativo) +
                          # Docling/MarkItDown/Marker/MinerU (interface fixada, Etapa 8)
    transcription/        # faster-whisper e whisper.cpp (interface fixada, Etapa 6)
  jobs/                   # execução em background (JobManager, workers, jobs de PDF)
  models/                 # dataclasses de domínio (extração, exportação, transcrição)
  infrastructure/         # paths, settings, logging, temp, dependências, histórico SQLite
  presets/                # NotebookLM, Obsidian, LLM genérico, Transcrição para IA
  tests/                  # pytest
scripts/
  setup_windows.ps1       # setup automatizado para Windows
```

---

## Privacidade e segurança

- **Nenhum** upload externo, sincronização em nuvem ou telemetria.
- Arquivos do usuário são tratados como **não confiáveis**: sem execução de
  macros ou JavaScript embutido, sem seguir links automaticamente.
- **Originais são preservados**; nunca sobrescrevemos sem confirmação.
- Temporários ficam em pasta controlada e são limpos automaticamente.
- Logs registram detalhes técnicos, mas **nunca** o conteúdo dos documentos.

---

## Desenvolvimento

```powershell
uv sync --extra dev
uv run pytest          # testes
uv run ruff check .    # lint
```

---

## Roadmap

- ✅ **Etapa 3–4** — Documento para IA (PDF/EPUB → Markdown/TXT, por capítulos, manifest).
- ✅ **Etapa 5** — OCR (OCRmyPDF + Tesseract, PDF pesquisável).
- **Etapa 6** — Transcrição (FFmpeg + faster-whisper, TXT/MD/JSON, timestamps).
- 🟡 **Etapa 7** — Presets (NotebookLM, Obsidian, LLM genérico já existem e são usados no
  Documento para IA e no OCR; falta o preset de Transcrição para IA, que depende da Etapa 6).
- **Etapa 8** — Backends opcionais (Docling, MarkItDown, Marker, MinerU) + seleção manual.
- **Etapa 9** — Lote e histórico.

---

## Licença

[Apache-2.0](LICENSE) © 2026 AI Knowledge Prep Suite contributors.
