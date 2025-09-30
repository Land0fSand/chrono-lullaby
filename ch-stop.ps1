#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 强制停止脚本 ===" -ForegroundColor Green
Write-Host "此脚本将强制停止所有相关进程，包括子进程和僵尸进程" -ForegroundColor Yellow
Write-Host "如果日志文件删除失败，可以使用 'ch-cleanup' 脚本" -ForegroundColor Cyan

function Find-ProjectRoot {
    # 首先检查当前目录是否有process_info.json
    if (Test-Path "process_info.json") {
        return (Get-Location).Path
    }

    # 检查脚本所在目录
    $scriptPath = $MyInvocation.MyCommand.Path
    if ($scriptPath) {
        $scriptDir = Split-Path $scriptPath -Parent
        if (Test-Path (Join-Path $scriptDir "process_info.json")) {
            return $scriptDir
        }
    }

    # 如果都找不到，返回null
    return $null
}

function Get-AllRelatedProcesses {
    param (
        [string[]]$Keywords = @("yt_dlp_downloader.py", "telegram_bot.py", "chronolullaby")
    )

    $allProcesses = @()

    # 查找poetry进程
    $poetryProcesses = Get-Process -Name "poetry*" -ErrorAction SilentlyContinue | Where-Object {
        if ($_.CommandLine) {
            $found = $false
            foreach ($keyword in $Keywords) {
                if ($_.CommandLine -like "*$keyword*") {
                    $found = $true
                    break
                }
            }
            return $found
        }
        return $false
    }
    $allProcesses += $poetryProcesses

    # 查找python进程
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        if ($_.CommandLine) {
            $found = $false
            foreach ($keyword in $Keywords) {
                if ($_.CommandLine -like "*$keyword*") {
                    $found = $true
                    break
                }
            }
            return $found
        }
        return $false
    }
    $allProcesses += $pythonProcesses

    # 查找cmd进程（可能包含子进程）
    $cmdProcesses = Get-Process -Name "cmd*" -ErrorAction SilentlyContinue | Where-Object {
        if ($_.CommandLine) {
            $found = $false
            foreach ($keyword in $Keywords) {
                if ($_.CommandLine -like "*$keyword*") {
                    $found = $true
                    break
                }
            }
            return $found
        }
        return $false
    }
    $allProcesses += $cmdProcesses

    return $allProcesses
}

# 查找项目根目录
$projectRoot = Find-ProjectRoot
$stoppedCount = 0

Write-Host "🔍 查找所有相关进程..." -ForegroundColor Cyan
$allProcesses = Get-AllRelatedProcesses

