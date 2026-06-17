# P6B - Docling Environment Setup
# Creates an isolated venv for Docling investigation
# Run this once before running run_docling_hdfc.py

$ErrorActionPreference = "Stop"
$VENV_DIR = "Z:\CA\investigations\DOCLING\docling_env"

Write-Host "=== P6B Docling Environment Setup ===" -ForegroundColor Cyan
Write-Host "Creating venv at: $VENV_DIR"

# Use Python 3.14 (main env) - Docling supports 3.14 since 2.59.0
python -m venv $VENV_DIR

Write-Host "Installing Docling (this may take several minutes)..." -ForegroundColor Yellow
& "$VENV_DIR\Scripts\pip" install --upgrade pip
& "$VENV_DIR\Scripts\pip" install "docling>=2.59.0" pymupdf pdfplumber

Write-Host ""
Write-Host "=== Docling environment ready ===" -ForegroundColor Green
Write-Host "Run the investigation with:"
Write-Host "  & '$VENV_DIR\Scripts\python' Z:\CA\investigations\DOCLING\run_docling_hdfc.py"
