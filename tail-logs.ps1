#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 实时日志跟踪 ===" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止跟踪" -ForegroundColor Yellow
Write-Host ""

# 检查进程信息文件
if (-not (Test-Path "process_info.json")) {
    Write-Host "❌ 未找到进程信息文件" -ForegroundColor Red
    Write-Host "请先使用 './start-background.ps1' 启动程序" -ForegroundColor Yellow
    exit 1
}

try {
    $processInfo = Get-Content "process_info.json" | ConvertFrom-Json
    
    # 获取日志文件路径
    $downloaderLog = $processInfo.downloader_log
    $botLog = $processInfo.bot_log
    
    # 检查日志文件是否存在
    if (-not (Test-Path $downloaderLog)) {
        Write-Host "❌ 下载器日志文件不存在: $downloaderLog" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Test-Path $botLog)) {
        Write-Host "❌ 机器人日志文件不存在: $botLog" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "📥 下载器日志: $downloaderLog" -ForegroundColor Cyan
    Write-Host "🤖 机器人日志: $botLog" -ForegroundColor Green
    Write-Host ""
    
    # 使用PowerShell Jobs来并行跟踪两个日志文件
    $downloaderJob = Start-Job -ScriptBlock {
        param($logPath)
        Get-Content $logPath -Tail 10 -Wait | ForEach-Object {
            "[下载器] $_"
        }
    } -ArgumentList $downloaderLog
    
    $botJob = Start-Job -ScriptBlock {
        param($logPath)
        Get-Content $logPath -Tail 10 -Wait | ForEach-Object {
            "[机器人] $_"
        }
    } -ArgumentList $botLog
    
    # 显示两个日志的输出
    while ($true) {
        # 获取下载器输出
        $downloaderOutput = Receive-Job $downloaderJob -Keep
        if ($downloaderOutput) {
            foreach ($line in $downloaderOutput) {
                if ($line -match "^\[下载器\]") {
                    Write-Host $line -ForegroundColor Cyan
                }
            }
        }
        
        # 获取机器人输出
        $botOutput = Receive-Job $botJob -Keep
        if ($botOutput) {
            foreach ($line in $botOutput) {
                if ($line -match "^\[机器人\]") {
                    Write-Host $line -ForegroundColor Green
                }
            }
        }
        
        Start-Sleep -Milliseconds 500
    }
    
}
catch {
    Write-Host "读取进程信息时出错: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    # 清理Jobs
    if ($downloaderJob) {
        Stop-Job $downloaderJob -ErrorAction SilentlyContinue
        Remove-Job $downloaderJob -ErrorAction SilentlyContinue
    }
    if ($botJob) {
        Stop-Job $botJob -ErrorAction SilentlyContinue
        Remove-Job $botJob -ErrorAction SilentlyContinue
    }
} 