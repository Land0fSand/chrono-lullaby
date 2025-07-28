#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 后台启动脚本 ===" -ForegroundColor Green

# 获取脚本所在的绝对路径
$scriptPath = $MyInvocation.MyCommand.Path
$projectRoot = Split-Path $scriptPath -Parent

Write-Host "项目目录: $projectRoot" -ForegroundColor Gray

# 检查Poetry环境
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Poetry，请确保 Poetry 已安装并在 PATH 中" -ForegroundColor Red
    exit 1
}

# 切换到项目根目录
Set-Location $projectRoot

# 检查是否在正确的项目目录（检查标志性文件）
if (-not (Test-Path "src/yt_dlp_downloader.py") -or -not (Test-Path "src/telegram_bot.py")) {
    Write-Host "错误: 未找到项目文件，请确保脚本在正确的项目目录中" -ForegroundColor Red
    Write-Host "当前目录: $(Get-Location)" -ForegroundColor Red
    exit 1
}

# 进入源代码目录
Push-Location src

try {
    # 创建日志目录（使用绝对路径）
    $logDir = Join-Path $projectRoot "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    # 设置日志文件路径（使用绝对路径）
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $downloaderLog = Join-Path $logDir "downloader_$timestamp.log"
    $botLog = Join-Path $logDir "bot_$timestamp.log"
    $downloaderErrorLog = Join-Path $logDir "downloader_error_$timestamp.log"
    $botErrorLog = Join-Path $logDir "bot_error_$timestamp.log"
    
    Write-Host "后台启动 YouTube 下载器..." -ForegroundColor Cyan
    Write-Host "下载器日志: $downloaderLog" -ForegroundColor Gray
    $downloaderProcess = Start-Process -FilePath "poetry" -ArgumentList "run", "python", "yt_dlp_downloader.py" -WindowStyle Hidden -PassThru -RedirectStandardOutput $downloaderLog -RedirectStandardError $downloaderErrorLog
    
    Start-Sleep 2
    
    Write-Host "后台启动 Telegram 机器人..." -ForegroundColor Cyan
    Write-Host "机器人日志: $botLog" -ForegroundColor Gray
    $botProcess = Start-Process -FilePath "poetry" -ArgumentList "run", "python", "telegram_bot.py" -WindowStyle Hidden -PassThru -RedirectStandardOutput $botLog -RedirectStandardError $botErrorLog
    
    # 创建进程信息文件（使用绝对路径）
    $processInfoPath = Join-Path $projectRoot "process_info.json"
    $processInfo = @{
        "downloader_pid"       = $downloaderProcess.Id
        "bot_pid"              = $botProcess.Id
        "start_time"           = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "project_root"         = $projectRoot
        "downloader_log"       = $downloaderLog
        "bot_log"              = $botLog
        "downloader_error_log" = $downloaderErrorLog
        "bot_error_log"        = $botErrorLog
    }
    
    $processInfo | ConvertTo-Json | Out-File -FilePath $processInfoPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "=== 后台启动完成 ===" -ForegroundColor Green
    Write-Host "YouTube 下载器 PID: $($downloaderProcess.Id)" -ForegroundColor White
    Write-Host "Telegram 机器人 PID: $($botProcess.Id)" -ForegroundColor White
    Write-Host "进程信息已保存到: $processInfoPath" -ForegroundColor White
    Write-Host ""
    Write-Host "使用以下命令管理:" -ForegroundColor Yellow
    Write-Host "  查看状态: ch-status" -ForegroundColor Gray
    Write-Host "  查看日志: ch-logs" -ForegroundColor Gray
    Write-Host "  停止服务: ch-stop" -ForegroundColor Gray
    
}
catch {
    Write-Host "启动过程中发生错误: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Pop-Location
} 