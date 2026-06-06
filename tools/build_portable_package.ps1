param(
    [string]$Version = "",
    [ValidateSet("auto", "cu128-rtx50", "cu128-nvidia", "cu126-mainstream")]
    [string]$Target = "auto",
    [string]$OutputDir = "",
    [string]$VenvDir = "",
    [int]$CompressionLevel = 1,
    [switch]$SkipFrontendBuild,
    [switch]$SkipModel,
    [switch]$PlanOnly,
    [switch]$AllowLocalVersion,
    [switch]$KeepStaging
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

function Invoke-Robocopy {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExtraArgs = @()
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        Fail "源路径不存在: $Source"
    }

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $args = @($Source, $Destination, "/MIR", "/R:2", "/W:2", "/NFL", "/NDL", "/NP") + $ExtraArgs
    & robocopy @args | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Fail "复制失败: $Source -> $Destination (robocopy exit $LASTEXITCODE)"
    }
}

function Copy-FileIfExists {
    param(
        [string]$Source,
        [string]$DestinationDirectory
    )

    if (Test-Path -LiteralPath $Source) {
        New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
        Copy-Item -LiteralPath $Source -Destination $DestinationDirectory -Force
    }
}

function Get-ConfigValue {
    param(
        [string]$Path,
        [string]$Key
    )

    $line = Get-Content -LiteralPath $Path -Encoding UTF8 |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } |
        Select-Object -First 1
    if (-not $line) {
        return $null
    }
    return ($line -replace "^\s*$([regex]::Escape($Key))\s*=\s*", "").Trim()
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

