param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipInstall,
    [switch]$SkipMigrations,
    [switch]$SkipDependencyCheck,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$stateDir = Join-Path $repoRoot ".local"
$logDir = Join-Path $repoRoot ".local\logs"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-HttpService {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Get -TimeoutSec 3 | Out-Null
        Write-Host "[ok] $Name reachable at $Url"
    }
    catch {
        Write-Host "[warn] $Name is not reachable at $Url"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required to run the backend locally."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required to run the frontend locally."
}

Write-Host "Checking local service dependencies. This script does not start Docker."
Test-HttpService -Name "Qdrant" -Url "http://127.0.0.1:6333"
Test-HttpService -Name "MinIO" -Url "http://127.0.0.1:9000/minio/health/live"
Test-HttpService -Name "Ollama" -Url "http://127.0.0.1:11434/api/tags"

$backendArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-backend-local.ps1"),
    "-Port", "$BackendPort"
)

if ($SkipInstall) {
    $backendArgs += "-SkipInstall"
}
if ($SkipMigrations) {
    $backendArgs += "-SkipMigrations"
}
if ($SkipDependencyCheck) {
    $backendArgs += "-SkipDependencyCheck"
}
if ($NoReload) {
    $backendArgs += "-NoReload"
}

$frontendArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-frontend-local.ps1"),
    "-Port", "$FrontendPort",
    "-ApiProxyTarget", "http://127.0.0.1:$BackendPort"
)

if ($SkipInstall) {
    $frontendArgs += "-SkipInstall"
}

$backendLog = Join-Path $logDir "backend-local.log"
$backendErrorLog = Join-Path $logDir "backend-local.err.log"
$frontendLog = Join-Path $logDir "frontend-local.log"
$frontendErrorLog = Join-Path $logDir "frontend-local.err.log"

$backendProcess = Start-Process powershell.exe `
    -ArgumentList $backendArgs `
    -PassThru `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrorLog `
    -WindowStyle Hidden

Start-Sleep -Seconds 3

$frontendProcess = Start-Process powershell.exe `
    -ArgumentList $frontendArgs `
    -PassThru `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrorLog `
    -WindowStyle Hidden

$backendProcess.Id | Set-Content -NoNewline -Path (Join-Path $stateDir "backend-local.pid")
$frontendProcess.Id | Set-Content -NoNewline -Path (Join-Path $stateDir "frontend-local.pid")

Write-Host "Local project processes started."
Write-Host "Backend PID:  $($backendProcess.Id)"
Write-Host "Frontend PID: $($frontendProcess.Id)"
Write-Host "Backend URL:  http://127.0.0.1:$BackendPort"
Write-Host "Frontend URL: http://127.0.0.1:$FrontendPort"
Write-Host "Backend log:  $backendLog"
Write-Host "Frontend log: $frontendLog"
Write-Host "Stop with: .\scripts\stop-local.ps1"
