# Sync local dataset folder to S3 using app/infra/pn-ec2/.env
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
# $PSScriptRoot = .../pn-ec2/scripts → parent = pn-ec2
$PnRoot = Split-Path $PSScriptRoot -Parent
Set-Location $PnRoot
if (-not (Test-Path ".env")) { throw "Missing .env — copy .env.example first" }

Get-Content ".env" | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $pair = $_.Split("=", 2)
  if ($pair.Length -eq 2) {
    [Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), "Process")
  }
}

$Bucket = $env:PN_S3_BUCKET
$Prefix = if ($env:PN_S3_SOURCES_PREFIX) { $env:PN_S3_SOURCES_PREFIX } else { "rags/procurement-th/sources/" }
$Local = $env:PN_DATASET_LOCAL_PATH
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-southeast-1" }

if (-not $Bucket) { throw "PN_S3_BUCKET empty" }
if (-not $Local -or -not (Test-Path $Local)) { throw "Set PN_DATASET_LOCAL_PATH to an existing folder" }

Write-Host "Sync $Local -> s3://$Bucket/$Prefix"
aws s3 sync $Local "s3://$Bucket/$Prefix" --region $Region
Write-Host "Done."