function Resolve-Npm {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $cmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "$env:ProgramFiles\nodejs\npm.cmd",
        "${env:ProgramFiles(x86)}\nodejs\npm.cmd",
        "$env:APPDATA\npm\npm.cmd"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Resolve-Node {
    $cmd = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "$env:ProgramFiles\nodejs\node.exe",
        "${env:ProgramFiles(x86)}\nodejs\node.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Invoke-Npm {
    param(
        [string]$NpmCmd,
        [string[]]$Arguments
    )

    $quotedNpm = '"' + $NpmCmd + '"'
    $commandLine = $quotedNpm + " " + ($Arguments -join " ")
    & cmd.exe /d /c $commandLine
}

function Invoke-FrontendBuild {
    param(
        [string]$NodeCmd,
        [string]$FrontendDir
    )

    $tsc = Join-Path $FrontendDir "node_modules\typescript\bin\tsc"
    $vite = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"

    if (-not (Test-Path -LiteralPath $tsc)) {
        return 1
    }
    if (-not (Test-Path -LiteralPath $vite)) {
        return 1
    }

    & $NodeCmd $tsc -b | Out-Host
    if ($LASTEXITCODE -ne 0) {
        return $LASTEXITCODE
    }

    & $NodeCmd $vite build | Out-Host
    return $LASTEXITCODE
}

function Get-TorchInfo {
    param([string]$PythonExe)

    $code = @'
import json
import sys
import warnings

try:
    warnings.filterwarnings("ignore")
    import torch
    info = {
        "ok": True,
        "version": getattr(torch, "__version__", ""),
        "cuda": getattr(getattr(torch, "version", None), "cuda", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "device_name": None,
        "capability": None,
        "arch_list": [],
    }
    if info["cuda_available"]:
        info["device_name"] = torch.cuda.get_device_name(0)
        info["capability"] = list(torch.cuda.get_device_capability(0))
        info["arch_list"] = list(torch.cuda.get_arch_list())
    print(json.dumps(info, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
    sys.exit(2)
'@

    $tmp = Join-Path $env:TEMP ("sharp-pack-torch-info-{0}.py" -f ([guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $tmp -Encoding UTF8 -Value $code
    try {
        $raw = & $PythonExe $tmp
        if ($LASTEXITCODE -ne 0) {
            Fail "无法读取 PyTorch 信息: $raw"
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    return $raw | ConvertFrom-Json
}

function Resolve-ModelPath {
    param([string]$PythonExe, [string]$Root)

    $code = @"
import sys
sys.path.insert(0, r"$Root")
from tools.download_model import get_model_path
print(get_model_path())
"@
    $tmp = Join-Path $env:TEMP ("sharp-pack-model-path-{0}.py" -f ([guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $tmp -Encoding UTF8 -Value $code
    try {
        $path = & $PythonExe $tmp
        if ($LASTEXITCODE -ne 0 -or -not $path) {
            Fail "无法解析 Sharp 模型缓存路径"
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    return $path.Trim()
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ([string]::IsNullOrWhiteSpace($Version)) {
    if (Test-Path -LiteralPath "$root\version.txt") {
        $Version = (Get-Content -LiteralPath "$root\version.txt" -Encoding UTF8 | Select-Object -First 1).Trim()
    }
    if ([string]::IsNullOrWhiteSpace($Version)) {
        try {
            $tag = (& git -C $root describe --tags --exact-match 2>$null).Trim()
            if (-not [string]::IsNullOrWhiteSpace($tag)) {
                $Version = $tag
            }
        } catch {
        }
    }
    if ([string]::IsNullOrWhiteSpace($Version)) {
        try {
            $tag = (& git -C $root describe --tags --abbrev=0 2>$null).Trim()
            if (-not [string]::IsNullOrWhiteSpace($tag)) {
                $Version = $tag
            }
        } catch {
        }
    }
    if ([string]::IsNullOrWhiteSpace($Version)) {
        $Version = "local-" + (Get-Date -Format "yyyyMMdd-HHmm")
    }
}
$Version = $Version -replace "^refs/tags/", ""
if (-not $AllowLocalVersion -and $Version -notmatch '^v\d+\.\d+\.\d+([.-](rc|alpha|beta|preview)\.?\d*)?$') {
    Fail "当前版本号 '$Version' 不像正式发布版本。请使用 -Version vX.Y.Z，或测试时加 -AllowLocalVersion。"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root "portable-dist"
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $root $OutputDir
}

if ($CompressionLevel -lt 0 -or $CompressionLevel -gt 9) {
    Fail "CompressionLevel 必须在 0 到 9 之间"
}

if ([string]::IsNullOrWhiteSpace($VenvDir)) {
    $VenvDir = Join-Path $root "venv"
} elseif (-not [System.IO.Path]::IsPathRooted($VenvDir)) {
    $VenvDir = Join-Path $root $VenvDir
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$pyvenvCfg = Join-Path $VenvDir "pyvenv.cfg"
$mlSharpDir = Join-Path $root "ml-sharp"
$frontendDir = Join-Path $root "frontend"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Fail "未找到虚拟环境 Python: $venvPython"
}
if (-not (Test-Path -LiteralPath $pyvenvCfg)) {
    Fail "未找到虚拟环境配置: $pyvenvCfg"
}
if (-not (Test-Path -LiteralPath $mlSharpDir)) {
    Fail "未找到 ml-sharp 目录，请先运行 install.bat"
}
if (-not (Test-Path -LiteralPath $frontendDir)) {
    Fail "未找到 frontend 目录"
}

$pythonHome = Get-ConfigValue -Path $pyvenvCfg -Key "home"
if ([string]::IsNullOrWhiteSpace($pythonHome) -or -not (Test-Path -LiteralPath (Join-Path $pythonHome "python.exe"))) {
    Fail "无法从 venv\pyvenv.cfg 找到可复制的 Python 安装目录: $pythonHome"
}

$torchInfo = Get-TorchInfo -PythonExe $venvPython
if (-not $torchInfo.ok) {
    Fail "当前 venv 中 PyTorch 不可用: $($torchInfo.error)"
}
if (-not $torchInfo.cuda_available) {
    Fail "当前 venv 不是可用的 CUDA 环境。首版完整包不提供 CPU 版本，请先在本机安装并验证 GPU 版 PyTorch。"
}

$resolvedTarget = $Target
if ($Target -eq "auto") {
    $name = [string]$torchInfo.device_name
    $cuda = [string]$torchInfo.cuda
    if ($name -match "RTX\s*50|RTX\s*5\d{3}") {
        $resolvedTarget = "cu128-rtx50"
    } elseif ($cuda.StartsWith("12.6")) {
        $resolvedTarget = "cu126-mainstream"
    } elseif ($cuda.StartsWith("12.8")) {
        $resolvedTarget = "cu128-nvidia"
    } else {
        $resolvedTarget = "cu$($cuda.Replace('.', ''))-nvidia"
    }
}

$modelPath = $null
if (-not $SkipModel) {
    $modelPath = Resolve-ModelPath -PythonExe $venvPython -Root $root
    if (-not (Test-Path -LiteralPath $modelPath)) {
        Write-Step "模型文件不存在，尝试先下载模型"
        & $venvPython "$root\tools\download_model.py"
        if ($LASTEXITCODE -ne 0) {
            Fail "模型下载失败。也可以手动下载后重新运行打包脚本。"
        }
    }
}

$packageName = "sharp-gui-$Version-windows-$resolvedTarget-portable"
$stagingRoot = Join-Path $root ".portable-build"
$packageRoot = Join-Path $stagingRoot $packageName
$zipPath = Join-Path $OutputDir "$packageName.zip"

Write-Step "打包计划"
Write-Info "版本: $Version"
Write-Info "目标包: $resolvedTarget"
Write-Info "PyTorch: $($torchInfo.version)"
Write-Info "CUDA: $($torchInfo.cuda)"
Write-Info "GPU: $($torchInfo.device_name)"
Write-Info "Python 源目录: $pythonHome"
Write-Info "依赖虚拟环境: $VenvDir"
Write-Info "输出 ZIP: $zipPath"
if ($modelPath) {
    $modelSizeGb = [math]::Round((Get-Item -LiteralPath $modelPath).Length / 1GB, 2)
    Write-Info ("模型: {0} ({1} GiB)" -f $modelPath, $modelSizeGb)
} else {
    Write-Info "模型: 跳过复制"
}

if ($PlanOnly) {
    Write-Host ""
    Write-Host "[OK] 计划检查完成，未执行复制或压缩。" -ForegroundColor Green
    exit 0
}

Write-Step "准备前端构建"
if (-not $SkipFrontendBuild) {
    $npmCmd = Resolve-Npm
    if (-not $npmCmd) {
        Fail "未找到 npm。请先安装 Node.js LTS，或确认 npm.cmd 在 PATH 中。"
    }
    $nodeCmd = Resolve-Node
    if (-not $nodeCmd) {
        Fail "未找到 node。请先安装 Node.js LTS，或确认 node.exe 在 PATH 中。"
    }
    Write-Info "npm: $npmCmd"
    Write-Info "node: $nodeCmd"

    Push-Location $frontendDir
    try {
        $buildReady = $false

        if (Test-Path -LiteralPath "$frontendDir\node_modules") {
            Write-Info "检测到现有 node_modules，先直接尝试构建，避免 npm 修改 lockfile"
            $buildExit = Invoke-FrontendBuild -NodeCmd $nodeCmd -FrontendDir $frontendDir
            if ($buildExit -eq 0) {
                $buildReady = $true
            } else {
                Write-Info "现有 node_modules 构建失败，准备重新安装前端依赖"
            }
        }

        if (-not $buildReady) {
            if (Test-Path -LiteralPath "$frontendDir\package-lock.json") {
                Write-Info "尝试 npm ci"
                Invoke-Npm -NpmCmd $npmCmd -Arguments @("ci", "--no-audit", "--no-fund")
                if ($LASTEXITCODE -ne 0) {
                    Write-Info "npm ci 失败，改用 npm install --no-package-lock 以兼容当前 lockfile"
                    Invoke-Npm -NpmCmd $npmCmd -Arguments @("install", "--no-package-lock", "--no-audit", "--no-fund")
                    if ($LASTEXITCODE -ne 0) {
                        Fail "npm install 失败"
                    }
                }
            } else {
                Invoke-Npm -NpmCmd $npmCmd -Arguments @("install", "--no-audit", "--no-fund")
                if ($LASTEXITCODE -ne 0) {
                    Fail "npm install 失败"
                }
            }

            $buildExit = Invoke-FrontendBuild -NodeCmd $nodeCmd -FrontendDir $frontendDir
            if ($buildExit -ne 0) {
                Fail "npm run build 失败"
            }
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Info "已跳过前端构建"
}

if (-not (Test-Path -LiteralPath "$frontendDir\dist\index.html")) {
    Fail "未找到 frontend\dist\index.html，请先完成前端构建"
}

Write-Step "创建打包目录"
if (Test-Path -LiteralPath $packageRoot) {
    Remove-Item -LiteralPath $packageRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Step "复制应用文件"
$coreFiles = @(
    "app.py",
    "README.md",
    "README.en.md",
    "LICENSE",
    "run.bat",
    "build.bat",
    "update.bat"
)
foreach ($file in $coreFiles) {
    Copy-FileIfExists -Source (Join-Path $root $file) -DestinationDirectory $packageRoot
}

Invoke-Robocopy -Source "$root\tools" -Destination "$packageRoot\tools" -ExtraArgs @("/XD", "__pycache__")
Invoke-Robocopy -Source "$root\backend" -Destination "$packageRoot\backend" -ExtraArgs @("/XD", "__pycache__")
Invoke-Robocopy -Source "$root\templates" -Destination "$packageRoot\templates"
Invoke-Robocopy -Source "$root\static" -Destination "$packageRoot\static"

New-Item -ItemType Directory -Force -Path "$packageRoot\frontend" | Out-Null
Invoke-Robocopy -Source "$frontendDir\dist" -Destination "$packageRoot\frontend\dist"
Copy-FileIfExists -Source "$frontendDir\package.json" -DestinationDirectory "$packageRoot\frontend"
Copy-FileIfExists -Source "$frontendDir\package-lock.json" -DestinationDirectory "$packageRoot\frontend"
if (Test-Path -LiteralPath "$frontendDir\node_modules") {
    Invoke-Robocopy -Source "$frontendDir\node_modules" -Destination "$packageRoot\frontend\node_modules"
}

Invoke-Robocopy -Source $mlSharpDir -Destination "$packageRoot\ml-sharp" -ExtraArgs @("/XD", ".git", "__pycache__", ".pytest_cache")

Write-Step "复制 Python 运行时与依赖"
Invoke-Robocopy -Source $pythonHome -Destination "$packageRoot\python" -ExtraArgs @("/XD", "__pycache__", "Doc", "tcl", "Tools")
Invoke-Robocopy -Source "$VenvDir\Lib\site-packages" -Destination "$packageRoot\python\Lib\site-packages" -ExtraArgs @("/XD", "__pycache__")

$editablePth = "$packageRoot\python\Lib\site-packages\__editable__.sharp-0.1.pth"
if (Test-Path -LiteralPath $editablePth) {
    Set-Content -LiteralPath $editablePth -Encoding UTF8 -Value "..\..\..\ml-sharp\src"
}

Write-Step "复制模型与创建运行目录"
New-Item -ItemType Directory -Force -Path "$packageRoot\inputs" | Out-Null
New-Item -ItemType Directory -Force -Path "$packageRoot\outputs" | Out-Null
if ($modelPath) {
    $modelDestDir = "$packageRoot\.cache\torch\hub\checkpoints"
    New-Item -ItemType Directory -Force -Path $modelDestDir | Out-Null
    Copy-Item -LiteralPath $modelPath -Destination $modelDestDir -Force
}

Write-Step "生成便携启动脚本"
$portableRun = @'
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONHOME="
set "PYTHONPATH="
set "TORCH_HOME=%SCRIPT_DIR%.cache\torch"
set "SHARP_FRONTEND_MODE=react"
set "PATH=%SCRIPT_DIR%;%SCRIPT_DIR%python;%SCRIPT_DIR%python\Scripts;%PATH%"

if /I "%~1"=="--verbose" (
    set "SHARP_VERBOSE=1"
    set "SHARP_LOG_LEVEL=DEBUG"
    set "SHARP_LOG_FILE=%SCRIPT_DIR%sharp-gui-verbose.log"
    set "PYTHONFAULTHANDLER=1"
)

if not exist "%SCRIPT_DIR%python\python.exe" (
    echo [ERROR] Missing bundled Python: %SCRIPT_DIR%python\python.exe
    goto failed
)

if not exist "%SCRIPT_DIR%ml-sharp\src" (
    echo [ERROR] Missing bundled ml-sharp source directory.
    goto failed
)

if not exist "%SCRIPT_DIR%frontend\dist\index.html" (
    echo [ERROR] Missing React build: frontend\dist\index.html
    goto failed
)

if not exist "%SCRIPT_DIR%inputs" mkdir "%SCRIPT_DIR%inputs"
if not exist "%SCRIPT_DIR%outputs" mkdir "%SCRIPT_DIR%outputs"

if not "%SHARP_SKIP_CUDA_CHECK%"=="1" (
    echo [1/2] Checking bundled CUDA runtime...
    "%SCRIPT_DIR%python\python.exe" -c "import torch; assert torch.cuda.is_available(), 'CUDA is not available'; x=torch.ones((4,4),device='cuda'); y=(x@x).sum(); torch.cuda.synchronize(); print('CUDA OK: torch=' + torch.__version__ + ', cuda=' + str(torch.version.cuda) + ', gpu=' + torch.cuda.get_device_name(0))"
    if errorlevel 1 goto cuda_failed
)

if "%SHARP_VERBOSE%"=="1" (
    echo [Verbose] Extra diagnostics enabled.
    echo [Verbose] Log file: %SHARP_LOG_FILE%
)

echo.
echo [2/2] Starting Sharp GUI...
echo.
"%SCRIPT_DIR%python\python.exe" app.py

pause
exit /b 0

:cuda_failed
echo.
echo [ERROR] Bundled PyTorch CUDA check failed.
echo Please update your NVIDIA driver or use the package matching your GPU.
echo To skip this check temporarily, run:
echo   set SHARP_SKIP_CUDA_CHECK=1
echo   portable-run.bat
goto failed

:failed
echo.
pause
exit /b 1
'@
[System.IO.File]::WriteAllText(
    "$packageRoot\portable-run.bat",
    ($portableRun -replace "`r?`n", "`r`n"),
    [System.Text.Encoding]::ASCII
)

$portableRunVerbose = @'
@echo off
call "%~dp0portable-run.bat" --verbose %*
exit /b %ERRORLEVEL%
'@
[System.IO.File]::WriteAllText(
    "$packageRoot\portable-run-verbose.bat",
    ($portableRunVerbose -replace "`r?`n", "`r`n"),
    [System.Text.Encoding]::ASCII
)

$sharpCmd = @'
@echo off
"%~dp0python\python.exe" -c "from sharp.cli import main_cli; main_cli()" %*
'@
Set-Content -LiteralPath "$packageRoot\sharp.cmd" -Encoding ASCII -Value $sharpCmd

$packageInfo = [ordered]@{
    name = $packageName
    version = $Version
    target = $resolvedTarget
    createdAt = (Get-Date).ToString("s")
    torch = @{
        version = $torchInfo.version
        cuda = $torchInfo.cuda
        deviceName = $torchInfo.device_name
        capability = $torchInfo.capability
        archList = $torchInfo.arch_list
    }
    notes = @(
        "这是本地打包生成的 Windows GPU 完整 ZIP。",
        "首选入口是 portable-run.bat。",
        "反馈问题时可以运行 portable-run-verbose.bat 获取更多日志。",
        "包内使用本地 TORCH_HOME，模型文件放在 .cache\\torch\\hub\\checkpoints。"
    )
}
$packageInfo | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$packageRoot\portable-package.json" -Encoding UTF8

$notes = @"
# Sharp GUI Windows 完整便携包

入口：双击 `portable-run.bat`。

反馈问题时：双击 `portable-run-verbose.bat`，并把窗口中的完整日志或 `sharp-gui-verbose.log` 发给维护者。

本包包含：

- Sharp GUI 后端与已构建 React 前端
- Apple ml-sharp 源码副本
- 包内 Python 运行时与当前本机 venv 中的 Python 依赖
- Sharp 模型缓存（除非打包时使用了 `-SkipModel`）
- `sharp.cmd` 包内 CLI 入口
- `portable-run-verbose.bat` 详细日志入口

注意：

- 首版只面向 NVIDIA GPU，不提供纯 CPU 包。
- 如果目标机器 NVIDIA 驱动过旧，包内 PyTorch CUDA 检查会失败，需要升级驱动或换用匹配包。
- 这个包用于网盘发布，不适合上传到 GitHub Release 资产。
- 如果移动包目录，仍应使用包内的 `portable-run.bat` 启动。
"@
Set-Content -LiteralPath "$packageRoot\便携包说明.md" -Encoding UTF8 -Value $notes

Write-Step "压缩完整 ZIP"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$sevenZip = Resolve-SevenZip
if ($sevenZip) {
    Write-Info "使用 7-Zip 生成 ZIP64: $sevenZip"
    Push-Location $packageRoot
    try {
        & $sevenZip a -tzip "-mx=$CompressionLevel" $zipPath ".\*" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Fail "7-Zip 压缩失败"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Info "未找到 7-Zip，改用 tar.exe 生成 zip"
    Push-Location $packageRoot
    try {
        & tar -a -cf $zipPath *
        if ($LASTEXITCODE -ne 0) {
            Fail "tar 压缩失败。建议安装 7-Zip 后重试。"
        }
    } finally {
        Pop-Location
    }
}

$zipItem = Get-Item -LiteralPath $zipPath
$zipHash = Get-FileHash -LiteralPath $zipPath -Algorithm SHA256
$hashLine = "$($zipHash.Hash)  $($zipItem.Name)"
Set-Content -LiteralPath (Join-Path $OutputDir "$packageName.sha256.txt") -Encoding ASCII -Value $hashLine

if (-not $KeepStaging) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}

Write-Host ""
Write-Host "[OK] 完整便携包已生成" -ForegroundColor Green
Write-Host "ZIP: $zipPath"
Write-Host ("大小: {0:N2} GiB" -f ($zipItem.Length / 1GB))
Write-Host "SHA256: $($zipHash.Hash)"
Write-Host ""
Write-Host "网盘发布建议：同时上传 ZIP 和 .sha256.txt，并在 GitHub Release 正文贴网盘链接与校验值。"










