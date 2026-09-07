# Serial local verification gate for TOR Compose.
# Rule: STOP all tests before any Docker rebuild/redeploy. Wait healthy. Check tools
# in order. Run ONE pytest/Playwright suite at a time (local runs are slow/unstable).
#
# Usage (from repo root):
#   powershell -File app/scripts/serial-verify.ps1 stop
#   docker compose -p tor-app --env-file .env --profile mcp-stub up -d --build
#   powershell -File app/scripts/serial-verify.ps1 health
#   powershell -File app/scripts/serial-verify.ps1 tools
#   powershell -File app/scripts/serial-verify.ps1 coverage
#   powershell -File app/scripts/serial-verify.ps1 live
#   powershell -File app/scripts/serial-verify.ps1 e2e

param(
    [Parameter(Position = 0)]
    [ValidateSet("stop", "health", "tools", "coverage", "live", "e2e")]
    [string]$Phase = "health"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $RepoRoot "docker-compose.yml"))) {
    $RepoRoot = (Get-Location).Path
}

function Clear-ConflictingColorEnv {
    if ($env:FORCE_COLOR -and $env:NO_COLOR) {
        Remove-Item Env:NO_COLOR -ErrorAction SilentlyContinue
    }
}

function Stop-TorTests {
    Write-Host "STOP: cancelling pytest / Playwright / coverage jobs (not Docker)."
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match "python|pytest|node" -and
            $_.CommandLine -and
            (
                $_.CommandLine -match "pytest" -or
                $_.CommandLine -match "playwright" -or
                $_.CommandLine -match "test:e2e" -or
                $_.CommandLine -match "run-playwright" -or
                $_.CommandLine -match "open-test-ui" -or
                $_.CommandLine -match "playwright-browsers" -or
                $_.CommandLine -match "vitest"
            )
        } |
        ForEach-Object {
            Write-Host ("  stopping pid {0}" -f $_.ProcessId)
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 180) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                Write-Host ("OK {0}" -f $Url)
                return
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    throw "Timed out waiting for $Url"
}

function Get-HealthJson {
    $raw = (Invoke-WebRequest -Uri "http://localhost:4000/health" -UseBasicParsing -TimeoutSec 15).Content
    return $raw | ConvertFrom-Json
}

switch ($Phase) {
    "stop" {
        Stop-TorTests
        break
    }
    "health" {
        Write-Host "Waiting Compose health (serial)..."
        Wait-HttpOk "http://localhost:4000/health" 240
        $health = Get-HealthJson
        foreach ($name in @("postgres", "redis", "minio", "mongo", "neo4j")) {
            $status = $health.services.$name
            if ($status -and $status -ne "up") {
                throw "health.$name=$status"
            }
            Write-Host ("  {0}=up" -f $name)
        }
        Wait-HttpOk "http://localhost:3000" 180
        break
    }
    "tools" {
        Write-Host "Tool check in order: backend health, frontend, PageIndex, MCP stub"
        $health = Get-HealthJson
        if (-not $health) { throw "backend /health missing" }
        Wait-HttpOk "http://localhost:3000" 30
        $pageindexUrls = @(
            "http://127.0.0.1:8000/health",
            "http://127.0.0.1:8000/api/search",
            "http://127.0.0.1:8100/health",
            "http://127.0.0.1:8100/api/search"
        )
        $pageindexOk = $false
        foreach ($url in $pageindexUrls) {
            try {
                Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 5 | Out-Null
                Write-Host ("OK PageIndex GET {0}" -f $url)
                $pageindexOk = $true
                break
            } catch {
                try {
                    Invoke-WebRequest -Uri $url -Method POST -UseBasicParsing -TimeoutSec 5 `
                        -ContentType "application/json" -Body '{"query":"ping","top_k":1}' | Out-Null
                    Write-Host ("OK PageIndex POST {0}" -f $url)
                    $pageindexOk = $true
                    break
                } catch { }
            }
        }
        if (-not $pageindexOk) {
            Write-Warning "PageIndex not reachable on host :8000/:8100 — Custom RAG will fail-open until it is up."
        }
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
            Write-Host "OK MCP stub :8765"
        } catch {
            Write-Warning "MCP stub :8765 down — start with: docker compose -p tor-app --profile mcp-stub up -d"
        }
        break
    }
    "coverage" {
        Stop-TorTests
        Set-Location (Join-Path $RepoRoot "app\backend")
        python -m pytest --cov=app --cov-report=term-missing -v -m "not live_llm"
        break
    }
    "live" {
        Stop-TorTests
        Set-Location (Join-Path $RepoRoot "app\backend")
        python -m pytest tests/test_live_realistic_workflow.py -v -s
        break
    }
    "e2e" {
        Stop-TorTests
        Clear-ConflictingColorEnv
        Set-Location (Join-Path $RepoRoot "app\frontend")
        node .\scripts\open-test-ui.mjs
        npm run test:e2e:headed
        break
    }
}
