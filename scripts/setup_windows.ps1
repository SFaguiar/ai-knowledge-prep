# Setup do AI Knowledge Prep Suite no Windows (Secao 13).
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# Pode ser chamado de qualquer diretorio - sempre opera a partir da raiz do repo.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "== AI Knowledge Prep Suite - setup (Windows) ==" -ForegroundColor Cyan
Write-Host "Raiz do projeto: $RepoRoot"

# 1. Python 3.12+
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python nao encontrado. Instale com:" -ForegroundColor Red
    Write-Host "  winget install Python.Python.3.12"
    exit 1
}
$version = (python -c "import sys; print('{0}.{1}'.format(*sys.version_info[:2]))")
if ([version]$version -lt [version]"3.12") {
    Write-Host "Python $version encontrado; e necessario 3.12 ou superior." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python $version"

# 2. Ambiente: uv (preferido) ou venv + pip
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    Write-Host "[OK] uv encontrado - executando 'uv sync'..."
    uv sync
    Write-Host ""
    Write-Host "Pronto! Rode o app com:  uv run python -m app.main" -ForegroundColor Green
} else {
    Write-Host "uv nao encontrado - usando venv + pip."
    Write-Host "(para instalar o uv:  winget install astral-sh.uv)"
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -e .
    Write-Host ""
    Write-Host "Pronto! Rode o app com:  .\.venv\Scripts\python.exe -m app.main" -ForegroundColor Green
}

Write-Host ""
Write-Host "Depois de abrir, va em Configuracoes > Verificar dependencias."
Write-Host "Ferramentas externas opcionais (conforme o modulo que voce usar):"
Write-Host "  winget install qpdf.qpdf"
Write-Host "  winget install UB-Mannheim.TesseractOCR   (marque o idioma 'Portuguese')"
Write-Host "  winget install ArtifexSoftware.GhostScript"
Write-Host "  winget install Gyan.FFmpeg"
