# Transcoder 一键打包脚本（Windows）
# 使用系统 Python 3.14（自带 tkinter）创建虚拟环境并打包为单文件 exe。
# 用法：在 transcoder/ 目录右键"使用 PowerShell 运行" 或命令行执行：
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

# 系统 Python（需自带 tkinter 用于打包 GUI）。脚本按以下顺序自动探测；
# 也可把下面 $PY 直接改成你本机 python.exe 的绝对路径。
$candidates = @(
    "py",
    "python",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python314\python.exe",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python313\python.exe"
)
$PY = $null
foreach ($c in $candidates) {
    if ($c -eq "py" -or $c -eq "python") {
        if (Get-Command $c -ErrorAction SilentlyContinue) { $PY = $c; break }
    } elseif (Test-Path $c) { $PY = $c; break }
}
if (-not $PY) {
    Write-Host "未找到 Python（需 3.13/3.14 且自带 tkinter）。" -ForegroundColor Red
    Write-Host "请修改脚本顶部的 `$PY 为你的 python.exe 路径。" -ForegroundColor Yellow
    pause
    exit 1
}
Write-Host "使用 Python：$PY" -ForegroundColor Cyan

$VENV = ".build/venv"
if (-not (Test-Path $VENV)) {
    Write-Host "创建虚拟环境..." -ForegroundColor Cyan
    & $PY -m venv $VENV
}
$PIP = "$VENV/Scripts/python.exe"
& $PIP -m pip install --upgrade pip | Out-Null
& $PIP -m pip install pyinstaller | Out-Null

# 若 ffmpeg/ffmpeg.exe 存在则会被 build.spec 一并打包；否则提示用户手动放置。
if (Test-Path "ffmpeg/ffmpeg.exe") {
    Write-Host "检测到 ffmpeg/ffmpeg.exe，将一并打包。" -ForegroundColor Green
} else {
    Write-Host "未检测到 ffmpeg/ffmpeg.exe。打包后会缺少转码核心，" -ForegroundColor Yellow
    Write-Host "请将 ffmpeg.exe（及 ffprobe.exe）放入 ffmpeg/ 目录后重新运行本脚本。" -ForegroundColor Yellow
}

Write-Host "开始打包..." -ForegroundColor Cyan
& "$VENV/Scripts/pyinstaller.exe" --clean -y build.spec

if (Test-Path "dist/Transcoder.exe") {
    Write-Host "`n完成：dist/Transcoder.exe" -ForegroundColor Green
    if (-not (Test-Path "ffmpeg/ffmpeg.exe")) {
        Write-Host "提醒：请把 ffmpeg.exe / ffprobe.exe 复制到 dist/Transcoder.exe 同目录下的 ffmpeg/ 子目录。" -ForegroundColor Yellow
    }
} else {
    Write-Host "打包似乎失败，请检查上方输出。" -ForegroundColor Red
}
pause
