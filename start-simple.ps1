#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 简单启动脚本 ===" -ForegroundColor Green
Write-Host "注意: 此脚本会在当前终端显示两个程序的输出" -ForegroundColor Yellow

# 检查Poetry环境
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Poetry，请确保 Poetry 已安装并在 PATH 中" -ForegroundColor Red
    exit 1
}

# 进入源代码目录
Push-Location src

try {
    Write-Host "启动下载器和机器人..." -ForegroundColor Cyan
    Write-Host "按 Ctrl+C 停止程序" -ForegroundColor Yellow
    Write-Host ""
    
    # 使用 PowerShell Job 在后台同时运行两个命令
    $downloaderJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        poetry run python yt_dlp_downloader.py
    }
    
    $botJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD  
        poetry run python telegram_bot.py
    }
    
    Write-Host "✅ 两个进程已启动" -ForegroundColor Green
    Write-Host "下载器 Job ID: $($downloaderJob.Id)" -ForegroundColor White
    Write-Host "机器人 Job ID: $($botJob.Id)" -ForegroundColor White
    Write-Host ""
    
    # 实时显示两个Job的输出
    while ($downloaderJob.State -eq "Running" -and $botJob.State -eq "Running") {
        # 获取下载器输出
        $downloaderOutput = Receive-Job $downloaderJob -Keep
        if ($downloaderOutput) {
            Write-Host "[下载器] $downloaderOutput" -ForegroundColor Cyan
        }
        
        # 获取机器人输出
        $botOutput = Receive-Job $botJob -Keep
        if ($botOutput) {
            Write-Host "[机器人] $botOutput" -ForegroundColor Green
        }
        
        Start-Sleep -Milliseconds 500
    }
    
}
catch {
    Write-Host "启动过程中发生错误: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    # 清理Job
    if ($downloaderJob) { 
        Stop-Job $downloaderJob -ErrorAction SilentlyContinue
        Remove-Job $downloaderJob -ErrorAction SilentlyContinue
    }
    if ($botJob) { 
        Stop-Job $botJob -ErrorAction SilentlyContinue 
        Remove-Job $botJob -ErrorAction SilentlyContinue
    }
    Pop-Location
}

Write-Host "程序已退出" -ForegroundColor Green 