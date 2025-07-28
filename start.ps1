#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 启动脚本 ===" -ForegroundColor Green
Write-Host "正在启动 YouTube 下载器和 Telegram 机器人..." -ForegroundColor Yellow

# 检查Poetry环境
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Poetry，请确保 Poetry 已安装并在 PATH 中" -ForegroundColor Red
    exit 1
}

# 进入源代码目录
Push-Location src

try {
    Write-Host "启动 YouTube 下载器..." -ForegroundColor Cyan
    $downloaderProcess = Start-Process -FilePath "poetry" -ArgumentList "run", "python", "yt_dlp_downloader.py" -WindowStyle Normal -PassThru
    
    Start-Sleep 2  # 等待2秒再启动第二个进程
    
    Write-Host "启动 Telegram 机器人..." -ForegroundColor Cyan
    $botProcess = Start-Process -FilePath "poetry" -ArgumentList "run", "python", "telegram_bot.py" -WindowStyle Normal -PassThru
    
    Write-Host ""
    Write-Host "=== 启动完成 ===" -ForegroundColor Green
    Write-Host "YouTube 下载器 PID: $($downloaderProcess.Id)" -ForegroundColor White
    Write-Host "Telegram 机器人 PID: $($botProcess.Id)" -ForegroundColor White
    Write-Host ""
    Write-Host "按任意键停止所有进程..." -ForegroundColor Yellow
    
    # 等待用户输入
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    Write-Host ""
    Write-Host "正在停止进程..." -ForegroundColor Yellow
    
    # 停止进程
    if (-not $downloaderProcess.HasExited) {
        Stop-Process -Id $downloaderProcess.Id -Force
        Write-Host "YouTube 下载器已停止" -ForegroundColor Green
    }
    
    if (-not $botProcess.HasExited) {
        Stop-Process -Id $botProcess.Id -Force
        Write-Host "Telegram 机器人已停止" -ForegroundColor Green
    }
    
}
catch {
    Write-Host "启动过程中发生错误: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Pop-Location
}

Write-Host "程序已退出" -ForegroundColor Green 