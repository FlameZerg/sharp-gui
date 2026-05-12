param(
  [string]$Output = "renders/sharp-gui-intro-current-hq-1080p.mp4",
  [string]$VideoBitrate = "30M",
  [int]$Fps = 30,
  [switch]$CheckOnly,
  [switch]$SkipInspect
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Invoke-Checked {
  param(
    [string]$Command,
    [string[]]$Arguments
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$Command $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
  }
}

$chromePath = Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"
if (-not $env:HYPERFRAMES_BROWSER_PATH -and (Test-Path $chromePath)) {
  $env:HYPERFRAMES_BROWSER_PATH = $chromePath
}

if (-not (Test-Path "node_modules\.bin\hyperframes.cmd")) {
  Invoke-Checked "npm" @("install")
}

if (-not (Test-Path "renders")) {
  New-Item -ItemType Directory -Path "renders" | Out-Null
}

Invoke-Checked "npx" @("hyperframes", "lint")

if (-not $SkipInspect) {
  Invoke-Checked "npx" @("hyperframes", "inspect", "--samples", "18")
}

if ($CheckOnly) {
  Write-Host ""
  Write-Host "Checks passed."
  exit 0
}

Invoke-Checked "npx" @("hyperframes", "render", "--output", $Output, "--quality", "high", "--fps", "$Fps", "--video-bitrate", $VideoBitrate, "--strict")

Write-Host ""
Write-Host "Rendered: $((Resolve-Path $Output).Path)"
