param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

$Command = $Command.ToLowerInvariant()
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$BackendLogDir = Join-Path $BackendDir "logs"
$FrontendLogDir = Join-Path $FrontendDir "logs"

$BackendPidFile = Join-Path $BackendLogDir "backend.pid"
$FrontendPidFile = Join-Path $FrontendLogDir "frontend.pid"

function Show-Usage {
    Write-Host "Usage: app.cmd <start|start-backend|stop|status|restart>"
}

function Get-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$DefaultValue
    )
    if (-not (Test-Path $Path)) { return $DefaultValue }
    $pattern = "^\s*$Key\s*=\s*(.*)\s*$"
    foreach ($line in Get-Content $Path) {
        $trim = $line.Trim()
        if ($trim -eq "" -or $trim.StartsWith("#")) { continue }
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) {
            $value = $match.Groups[1].Value.Trim()
            if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                return $value.Trim('"')
            }
            if ($value.StartsWith("'") -and $value.EndsWith("'")) {
                return $value.Trim("'")
            }
            return $value
        }
    }
    return $DefaultValue
}

function Get-PortPid {
    param([int]$Port)
    $lines = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
    foreach ($line in $lines) {
        $text = $line.ToString()
        if ($text -match "\s+LISTENING\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    return $null
}

function Wait-ForPort {
    param(
        [int]$Port,
        [int]$TimeoutSec
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Get-PortPid $Port) { return $true }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Read-Pid {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) { return $null }
    $line = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $line) { return $null }
    $raw = $line.Trim()
    if ($raw -match "^\d+$") { return [int]$raw }
    return $null
}

function Stop-ByPidFile {
    param(
        [string]$PidFile,
        [string]$Name
    )
    $procId = Read-Pid $PidFile
    if (-not $procId) {
        if (Test-Path $PidFile) { Remove-Item $PidFile -ErrorAction SilentlyContinue }
        Write-Host "$Name not running (pid file missing or invalid)."
        return
    }
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
        $stopped = $false
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            $stopped = $true
        } catch {
            $stopped = $false
        }

        if (-not $stopped) {
            & taskkill /PID $procId /T /F 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $stopped = $true }
        }

        Start-Sleep -Milliseconds 400
        if ($stopped) {
            Write-Host "$Name stopped (PID $procId)."
        } else {
            Write-Host "$Name failed to stop (PID $procId). Try running in an elevated shell."
        }
    } else {
        Write-Host "$Name process not found for PID $procId. Removing pid file."
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

function Start-Backend {
    $pythonPath = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        Write-Host "Backend python not found: $pythonPath"
        return $false
    }

    $envPath = Join-Path $BackendDir ".env"
    $backendHost = Get-DotEnvValue $envPath "APP_HOST" "127.0.0.1"
    $backendPort = [int](Get-DotEnvValue $envPath "APP_PORT" "8001")

    $existingPid = Get-PortPid $backendPort
    if ($existingPid) {
        Write-Host "Backend port $backendPort already in use by PID $existingPid."
        return $false
    }

    New-Item -ItemType Directory -Force $BackendLogDir | Out-Null
    $outLog = Join-Path $BackendLogDir "backend.out.log"
    $errLog = Join-Path $BackendLogDir "backend.err.log"

    $proc = Start-Process -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $backendHost, "--port", $backendPort) `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru `
        -WindowStyle Hidden

    Set-Content -Path $BackendPidFile -Value $proc.Id -Encoding ascii

    if (-not (Wait-ForPort $backendPort 6)) {
        Write-Host "Backend failed to start. Check logs:"
        Write-Host "  $errLog"
        return $false
    }

    Write-Host "Backend started on http://$backendHost`:$backendPort (PID $($proc.Id))."
    return $true
}

