#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ChronoLullaby 本地编译脚本
.DESCRIPTION
    使用 PyInstaller 将核心服务编译为独立可执行文件。
    编译产物输出到项目根目录的 dist/ 目录。
.PARAMETER Clean
    编译前清理旧的编译产物
.EXAMPLE
    .\scripts\build.ps1
    .\scripts\build.ps1 -Clean
#>

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# 获取项目根目录
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = Split-Path $scriptDir -Parent
$specFile = Join-Path $projectRoot "build\chronolullaby.spec"
$distDir = Join-Path $projectRoot "dist"
$buildTmpDir = Join-Path $projectRoot "build\tmp"

Write-Host "=== ChronoLullaby 编译工具 ===" -ForegroundColor Green
Write-Host ""

# 检查 spec 文件
if (-not (Test-Path $specFile)) {
    Write-Host "错误: 找不到 spec 文件: $specFile" -ForegroundColor Red
    exit 1
}

# 检查 PyInstaller 是否可用
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$useVenv = Test-Path $venvPython

if ($useVenv) {
    $pyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
    if (-not (Test-Path $pyinstaller)) {
        Write-Host "错误: 虚拟环境中未安装 PyInstaller" -ForegroundColor Red
        Write-Host "请运行: uv sync" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "使用虚拟环境: $venvPython" -ForegroundColor Gray
}
else {
    # 尝试用 uv 运行
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "错误: 未找到虚拟环境或 uv" -ForegroundColor Red
        exit 1
    }
    $pyinstaller = "pyinstaller"
    Write-Host "使用 uv 环境" -ForegroundColor Gray
}

# 清理旧产物
if ($Clean) {
    Write-Host "清理旧的编译产物..." -ForegroundColor Cyan
    if (Test-Path $distDir) {
        Remove-Item $distDir -Recurse -Force
        Write-Host "  已删除 dist/" -ForegroundColor Gray
    }
    if (Test-Path $buildTmpDir) {
        Remove-Item $buildTmpDir -Recurse -Force
        Write-Host "  已删除 build/tmp/" -ForegroundColor Gray
    }
    Write-Host ""
}

# 开始编译
Write-Host "开始编译..." -ForegroundColor Cyan
Write-Host "  Spec 文件: $specFile" -ForegroundColor Gray
Write-Host "  输出目录: $distDir" -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date

try {
    if ($useVenv) {
        & $pyinstaller `
            --distpath $distDir `
            --workpath $buildTmpDir `
            --noconfirm `
            $specFile
    }
    else {
        uv run pyinstaller `
            --distpath $distDir `
            --workpath $buildTmpDir `
            --noconfirm `
            $specFile
    }

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 编译失败，退出码: $LASTEXITCODE"
    }
}
catch {
    Write-Host ""
    Write-Host "编译失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$elapsed = (Get-Date) - $startTime

# 显示编译结果
Write-Host ""
Write-Host "=== 编译完成 ===" -ForegroundColor Green
Write-Host "耗时: $([math]::Round($elapsed.TotalSeconds, 1)) 秒" -ForegroundColor White
Write-Host ""

# 列出编译产物
$exeFiles = Get-ChildItem $distDir -Filter "*.exe" -ErrorAction SilentlyContinue
if (-not $exeFiles) {
    # macOS/Linux 没有 .exe 后缀
    $exeFiles = Get-ChildItem $distDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('yt_dlp_downloader', 'telegram_bot') }
}

if ($exeFiles) {
    Write-Host "编译产物:" -ForegroundColor Cyan
    foreach ($file in $exeFiles) {
        $sizeMB = [math]::Round($file.Length / 1MB, 2)
        Write-Host "  $($file.Name)  ($sizeMB MB)" -ForegroundColor White
    }
}
else {
    Write-Host "警告: 未找到编译产物" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "使用 'ch start' 启动服务时将自动检测并优先使用编译版本" -ForegroundColor Yellow
