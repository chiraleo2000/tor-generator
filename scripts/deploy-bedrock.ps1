# Active deploy for this machine: Bedrock chat + local EmbeddingGemma.
# Always uses .env.bedrock. Do NOT pass .env / .env.local here.
# Usage (from repo root):
#   powershell -File scripts/deploy-bedrock.ps1
#   powershell -File scripts/deploy-bedrock.ps1 -Build

param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$EnvFile = Join-Path $RepoRoot ".env.bedrock"
if (-not (Test-Path $EnvFile)) {
    throw ".env.bedrock is required for active deploy (Bedrock chat)."
}

$llmLine = Select-String -Path $EnvFile -Pattern "^LLM_PROVIDER=" | Select-Object -First 1
if (-not $llmLine -or $llmLine.Line -notmatch "^LLM_PROVIDER=bedrock\s*$") {
    throw ".env.bedrock must set LLM_PROVIDER=bedrock (found: $($llmLine.Line))"
}

Write-Host "Deploying tor-app with --env-file .env.bedrock (LLM=bedrock)"
if ($Build) {
    docker compose -p tor-app --env-file .env.bedrock up -d --build --force-recreate backend frontend mcp-rag
} else {
    docker compose -p tor-app --env-file .env.bedrock up -d --force-recreate backend frontend mcp-rag
}
if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit $LASTEXITCODE"
}

$deadline = (Get-Date).AddMinutes(5)
do {
    $health = docker inspect tor-app-backend-1 --format "{{.State.Health.Status}}" 2>$null
    if ($health -eq "healthy") { break }
    if ((Get-Date) -gt $deadline) { throw "backend not healthy (status=$health)" }
    Start-Sleep -Seconds 3
} while ($true)

$probe = docker exec tor-app-backend-1 python -c "from app.config import get_settings; s=get_settings(); print(s.llm_provider); print(s.embedding_provider); print(s.pin_on_prem_llm)"
$lines = @($probe -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($lines.Count -lt 3) {
    throw "Could not read live provider settings: $probe"
}
if ($lines[0] -ne "bedrock") {
    throw "REFUSING: live LLM_PROVIDER=$($lines[0]) (expected bedrock)."
}
if ($lines[2] -ne "False" -and $lines[2] -ne "false") {
    throw "REFUSING: PIN_ON_PREM_LLM must be false for Bedrock chat (got $($lines[2]))"
}

Write-Host ("OK llm={0} embed={1} pin={2}" -f $lines[0], $lines[1], $lines[2])
Write-Host "UI http://localhost:3000 API http://localhost:4000/health"
