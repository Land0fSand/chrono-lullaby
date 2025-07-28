#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 停止脚本 ===" -ForegroundColor Green

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

# 查找项目根目录
$projectRoot = Find-ProjectRoot
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

Write-Host "停止操作完成" -ForegroundColor Green 