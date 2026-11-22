param(
    [Parameter(Mandatory = $true)]
    [string]$Label,
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [Parameter(Mandatory = $true)]
    [string]$ArgumentLine,
    [Parameter(Mandatory = $true)]
    [string]$LogName
)

$ErrorActionPreference = "Stop"
$logDirectory = Join-Path (Get-Location).Path "logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$stdoutPath = Join-Path $logDirectory "setup-$LogName-stdout.log"
$stderrPath = Join-Path $logDirectory "setup-$LogName-stderr.log"

if (Test-Path $FilePath) {
    $resolvedFilePath = (Resolve-Path $FilePath).Path
} else {
    $resolvedFilePath = (Get-Command $FilePath -ErrorAction Stop).Source
}

$globeFramesPath = Join-Path $PSScriptRoot "setup_globe_frames.txt"
$globeData = [System.IO.File]::ReadAllText($globeFramesPath) -replace '(?:\r?\n)+$', ''
$script:GlobeFrames = @($globeData -split '(?:\r?\n){2,}')
if ($script:GlobeFrames.Count -ne 60) {
    throw "Expected 60 globe animation frames in $globeFramesPath."
}
foreach ($frame in $script:GlobeFrames) {
    $frameLines = $frame -split '\r?\n'
    if ($frameLines.Count -ne 27) {
        throw "Invalid globe animation frame in $globeFramesPath."
    }
    foreach ($line in $frameLines) {
        if ($line.Length -gt 64 -or $line -ne $line.TrimEnd()) {
            throw "Invalid globe animation frame width in $globeFramesPath."
        }
    }
}

$process = $null
try {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $resolvedFilePath
    $startInfo.Arguments = $ArgumentLine
    $startInfo.WorkingDirectory = (Get-Location).Path
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "The process did not start."
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $frameIndex = 0
    $showGlobe = -not [Console]::IsOutputRedirected
    $spinnerFrames = @("|", "/", "-", "\")
    while (-not $process.HasExited) {
        $process.Refresh()
        if ($showGlobe) {
            try {
                [Console]::SetCursorPosition(0, 0)
                $frame = $script:GlobeFrames[$frameIndex % $script:GlobeFrames.Count]
                $lines = $frame -split '\r?\n'
                foreach ($line in $lines) {
                    Write-Host ("    " + $line.PadRight(64)) -ForegroundColor Green
                }
                Write-Host ("  J.A.R.V.I.S. // STATUS: {0}".PadRight(68) -f $Label) -ForegroundColor Cyan
                Write-Host ("  OUTPUT HIDDEN // LOGS: logs\setup-$LogName-*.log".PadRight(68)) -ForegroundColor DarkGray
            } catch {
                $showGlobe = $false
            }
        }
        if (-not $showGlobe) {
            $spinner = $spinnerFrames[$frameIndex % $spinnerFrames.Count]
            Write-Host ("`r[{0}] {1}...".PadRight(60) -f $spinner, $Label) -NoNewline -ForegroundColor Green
        }
        Start-Sleep -Milliseconds 140
        $frameIndex++
    }

    $process.WaitForExit()
    $process.Refresh()
    $exitCode = $process.ExitCode
    [System.IO.File]::WriteAllText($stdoutPath, $stdoutTask.Result)
    [System.IO.File]::WriteAllText($stderrPath, $stderrTask.Result)
    if (-not $showGlobe) {
        Write-Host ""
    }
    if ($exitCode -ne 0) {
        Write-Host "[ERROR] $Label failed. Details are in $stdoutPath and $stderrPath." -ForegroundColor Red
        exit $exitCode
    }

    Write-Host "[OK] $Label" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "[ERROR] Could not run $Label`: $_" -ForegroundColor Red
    exit 1
} finally {
    if ($process) {
        $process.Dispose()
    }
}
