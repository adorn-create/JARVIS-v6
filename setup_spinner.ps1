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

$frames = @(
@'
               .-""""""""-.
            .-'  .--.  .--. '-.
          .'    / ## \/ ## \    '.
         /     |  ###  ###  |     \
        ;      |  ## /\ ##  |      ;
        |       \__//  \\__/       |
        ;       /  \    /  \       ;
         \     | ###\__/### |     /
          '.    \  ##    ## /    .'
            '-.  '--------'  .-'
               '-.________.-'
'@,
@'
               .-""""""""-.
            .-' .--.   .--. '-.
          .'   / ## \ / ## \   '.
         /    | ###  X  ### |    \
        ;     | ##  / \  ## |     ;
        |      \___/   \___/      |
        ;      /  \     /  \      ;
         \    | ### \_/ ### |    /
          '.   \ ##     ## /   .'
            '-. '---------' .-'
               '-.________.-'
'@,
@'
               .-""""""""-.
            .-'  .--.  .--. '-.
          .'    / ## \/ ## \    '.
         /     | ###  ###  |     \
        ;      | ## \  / ## |      ;
        |      | ##  \/  ## |      |
        ;      | ###    ### |      ;
         \      \ ##    ## /      /
          '.     '------'      .'
            '-.    ____    .-'
               '-.______.-'
'@,
@'
               .-""""""""-.
            .-' .--.   .--. '-.
          .'   / ## \ / ## \   '.
         /    | ###  X  ### |    \
        ;     | ##  / \  ## |     ;
        |      \__/   \__/       |
        ;      /  \   /  \       ;
         \    | ### \_/ ### |    /
          '.   \ ##     ## /   .'
            '-. '---------' .-'
               '-.________.-'
'@
)

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
                $lines = @($frames[$frameIndex % $frames.Count] -split "`r?`n" | Where-Object { $_ })
                foreach ($line in $lines) {
                    Write-Host $line.PadRight(72) -ForegroundColor Green
                }
                Write-Host ("  J.A.R.V.I.S. // LOCAL SETUP".PadRight(72)) -ForegroundColor DarkGreen
                Write-Host ("  STATUS: {0}".PadRight(72) -f $Label) -ForegroundColor Cyan
                Write-Host ("  OUTPUT HIDDEN // LOGS: logs\setup-{0}-*.log".PadRight(72)) -ForegroundColor DarkGray
            } catch {
                $showGlobe = $false
            }
        }
        if (-not $showGlobe) {
            $spinner = $spinnerFrames[$frameIndex % $spinnerFrames.Count]
            Write-Host ("`r[{0}] {1}...".PadRight(72) -f $spinner, $Label) -NoNewline -ForegroundColor Green
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
