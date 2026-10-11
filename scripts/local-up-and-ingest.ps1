# Local Compose only. Builds and starts docker-compose.yml with .env.local,
# waits until services are healthy, confirms the backend can reach LM Studio,
# then uploads new PDFs from this host. Does not delete volumes, does not call
# app/infra/pn-ec2/scripts/deploy.sh, and does not target EC2.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot "docker-compose.yml"))) {
    throw "docker-compose.yml not found at $RepoRoot"
}
if (-not (Test-Path (Join-Path $RepoRoot ".env.local"))) {
    throw ".env.local is required and is not committed"
}

Write-Host "Starting local Compose (no volume delete)"
docker compose -p tor-app --env-file .env.local up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed with exit $LASTEXITCODE"
}

function Get-ComposeRows {
    $lines = docker compose -p tor-app --env-file .env.local ps --format "{{.Service}}|{{.State}}|{{.Health}}"
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose ps failed"
    }
    $rows = @()
    foreach ($line in @($lines)) {
        if (-not $line) { continue }
        $parts = $line.Split("|")
        if ($parts.Count -lt 3) { continue }
        $rows += [pscustomobject]@{
            Service = $parts[0]
            State   = $parts[1]
            Health  = $parts[2]
        }
    }
    return $rows
}

$requiredHealthy = @(
    "postgres", "redis", "minio", "mongo", "neo4j", "mcp-rag", "backend", "frontend"
)
$deadline = (Get-Date).AddMinutes(45)
do {
    $rows = @(Get-ComposeRows)
    $byName = @{}
    foreach ($row in $rows) { $byName[$row.Service] = $row }
    $pending = @()
    foreach ($name in $requiredHealthy) {
        $row = $byName[$name]
        if ($null -eq $row) {
            $pending += "$name missing"
            continue
        }
        if ($row.State -match "exited|dead") {
            throw "Service $name is $($row.State)"
        }
        if ($row.Health -ne "healthy") {
            $pending += "$name $($row.State) $($row.Health)"
        }
    }
    if ($pending.Count -eq 0) {
        Write-Host "Services healthy"
        break
    }
    Write-Host ("Waiting: " + ($pending -join ", "))
    if ((Get-Date) -gt $deadline) {
        throw "Timed out waiting for healthy services"
    }
    Start-Sleep -Seconds 8
} while ($true)

Write-Host "Checking LM Studio from the backend container"
docker compose -p tor-app --env-file .env.local exec -T backend python -c "import os,urllib.request; base=os.environ.get('LM_STUDIO_BASE_URL','').rstrip('/'); resp=urllib.request.urlopen(base+'/models', timeout=20); print('lm_studio_http', resp.status)"
if ($LASTEXITCODE -ne 0) {
    throw "Backend cannot reach LM Studio. Ingest was not started."
}

Write-Host "Uploading RAG from the host (additive, no wipe)"
Get-Content (Join-Path $RepoRoot ".env.local") | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $splitAt = $line.IndexOf("=")
    $name = $line.Substring(0, $splitAt).Trim()
    $value = $line.Substring($splitAt + 1)
    if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    Set-Item -Path "Env:$name" -Value $value
}
$env:POSTGRES_HOST = "127.0.0.1"
$env:REDIS_HOST = "127.0.0.1"
$env:MONGO_URI = "mongodb://127.0.0.1:27017"
$env:NEO4J_URI = "bolt://127.0.0.1:7687"
$env:LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
$env:LOCAL_EMBEDDING_BASE_URL = "http://127.0.0.1:1234/v1"
$env:PYTHONPATH = Join-Path $RepoRoot "app\backend"
$env:PYTHONIOENCODING = "utf-8"

python (Join-Path $RepoRoot "app\backend\scripts\ingest_local_additions.py")
if ($LASTEXITCODE -ne 0) {
    throw "Host ingest failed with exit $LASTEXITCODE"
}
Write-Host "Local stack is up and RAG upload finished"
