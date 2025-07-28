#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 状态检查 ===" -ForegroundColor Green
Write-Host ""

function Check-ProcessStatus {
    param (
        [int]$ProcessId,
        [string]$ProcessName
    )
    
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($process) {
            $uptime = (Get-Date) - $process.StartTime
            Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Green
            Write-Host "  状态: 运行中" -ForegroundColor Green
            Write-Host "  运行时间: $($uptime.ToString('hh\:mm\:ss'))" -ForegroundColor White
            Write-Host "  CPU 使用: $($process.CPU.ToString('F2'))秒" -ForegroundColor White
            Write-Host "  内存使用: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
            return $true
        }
        else {
            Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Red
            Write-Host "  状态: 未运行" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Red
        Write-Host "  状态: 检查失败 - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# 检查进程信息文件
if (Test-Path "process_info.json") {
    try {
        $processInfo = Get-Content "process_info.json" | ConvertFrom-Json
        
        Write-Host "从进程信息文件读取状态:" -ForegroundColor Cyan
        Write-Host "启动时间: $($processInfo.start_time)" -ForegroundColor White
        
        # 显示日志信息
        if ($processInfo.downloader_log) {
            Write-Host "下载器日志: $($processInfo.downloader_log)" -ForegroundColor Gray
        }
        if ($processInfo.bot_log) {
            Write-Host "机器人日志: $($processInfo.bot_log)" -ForegroundColor Gray
        }
        Write-Host ""
        
        $downloaderRunning = Check-ProcessStatus -ProcessId $processInfo.downloader_pid -ProcessName "YouTube 下载器"
        Write-Host ""
        $botRunning = Check-ProcessStatus -ProcessId $processInfo.bot_pid -ProcessName "Telegram 机器人"
        Write-Host ""
        
        if ($downloaderRunning -and $botRunning) {
            Write-Host "✅ 所有服务运行正常" -ForegroundColor Green
        }
        elseif ($downloaderRunning -or $botRunning) {
            Write-Host "⚠️  部分服务运行异常" -ForegroundColor Yellow
        }
        else {
            Write-Host "❌ 所有服务都未运行" -ForegroundColor Red
        }
        
    }
    catch {
        Write-Host "读取进程信息文件时出错: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "未找到进程信息文件，手动搜索相关进程..." -ForegroundColor Yellow
    Write-Host ""
    
    # 搜索相关的Poetry和Python进程
    $allProcesses = @()
    $allProcesses += Get-Process -Name "poetry*" -ErrorAction SilentlyContinue
    $allProcesses += Get-Process -Name "python*" -ErrorAction SilentlyContinue
    $foundProcesses = $false
    
    foreach ($process in $allProcesses) {
        try {
            # 尝试获取命令行参数（可能需要管理员权限）
            $commandLine = $process.CommandLine
            if ($commandLine -like "*yt_dlp_downloader.py*") {
                Write-Host "找到 YouTube 下载器进程:" -ForegroundColor Green
                Write-Host "  进程名: $($process.ProcessName)" -ForegroundColor White
                Write-Host "  PID: $($process.Id)" -ForegroundColor White
                Write-Host "  内存: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                $foundProcesses = $true
            }
            elseif ($commandLine -like "*telegram_bot.py*") {
                Write-Host "找到 Telegram 机器人进程:" -ForegroundColor Green
                Write-Host "  进程名: $($process.ProcessName)" -ForegroundColor White
                Write-Host "  PID: $($process.Id)" -ForegroundColor White
                Write-Host "  内存: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                $foundProcesses = $true
            }
        }
        catch {
            # 无法获取命令行信息，可能权限不足
        }
    }
    
    if (-not $foundProcesses) {
        Write-Host "未找到相关的 Poetry/Python 进程" -ForegroundColor Yellow
        Write-Host "提示: 如果进程正在运行，可能需要管理员权限来查看详细信息" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "状态检查完成" -ForegroundColor Green 