function Start-Frontend {
    $npmCmd = (Get-Command npm -ErrorAction SilentlyContinue).Source
    if (-not $npmCmd) {
        Write-Host "npm not found in PATH. Please install Node.js and npm."
        return $false
    }

    $envPath = Join-Path $FrontendDir ".env"
    $frontendHost = "127.0.0.1"
    $frontendPort = [int](Get-DotEnvValue $envPath "VITE_DEV_PORT" "5173")

    $existingPid = Get-PortPid $frontendPort
    if ($existingPid) {
        Write-Host "Frontend port $frontendPort already in use by PID $existingPid."
        return $false
    }

    New-Item -ItemType Directory -Force $FrontendLogDir | Out-Null
    $outLog = Join-Path $FrontendLogDir "frontend.out.log"
    $errLog = Join-Path $FrontendLogDir "frontend.err.log"

    $cmdExe = $env:ComSpec
    $proc = Start-Process -FilePath $cmdExe `
        -ArgumentList @("/c", "`"$npmCmd`"", "run", "dev", "--", "--host", $frontendHost, "--port", $frontendPort) `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru `
        -WindowStyle Hidden

    Set-Content -Path $FrontendPidFile -Value $proc.Id -Encoding ascii

    if (-not (Wait-ForPort $frontendPort 8)) {
        Write-Host "Frontend failed to start. Check logs:"
        Write-Host "  $errLog"
        Write-Host "If you see 'spawn EPERM', try running in an elevated shell or adjust system policies."
        return $false
    }

    Write-Host "Frontend started on http://$frontendHost`:$frontendPort (PID $($proc.Id))."
    return $true
}

function Show-Status {
    $envPathBackend = Join-Path $BackendDir ".env"
    $backendHost = Get-DotEnvValue $envPathBackend "APP_HOST" "127.0.0.1"
    $backendPort = [int](Get-DotEnvValue $envPathBackend "APP_PORT" "8001")
    $backendPid = Read-Pid $BackendPidFile
    $backendPortPid = Get-PortPid $backendPort

    $envPathFrontend = Join-Path $FrontendDir ".env"
    $frontendHost = "127.0.0.1"
    $frontendPort = [int](Get-DotEnvValue $envPathFrontend "VITE_DEV_PORT" "5173")
    $frontendPid = Read-Pid $FrontendPidFile
    $frontendPortPid = Get-PortPid $frontendPort

    if ($backendPid -and $backendPortPid) {
        Write-Host "Backend: RUNNING (PID file $backendPid, listening PID $backendPortPid) at http://$backendHost`:$backendPort"
    } else {
        Write-Host "Backend: STOPPED"
    }

    if ($frontendPid -and $frontendPortPid) {
        Write-Host "Frontend: RUNNING (PID file $frontendPid, listening PID $frontendPortPid) at http://$frontendHost`:$frontendPort"
    } else {
        Write-Host "Frontend: STOPPED"
    }
}

switch ($Command) {
    "start" {
        $okBackend = Start-Backend
        if (-not $okBackend) { exit 1 }
        $okFrontend = Start-Frontend
        if (-not $okFrontend) {
            Stop-ByPidFile $BackendPidFile "Backend"
            exit 1
        }
        exit 0
    }
    "start-backend" {
        $okBackend = Start-Backend
        if (-not $okBackend) { exit 1 }
        exit 0
    }
    "stop" {
        Stop-ByPidFile $FrontendPidFile "Frontend"
        Stop-ByPidFile $BackendPidFile "Backend"
        exit 0
    }
    "status" {
        Show-Status
        exit 0
    }
    "restart" {
        Stop-ByPidFile $FrontendPidFile "Frontend"
        Stop-ByPidFile $BackendPidFile "Backend"
        $okBackend = Start-Backend
        if (-not $okBackend) { exit 1 }
        $okFrontend = Start-Frontend
        if (-not $okFrontend) {
            Stop-ByPidFile $BackendPidFile "Backend"
            exit 1
        }
        exit 0
    }
    "help" { Show-Usage; exit 0 }
    "-h" { Show-Usage; exit 0 }
    "--help" { Show-Usage; exit 0 }
    default { Show-Usage; exit 1 }
}