if ($allProcesses.Count -gt 0) {
    Write-Host "发现 $($allProcesses.Count) 个相关进程" -ForegroundColor Yellow

    foreach ($process in $allProcesses) {
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-Host "✅ 已停止: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Green
            $stoppedCount++
        }
        catch {
            Write-Host "❌ 停止 $($process.ProcessName) (PID: $($process.Id)) 时出错: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}
else {
    Write-Host "ℹ️ 未找到相关进程" -ForegroundColor Gray
}

if (-not $projectRoot) {
    Write-Host "❌ 未找到项目目录或进程信息文件" -ForegroundColor Red
    Write-Host "将尝试通过进程名称搜索..." -ForegroundColor Yellow

    # 通过进程名称查找并停止 (包括poetry进程和python进程)
    $relevantProcesses = @()

    # 查找poetry进程
    $poetryProcesses = Get-Process -Name "poetry*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*yt_dlp_downloader.py*" -or $_.CommandLine -like "*telegram_bot.py*")
    }
    $relevantProcesses += $poetryProcesses

    # 查找python进程
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*yt_dlp_downloader.py*" -or $_.CommandLine -like "*telegram_bot.py*")
    }
    $relevantProcesses += $pythonProcesses

    if ($relevantProcesses) {
        foreach ($process in $relevantProcesses) {
            try {
                Stop-Process -Id $process.Id -Force
                Write-Host "已停止进程 PID: $($process.Id) ($($process.ProcessName))" -ForegroundColor Green
            }
            catch {
                Write-Host "停止进程 PID: $($process.Id) 时出错: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "未找到相关的 Poetry/Python 进程" -ForegroundColor Yellow
    }

    Write-Host "停止操作完成" -ForegroundColor Green
    exit 0
}

$processInfoPath = Join-Path $projectRoot "process_info.json"

# 检查进程信息文件
if (Test-Path $processInfoPath) {
    try {
        $processInfo = Get-Content $processInfoPath | ConvertFrom-Json
        
        Write-Host "从进程信息文件中读取 PID..." -ForegroundColor Cyan
        Write-Host "项目目录: $($processInfo.project_root)" -ForegroundColor Gray
        
        # 停止下载器进程
        if ($processInfo.downloader_pid) {
            try {
                $process = Get-Process -Id $processInfo.downloader_pid -ErrorAction SilentlyContinue
                if ($process) {
                    Stop-Process -Id $processInfo.downloader_pid -Force
                    Write-Host "YouTube 下载器 (PID: $($processInfo.downloader_pid)) 已停止" -ForegroundColor Green
                }
                else {
                    Write-Host "YouTube 下载器进程已不存在" -ForegroundColor Yellow
                }
            }
            catch {
                Write-Host "停止 YouTube 下载器时出错: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        # 停止机器人进程
        if ($processInfo.bot_pid) {
            try {
                $process = Get-Process -Id $processInfo.bot_pid -ErrorAction SilentlyContinue
                if ($process) {
                    Stop-Process -Id $processInfo.bot_pid -Force
                    Write-Host "Telegram 机器人 (PID: $($processInfo.bot_pid)) 已停止" -ForegroundColor Green
                }
                else {
                    Write-Host "Telegram 机器人进程已不存在" -ForegroundColor Yellow
                }
            }
            catch {
                Write-Host "停止 Telegram 机器人时出错: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        # 删除进程信息文件
        Remove-Item $processInfoPath -Force
        Write-Host "已清理进程信息文件" -ForegroundColor Green
        
    }
    catch {
        Write-Host "读取进程信息文件时出错: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "未找到进程信息文件，尝试通过进程名称查找..." -ForegroundColor Yellow
    
    # 通过进程名称查找并停止 (包括poetry进程和python进程)
    $relevantProcesses = @()
    
    # 查找poetry进程
    $poetryProcesses = Get-Process -Name "poetry*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*yt_dlp_downloader.py*" -or $_.CommandLine -like "*telegram_bot.py*")
    }
    $relevantProcesses += $poetryProcesses
    
    # 查找python进程
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*yt_dlp_downloader.py*" -or $_.CommandLine -like "*telegram_bot.py*")
    }
    $relevantProcesses += $pythonProcesses
    
    if ($relevantProcesses) {
        foreach ($process in $relevantProcesses) {
            try {
                Stop-Process -Id $process.Id -Force
                Write-Host "已停止进程 PID: $($process.Id) ($($process.ProcessName))" -ForegroundColor Green
            }
            catch {
                Write-Host "停止进程 PID: $($process.Id) 时出错: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "未找到相关的 Poetry/Python 进程" -ForegroundColor Yellow
    }
}

# 清理日志文件（如果有权限问题）
Write-Host "🧹 尝试清理日志文件..." -ForegroundColor Cyan
try {
    $logDir = Join-Path $projectRoot "logs"
    if (Test-Path $logDir) {
        $logFiles = Get-ChildItem -Path $logDir -File -ErrorAction SilentlyContinue
        foreach ($file in $logFiles) {
            try {
                # 尝试关闭可能占用的文件句柄
                $file.Close()
                Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
                Write-Host "✅ 已删除日志文件: $($file.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ 无法删除日志文件 $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}
catch {
    Write-Host "⚠️ 日志文件清理过程中出错: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "🎯 停止操作完成 - 共停止了 $stoppedCount 个进程" -ForegroundColor Green
if ($stoppedCount -gt 0) {
    Write-Host "✅ 所有相关进程已停止" -ForegroundColor Green
    Write-Host "💡 现在可以安全删除日志文件了" -ForegroundColor Cyan
}
else {
    Write-Host "⚠️ 未找到相关进程，可能需要使用 'ch-cleanup' 强制清理" -ForegroundColor Yellow
}
Write-Host "💡 建议等待10秒后重新启动" -ForegroundColor Cyan 