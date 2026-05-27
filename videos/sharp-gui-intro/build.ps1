param(
  [string]$Version = "",
  [string]$Manifest = "video-manifest.json",
  [string]$Output = "",
  [string]$VideoBitrate = "30M",
  [int]$Fps = 30,
  [switch]$CheckOnly,
  [switch]$SkipInspect,
  [switch]$CaptionsOnly
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

function Resolve-ProjectPath {
  param([string]$Path)

  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }

  return Join-Path $scriptDir $Path
}

function Get-VideoVersion {
  param(
    [string]$ManifestPath,
    [string]$RequestedVersion
  )

  $resolvedManifestPath = Resolve-ProjectPath $ManifestPath
  if (-not (Test-Path $resolvedManifestPath)) {
    throw "Video manifest not found: $resolvedManifestPath"
  }

  $data = Get-Content -Encoding UTF8 -Raw -Path $resolvedManifestPath | ConvertFrom-Json
  $resolvedVersion = $RequestedVersion
  if ([string]::IsNullOrWhiteSpace($resolvedVersion)) {
    $resolvedVersion = [string]$data.currentVersion
  }

  if ([string]::IsNullOrWhiteSpace($resolvedVersion)) {
    throw "No version was provided and video manifest has no currentVersion."
  }

  $versionProperty = $data.versions.PSObject.Properties | Where-Object { $_.Name -eq $resolvedVersion } | Select-Object -First 1
  if (-not $versionProperty) {
    throw "Version '$resolvedVersion' is not defined in $resolvedManifestPath"
  }

  return [pscustomobject]@{
    Name = $resolvedVersion
    Data = $versionProperty.Value
  }
}

$versionConfig = Get-VideoVersion -ManifestPath $Manifest -RequestedVersion $Version
$resolvedOutput = $Output
if ([string]::IsNullOrWhiteSpace($resolvedOutput)) {
  $resolvedOutput = [string]$versionConfig.Data.renderOutput
}

if ([string]::IsNullOrWhiteSpace($resolvedOutput)) {
  throw "Version '$($versionConfig.Name)' has no renderOutput in $Manifest."
}

Write-Host "Video version: $($versionConfig.Name)"

Invoke-Checked "powershell" @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  (Join-Path $scriptDir "scripts\generate-captions.ps1"),
  "-Version",
  $versionConfig.Name,
  "-Manifest",
  $Manifest
)

if ($CaptionsOnly) {
  Write-Host ""
  Write-Host "Captions generated."
  exit 0
}

$renderArgs = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  (Join-Path $scriptDir "render.ps1"),
  "-Version",
  $versionConfig.Name,
  "-Manifest",
  $Manifest,
  "-Output",
  $resolvedOutput,
  "-VideoBitrate",
  $VideoBitrate,
  "-Fps",
  "$Fps"
)

if ($CheckOnly) {
  $renderArgs += "-CheckOnly"
}

if ($SkipInspect) {
  $renderArgs += "-SkipInspect"
}

Invoke-Checked "powershell" $renderArgs
