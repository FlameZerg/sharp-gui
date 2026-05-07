param(
    [string]$Version = "",
    [string]$OutputDir = "",
    [int]$CompressionLevel = 1,
    [switch]$PlanOnly,
    [switch]$AllowLocalVersion,
    [switch]$CleanBuildVenvs,
    [switch]$CleanOldArtifacts,
    [switch]$SkipArchiveTest,
    [switch]$SkipCu126,
    [switch]$SkipCu128
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message"
}

function Fail {
    param([string]$Message)
    Write-Host "[错误] $Message" -ForegroundColor Red
    exit 1
}

function Resolve-SevenZip {
    $cmd = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "$env:ProgramFiles\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Invoke-CommandChecked {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    Write-Step $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Fail "$Description 失败，退出码 $LASTEXITCODE"
    }
}

function Get-ReleaseVersion {
    param([string]$Root, [string]$RequestedVersion)

    if (-not [string]::IsNullOrWhiteSpace($RequestedVersion)) {
        return ($RequestedVersion.Trim() -replace "^refs/tags/", "")
    }

    $versionFile = Join-Path $Root "version.txt"
    if (Test-Path -LiteralPath $versionFile) {
        $fromFile = (Get-Content -LiteralPath $versionFile -Encoding UTF8 | Select-Object -First 1).Trim()
        if (-not [string]::IsNullOrWhiteSpace($fromFile)) {
            return $fromFile
        }
    }

    try {
        $tag = (& git -C $Root describe --tags --exact-match 2>$null).Trim()
        if (-not [string]::IsNullOrWhiteSpace($tag)) {
            return ($tag -replace "^refs/tags/", "")
        }
    } catch {
    }

    try {
        $tag = (& git -C $Root describe --tags --abbrev=0 2>$null).Trim()
        if (-not [string]::IsNullOrWhiteSpace($tag)) {
            return ($tag -replace "^refs/tags/", "")
        }
    } catch {
    }

    return "local-" + (Get-Date -Format "yyyyMMdd-HHmm")
}

function Test-VersionIsReleaseLike {
    param([string]$Version)
    return $Version -match '^v\d+\.\d+\.\d+([.-](rc|alpha|beta|preview)\.?\d*)?$'
}

function Test-PythonCuda {
    param([string]$PythonExe)

    $code = @'
import json
import sys
import warnings

try:
    warnings.filterwarnings("ignore")
    import torch
    payload = {
        "ok": True,
        "torch": getattr(torch, "__version__", ""),
        "cuda": getattr(getattr(torch, "version", None), "cuda", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
        "arch_list": list(torch.cuda.get_arch_list()),
    }
    print(json.dumps(payload, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
    sys.exit(2)
'@

    $tmp = Join-Path $env:TEMP ("sharp-release-cuda-{0}.py" -f ([guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $tmp -Encoding UTF8 -Value $code
    try {
        $raw = & $PythonExe $tmp
        if ($LASTEXITCODE -ne 0) {
            Fail "无法读取 PyTorch/CUDA 信息: $raw"
        }
        return $raw | ConvertFrom-Json
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Ensure-Cu126Venv {
    param(
        [string]$Root,
        [string]$BasePython
    )

    $venv = Join-Path $Root ".portable-venvs\cu126"
    $python = Join-Path $venv "Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $python)) {
        Write-Step "创建 cu126 打包虚拟环境"
        & $BasePython -m venv $venv | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Fail "创建 cu126 虚拟环境失败"
        }
    }

    Write-Step "准备 cu126 打包依赖"
    & $python -m pip install --upgrade pip | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail "升级 cu126 pip 失败"
    }

    Push-Location (Join-Path $Root "ml-sharp")
    try {
        & $python -m pip install -r requirements.txt | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Fail "安装 ml-sharp requirements 到 cu126 环境失败"
        }
    } finally {
        Pop-Location
    }

    & $python -m pip install flask | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail "安装 Flask 到 cu126 环境失败"
    }

    & $python -m pip install --force-reinstall --no-deps torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu126 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail "安装 cu126 PyTorch 失败"
    }

    $info = Test-PythonCuda -PythonExe $python
    if (-not $info.ok) {
        Fail "cu126 PyTorch 导入失败: $($info.error)"
    }

    Write-Info "cu126 环境: torch=$($info.torch), cuda=$($info.cuda), device=$($info.device)"
    return $venv
}

function Invoke-PackageBuild {
    param(
        [string]$Root,
        [string]$Version,
        [string]$Target,
        [string]$VenvDir,
        [string]$OutputDir,
        [int]$CompressionLevel,
        [bool]$SkipFrontendBuild,
        [bool]$PlanOnly
    )

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $Root "tools\build_portable_package.ps1"),
        "-Version", $Version,
        "-Target", $Target,
        "-VenvDir", $VenvDir,
        "-OutputDir", $OutputDir,
        "-CompressionLevel", $CompressionLevel
    )

    if ($SkipFrontendBuild) {
        $args += "-SkipFrontendBuild"
    }
    if ($PlanOnly) {
        $args += "-PlanOnly"
    }

    & powershell @args
    if ($LASTEXITCODE -ne 0) {
        Fail "打包 $Target 失败"
    }
}

