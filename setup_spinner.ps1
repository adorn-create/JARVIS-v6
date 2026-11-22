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

$script:LandMasses = @(
    @{ Longitude = -108; Latitude = 43; Width = 48; Height = 31 },
    @{ Longitude = -82; Latitude = 12; Width = 20; Height = 19 },
    @{ Longitude = -60; Latitude = -18; Width = 25; Height = 42 },
    @{ Longitude = -43; Latitude = 73; Width = 17; Height = 14 },
    @{ Longitude = 26; Latitude = 53; Width = 39; Height = 22 },
    @{ Longitude = 20; Latitude = 5; Width = 34; Height = 49 },
    @{ Longitude = 77; Latitude = 47; Width = 76; Height = 31 },
    @{ Longitude = 108; Latitude = 13; Width = 31; Height = 22 },
    @{ Longitude = 135; Latitude = -25; Width = 22; Height = 17 },
    @{ Longitude = 0; Latitude = -81; Width = 150; Height = 8 }
)

function New-GlobeFrame {
    param([double]$Rotation)

    $radiusY = 9
    $radiusX = 18
    $rows = New-Object 'System.Collections.Generic.List[string]'
    for ($y = -$radiusY; $y -le $radiusY; $y++) {
        $ny = $y / [double]$radiusY
        $row = New-Object System.Text.StringBuilder
        for ($x = -$radiusX; $x -le $radiusX; $x++) {
            $nx = $x / [double]$radiusX
            $depthSquared = 1.0 - ($nx * $nx) - ($ny * $ny)
            if ($depthSquared -lt 0) {
                [void]$row.Append(" ")
                continue
            }

            $nz = [Math]::Sqrt($depthSquared)
            $latitude = [Math]::Asin($ny)
            $longitude = [Math]::Atan2($nx, $nz) + ($Rotation * [Math]::PI / 180.0)
            $latitudeDegrees = $latitude * 180.0 / [Math]::PI
            $longitudeDegrees = (($longitude * 180.0 / [Math]::PI) % 360.0)
            if ($longitudeDegrees -gt 180) { $longitudeDegrees -= 360 }
            if ($longitudeDegrees -lt -180) { $longitudeDegrees += 360 }

            $isLand = $false
            foreach ($mass in $script:LandMasses) {
                $longitudeDistance = [Math]::Abs($longitudeDegrees - $mass.Longitude)
                if ($longitudeDistance -gt 180) { $longitudeDistance = 360 - $longitudeDistance }
                $horizontal = $longitudeDistance / $mass.Width
                $vertical = ($latitudeDegrees - $mass.Latitude) / $mass.Height
                if (($horizontal * $horizontal) + ($vertical * $vertical) -le 1) {
                    $isLand = $true
                    break
                }
            }

            $illumination = (-0.45 * $nx) - (0.35 * $ny) + (0.8 * $nz)
            $latitudeLine = [Math]::Abs([Math]::Sin($latitude * 6.0)) -lt 0.09
            $longitudeLine = [Math]::Abs([Math]::Sin($longitude * 4.0)) -lt 0.07
            if ($nz -lt 0.16) {
                $character = "."
            } elseif ($latitudeLine -or $longitudeLine) {
                if ($illumination -gt 0.05) { $character = "+" } else { $character = ":" }
            } elseif ($isLand) {
                if ($illumination -gt 0.1) { $character = "#" } else { $character = "+" }
            } elseif ($illumination -gt 0.55) {
                $character = "."
            } elseif ($illumination -gt -0.15) {
                $character = ":"
            } else {
                $character = "'"
            }
            [void]$row.Append($character)
        }
        [void]$rows.Add("        " + $row.ToString())
    }

    return $rows
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
                $rotation = ($frameIndex * 6) % 360
                $lines = @(New-GlobeFrame -Rotation $rotation)
                foreach ($line in $lines) {
                    Write-Host $line.PadRight(60) -ForegroundColor Green
                }
                Write-Host ("  J.A.R.V.I.S. // LOCAL SETUP".PadRight(60)) -ForegroundColor DarkGreen
                Write-Host ("  STATUS: {0}".PadRight(60) -f $Label) -ForegroundColor Cyan
                Write-Host ("  OUTPUT HIDDEN // LOGS: logs\setup-{0}-*.log".PadRight(60)) -ForegroundColor DarkGray
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
