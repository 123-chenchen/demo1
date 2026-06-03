param(
    [int]$Port = 8000,
    [switch]$SkipInstall,
    [switch]$SkipMigrations,
    [switch]$SkipDependencyCheck,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required to run the backend locally. Install uv, then rerun this script."
}

function Test-TcpPort {
    param(
        [string]$Name,
        [string]$HostName,
        [int]$Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(3000, $false)) {
            throw "$Name is not reachable at ${HostName}:${Port}."
        }
        try {
            $client.EndConnect($connect)
        }
        catch {
            throw "$Name is not reachable at ${HostName}:${Port}."
        }
    }
    finally {
        $client.Close()
    }
}

function Test-HttpUrl {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Get -TimeoutSec 3 | Out-Null
    }
    catch {
        throw "$Name is not reachable at $Url."
    }
}

Push-Location $backendDir
try {
    if (-not $SkipDependencyCheck) {
        Test-TcpPort -Name "PostgreSQL" -HostName "127.0.0.1" -Port 5432
        Test-HttpUrl -Name "Qdrant" -Url "http://127.0.0.1:6333"
        Test-HttpUrl -Name "MinIO" -Url "http://127.0.0.1:9000/minio/health/live"
        Test-HttpUrl -Name "Ollama" -Url "http://127.0.0.1:11434/api/tags"
    }

    if (-not $SkipInstall) {
        uv sync
    }

    if (-not $SkipMigrations) {
        uv run alembic upgrade head
    }

    $env:API_PORT = "$Port"
    $reloadArg = if ($NoReload) { @() } else { @("--reload") }
    uv run uvicorn app.main:app --host 0.0.0.0 --port $Port @reloadArg
}
finally {
    Pop-Location
}
