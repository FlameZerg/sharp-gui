param(
  [string]$Version = "",
  [string]$Manifest = "video-manifest.json",
  [string]$Source = "",
  [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

function Resolve-ProjectPath {
  param([string]$Path)

  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }

  return Join-Path $projectDir $Path
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

  $manifestData = Get-Content -Encoding UTF8 -Raw -Path $resolvedManifestPath | ConvertFrom-Json
  $resolvedVersion = $RequestedVersion
  if ([string]::IsNullOrWhiteSpace($resolvedVersion)) {
    $resolvedVersion = [string]$manifestData.currentVersion
  }

  if ([string]::IsNullOrWhiteSpace($resolvedVersion)) {
    throw "No version was provided and video manifest has no currentVersion."
  }

  $versionProperty = $manifestData.versions.PSObject.Properties | Where-Object { $_.Name -eq $resolvedVersion } | Select-Object -First 1
  if (-not $versionProperty) {
    throw "Version '$resolvedVersion' is not defined in $resolvedManifestPath"
  }

  return [pscustomobject]@{
    Name = $resolvedVersion
    Data = $versionProperty.Value
  }
}

function Format-CaptionTime {
  param(
    [double]$Seconds,
    [string]$Separator
  )

  if ($Seconds -lt 0) {
    throw "Caption time cannot be negative: $Seconds"
  }

  $totalMs = [int64][Math]::Round($Seconds * 1000)
  $hours = [int]($totalMs / 3600000)
  $minutes = [int](($totalMs % 3600000) / 60000)
  $secs = [int](($totalMs % 60000) / 1000)
  $millis = [int]($totalMs % 1000)

  return "{0:00}:{1:00}:{2:00}{3}{4:000}" -f $hours, $minutes, $secs, $Separator, $millis
}

$versionConfig = Get-VideoVersion -ManifestPath $Manifest -RequestedVersion $Version
if ([string]::IsNullOrWhiteSpace($Source)) {
  $Source = [string]$versionConfig.Data.captionSource
}

if ([string]::IsNullOrWhiteSpace($Source)) {
  throw "Version '$($versionConfig.Name)' has no captionSource in $Manifest."
}

if ([string]::IsNullOrWhiteSpace($OutputDir) -and $versionConfig.Data.captionOutputDir) {
  $OutputDir = [string]$versionConfig.Data.captionOutputDir
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = "captions"
}

Write-Host "Caption version: $($versionConfig.Name)"

$sourcePath = Resolve-ProjectPath $Source
$outputPath = Resolve-ProjectPath $OutputDir

if (-not (Test-Path $sourcePath)) {
  throw "Caption source not found: $sourcePath"
}

if (-not (Test-Path $outputPath)) {
  New-Item -ItemType Directory -Path $outputPath | Out-Null
}

$data = Get-Content -Encoding UTF8 -Raw -Path $sourcePath | ConvertFrom-Json
$captions = @($data.captions)
if ($captions.Count -eq 0) {
  throw "Caption source contains no captions: $sourcePath"
}

$outputBase = $data.outputBase
if (-not $outputBase) {
  $outputBase = [System.IO.Path]::GetFileNameWithoutExtension($sourcePath)
}

$srtLines = New-Object System.Collections.Generic.List[string]
$vttLines = New-Object System.Collections.Generic.List[string]
$vttLines.Add("WEBVTT")
$vttLines.Add("")

for ($i = 0; $i -lt $captions.Count; $i++) {
  $caption = $captions[$i]
  $start = [double]$caption.start
  $end = [double]$caption.end
  $text = [string]$caption.text

  if ($end -le $start) {
    throw "Caption $($i + 1) end must be after start."
  }

  if ([string]::IsNullOrWhiteSpace($text)) {
    throw "Caption $($i + 1) text is empty."
  }

  $srtLines.Add("$($i + 1)")
  $srtLines.Add("$(Format-CaptionTime $start ",") --> $(Format-CaptionTime $end ",")")
  $srtLines.Add($text)
  $srtLines.Add("")

  $vttLines.Add("$($i + 1)")
  $vttLines.Add("$(Format-CaptionTime $start ".") --> $(Format-CaptionTime $end ".")")
  $vttLines.Add($text)
  $vttLines.Add("")
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$srtPath = Join-Path $outputPath "$outputBase.srt"
$vttPath = Join-Path $outputPath "$outputBase.vtt"

[System.IO.File]::WriteAllText($srtPath, ($srtLines -join "`r`n"), $utf8NoBom)
[System.IO.File]::WriteAllText($vttPath, ($vttLines -join "`r`n"), $utf8NoBom)

Write-Host "Generated: $srtPath"
Write-Host "Generated: $vttPath"
