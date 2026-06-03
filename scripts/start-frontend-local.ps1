param(
    [int]$Port = 5173,
    [string]$ApiProxyTarget = "http://127.0.0.1:8000",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $repoRoot "frontend"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required to run the frontend locally. Install Node.js/npm, then rerun this script."
}

Push-Location $frontendDir
try {
    if ((-not $SkipInstall) -and (-not (Test-Path "node_modules"))) {
        npm ci
    }

    $env:VITE_API_PROXY_TARGET = $ApiProxyTarget
    npm run dev -- --port $Port
}
finally {
    Pop-Location
}
