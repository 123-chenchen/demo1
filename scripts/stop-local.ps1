$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$stateDir = Join-Path $repoRoot ".local"
$pidFiles = @(
    (Join-Path $stateDir "frontend-local.pid"),
    (Join-Path $stateDir "backend-local.pid")
)

function Stop-ProcessTree {
    param([int]$RootProcessId)

    $children = Get-CimInstance Win32_Process |
        Where-Object { $_.ParentProcessId -eq $RootProcessId }

    foreach ($child in $children) {
        Stop-ProcessTree -RootProcessId $child.ProcessId
    }

    $process = Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $RootProcessId -Force
        Write-Host "Stopped process $RootProcessId"
    }
}

foreach ($pidFile in $pidFiles) {
    if (-not (Test-Path $pidFile)) {
        continue
    }

    $rawPid = Get-Content -Raw -Path $pidFile
    $processId = 0
    if (-not [int]::TryParse($rawPid.Trim(), [ref]$processId)) {
        Remove-Item -LiteralPath $pidFile -Force
        continue
    }

    Stop-ProcessTree -RootProcessId $processId

    Remove-Item -LiteralPath $pidFile -Force
}