function Test-Archive {
    param([string]$SevenZip, [string]$ZipPath)

    Write-Step "测试 ZIP 完整性: $(Split-Path -Leaf $ZipPath)"
    & $SevenZip t $ZipPath
    if ($LASTEXITCODE -ne 0) {
        Fail "ZIP 完整性测试失败: $ZipPath"
    }
}

function Write-ReleaseTemplate {
    param(
        [string]$OutputDir,
        [string]$Version,
        [object[]]$Packages
    )

    $template = Join-Path $OutputDir "portable-release-template-$Version.md"
    $lines = New-Object System.Collections.Generic.List[string]

    $lines.Add("## Windows 完整便携包下载")
    $lines.Add("")
    $lines.Add("下载：[点击打开网盘文件夹](待填写网盘链接)")
    $lines.Add("")
    $lines.Add("网盘文件夹内包含 RTX 50 和主流 NVIDIA 两个完整包，请按显卡选择：")
    $lines.Add("")
    $lines.Add("| 适用显卡 | 下载文件 | SHA256 |")
    $lines.Add("|---|---|---|")

    $orderedPackages = $Packages | Sort-Object @{
        Expression = {
            if ($_.Target -eq "cu128-rtx50") { 0 } else { 1 }
        }
    }, Target

    foreach ($pkg in $orderedPackages) {
        if ($pkg.Target -eq "cu128-rtx50") {
            $label = "RTX 50 系列"
        } else {
            $label = "RTX 50 以下主流 NVIDIA"
        }

        $lines.Add(('| {0} | `{1}` | `{2}` |' -f $label, $pkg.File, $pkg.Hash))
    }

    $lines.Add("")
    $lines.Add('使用方式：下载匹配显卡的 ZIP，校验 SHA256，解压后双击 `portable-run.bat`。')
    $lines.Add("")
    $lines.Add("> 首版完整便携包只支持 NVIDIA GPU，不提供纯 CPU 包。")

    Set-Content -LiteralPath $template -Encoding UTF8 -Value ($lines -join "`r`n")
    Write-Info "Release 模板: $template"
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$version = Get-ReleaseVersion -Root $root -RequestedVersion $Version
if (-not $AllowLocalVersion -and -not (Test-VersionIsReleaseLike -Version $version)) {
    Fail "当前解析到的版本号 '$version' 不像正式发布版本。请使用 -Version vX.Y.Z，或测试时加 -AllowLocalVersion。"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root "portable-dist"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if ($CleanOldArtifacts -and -not $PlanOnly) {
    Write-Step "清理旧便携包产物"
    Get-ChildItem -LiteralPath $OutputDir -File -Filter "sharp-gui-*-windows-*-portable.zip" -ErrorAction SilentlyContinue |
        Remove-Item -Force
    Get-ChildItem -LiteralPath $OutputDir -File -Filter "sharp-gui-*-windows-*-portable.sha256.txt" -ErrorAction SilentlyContinue |
        Remove-Item -Force
    Get-ChildItem -LiteralPath $OutputDir -File -Filter "portable-release-template-*.md" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

$mainPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $mainPython)) {
    Fail "未找到主虚拟环境 venv\Scripts\python.exe，请先运行 install.bat"
}
if (-not (Test-Path -LiteralPath (Join-Path $root "ml-sharp"))) {
    Fail "未找到 ml-sharp 目录，请先运行 install.bat"
}

$sevenZip = Resolve-SevenZip
if (-not $sevenZip) {
    Fail "未找到 7-Zip。请安装 7-Zip 后再生成完整大包。"
}

Write-Step "一键便携包发布计划"
Write-Info "版本: $version"
Write-Info "输出目录: $OutputDir"
Write-Info "压缩等级: $CompressionLevel"
Write-Info "7-Zip: $sevenZip"

$mainInfo = Test-PythonCuda -PythonExe $mainPython
Write-Info "主环境: torch=$($mainInfo.torch), cuda=$($mainInfo.cuda), device=$($mainInfo.device)"

$cu126Venv = $null
if (-not $SkipCu126) {
    if ($PlanOnly) {
        $cu126Venv = Join-Path $root ".portable-venvs\cu126"
        Write-Info "cu126 环境: $cu126Venv (PlanOnly 不安装)"
    } else {
        $cu126Venv = Ensure-Cu126Venv -Root $root -BasePython $mainPython
    }
}

if ($PlanOnly) {
    if (-not $SkipCu128) {
        Invoke-PackageBuild -Root $root -Version $version -Target "cu128-rtx50" -VenvDir (Join-Path $root "venv") -OutputDir $OutputDir -CompressionLevel $CompressionLevel -SkipFrontendBuild:$false -PlanOnly:$true
    }
    if (-not $SkipCu126) {
        if (Test-Path -LiteralPath (Join-Path $cu126Venv "Scripts\python.exe")) {
            Invoke-PackageBuild -Root $root -Version $version -Target "cu126-mainstream" -VenvDir $cu126Venv -OutputDir $OutputDir -CompressionLevel $CompressionLevel -SkipFrontendBuild:$true -PlanOnly:$true
        } else {
            Write-Step "打包计划"
            Write-Info "版本: $version"
            Write-Info "目标包: cu126-mainstream"
            Write-Info "依赖虚拟环境: $cu126Venv"
            Write-Info "输出 ZIP: $(Join-Path $OutputDir "sharp-gui-$version-windows-cu126-mainstream-portable.zip")"
            Write-Info "cu126 缓存环境尚不存在，真实运行时会自动创建。"
        }
    }
    Write-Host ""
    Write-Host "[OK] 一键发布计划检查完成，未生成 ZIP。" -ForegroundColor Green
    exit 0
}

if (-not $SkipCu128) {
    Invoke-PackageBuild -Root $root -Version $version -Target "cu128-rtx50" -VenvDir (Join-Path $root "venv") -OutputDir $OutputDir -CompressionLevel $CompressionLevel -SkipFrontendBuild:$false -PlanOnly:$false
}

if (-not $SkipCu126) {
    Invoke-PackageBuild -Root $root -Version $version -Target "cu126-mainstream" -VenvDir $cu126Venv -OutputDir $OutputDir -CompressionLevel $CompressionLevel -SkipFrontendBuild:$true -PlanOnly:$false
}

$packages = @()
foreach ($zip in Get-ChildItem -LiteralPath $OutputDir -Filter "sharp-gui-$version-windows-*-portable.zip" | Sort-Object Name) {
    $hash = (Get-FileHash -LiteralPath $zip.FullName -Algorithm SHA256).Hash
    $shaPath = Join-Path $zip.DirectoryName ($zip.BaseName + ".sha256.txt")
    Set-Content -LiteralPath $shaPath -Encoding ASCII -Value "$hash  $($zip.Name)"

    if (-not $SkipArchiveTest) {
        Test-Archive -SevenZip $sevenZip -ZipPath $zip.FullName
    }

    $target = if ($zip.Name -match "windows-(.+)-portable\.zip$") { $Matches[1] } else { "unknown" }
    $packages += [PSCustomObject]@{
        File = $zip.Name
        SizeGiB = [math]::Round($zip.Length / 1GB, 2)
        Hash = $hash
        Target = $target
    }
}

Write-ReleaseTemplate -OutputDir $OutputDir -Version $version -Packages $packages

if ($CleanBuildVenvs -and -not $PlanOnly) {
    Write-Step "清理临时打包环境"
    Remove-Item -LiteralPath (Join-Path $root ".portable-venvs") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $root ".portable-build") -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Remove-Item -LiteralPath (Join-Path $root ".portable-build") -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[OK] Windows 完整便携包一键打包完成" -ForegroundColor Green
$packages | Format-Table File, Target, SizeGiB, Hash -AutoSize
Write-Host ""
Write-Host "下一步：把 ZIP 和 .sha256.txt 上传到网盘，然后把 portable-release-template-$version.md 内容贴进 GitHub Release。"
Write-Host ""
Write-Host "缓存说明："
Write-Host "  cu126 打包缓存: $(Join-Path $root ".portable-venvs")"
Write-Host "  pip 缓存: $env:LOCALAPPDATA\pip\Cache"
Write-Host "  npm 缓存: $env:LOCALAPPDATA\npm-cache"
Write-Host "如需手动清理项目内打包缓存，可运行："
Write-Host "  rmdir /s /q .portable-venvs"
Write-Host "旧版本 ZIP 默认保留在 portable-dist；如需清理，请手动删除不需要的版本。"











