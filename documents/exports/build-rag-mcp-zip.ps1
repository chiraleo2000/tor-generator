# Build tor-rag-mcp-dataset zip (wrapper). Prefer the Python builder on Windows.
param(
    [string]$Version = "0.4.0"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
python documents/exports/build_rag_mcp_zip.py --version $Version
