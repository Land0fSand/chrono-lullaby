#!/usr/bin/env pwsh

param(
    [string]$Type = "all",     # all, downloader, bot, error
    [int]$Lines = 50,          # 显示的行数
    [switch]$Follow,           # 实时跟踪
    [switch]$List             # 列出所有日志文件
)

Write-Host "=== ChronoLullaby 日志查看器 ===" -ForegroundColor Green

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
    Write-Host "请确保:" -ForegroundColor Yellow
    Write-Host "  1. 已经运行过 'ch' 启动脚本" -ForegroundColor Gray
    Write-Host "  2. 或者在项目根目录运行此命令" -ForegroundColor Gray
    exit 1
}

$logDir = Join-Path $projectRoot "logs"

# 检查日志目录是否存在
if (-not (Test-Path $logDir)) {
    Write-Host "❌ 日志目录不存在: $logDir" -ForegroundColor Red
    Write-Host "请先使用 'ch' 启动程序" -ForegroundColor Yellow
    exit 1
}

# 列出所有日志文件
if ($List) {
    Write-Host "📁 可用的日志文件:" -ForegroundColor Cyan
    Write-Host ""
    
    $logFiles = Get-ChildItem -Path $logDir -Name "*.log" | Sort-Object -Descending
    if ($logFiles.Count -eq 0) {
        Write-Host "未找到日志文件" -ForegroundColor Yellow
    }
    else {
        foreach ($file in $logFiles) {
            $fullPath = Join-Path $logDir $file
            $size = [math]::Round((Get-Item $fullPath).Length / 1KB, 2)
            $modified = (Get-Item $fullPath).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            
            if ($file -like "*error*") {
                Write-Host "❌ $file (${size}KB, $modified)" -ForegroundColor Red
            }
            elseif ($file -like "*downloader*") {
                Write-Host "📥 $file (${size}KB, $modified)" -ForegroundColor Cyan
            }
            elseif ($file -like "*bot*") {
                Write-Host "🤖 $file (${size}KB, $modified)" -ForegroundColor Green
            }
            else {
                Write-Host "📄 $file (${size}KB, $modified)" -ForegroundColor White
            }
        }
    }
    exit 0
}

function Get-LatestLogFiles {
    $processInfoPath = Join-Path $projectRoot "process_info.json"
    
    if (Test-Path $processInfoPath) {
        try {
            $processInfo = Get-Content $processInfoPath | ConvertFrom-Json
            return @{
                "downloader_log"       = $processInfo.downloader_log
                "bot_log"              = $processInfo.bot_log
                "downloader_error_log" = $processInfo.downloader_error_log
                "bot_error_log"        = $processInfo.bot_error_log
            }
        }
        catch {
            Write-Host "⚠️  无法读取进程信息文件，将查找最新的日志文件" -ForegroundColor Yellow
        }
    }
    
    # 如果没有进程信息文件，查找最新的日志文件
    $latestDownloader = Get-ChildItem -Path $logDir -Name "downloader_*.log" | Where-Object { $_ -notlike "*error*" } | Sort-Object -Descending | Select-Object -First 1
    $latestBot = Get-ChildItem -Path $logDir -Name "bot_*.log" | Where-Object { $_ -notlike "*error*" } | Sort-Object -Descending | Select-Object -First 1
    $latestDownloaderError = Get-ChildItem -Path $logDir -Name "downloader_error_*.log" | Sort-Object -Descending | Select-Object -First 1
    $latestBotError = Get-ChildItem -Path $logDir -Name "bot_error_*.log" | Sort-Object -Descending | Select-Object -First 1
    
    return @{
        "downloader_log"       = if ($latestDownloader) { Join-Path $logDir $latestDownloader } else { $null }
        "bot_log"              = if ($latestBot) { Join-Path $logDir $latestBot } else { $null }
        "downloader_error_log" = if ($latestDownloaderError) { Join-Path $logDir $latestDownloaderError } else { $null }
        "bot_error_log"        = if ($latestBotError) { Join-Path $logDir $latestBotError } else { $null }
    }
}

function Show-Log {
    param(
        [string]$LogPath,
        [string]$LogName,
        [string]$Color = "White"
    )
    
    if (-not $LogPath -or -not (Test-Path $LogPath)) {
        Write-Host "❌ 日志文件不存在: $LogName" -ForegroundColor Red
        return
    }
    
    Write-Host "📄 $LogName ($LogPath)" -ForegroundColor $Color
    Write-Host "=" * 60 -ForegroundColor Gray
    
    if ($Follow) {
        Write-Host "实时跟踪日志 (按 Ctrl+C 停止)..." -ForegroundColor Yellow
        Get-Content $LogPath -Tail $Lines -Wait
    }
    else {
        Get-Content $LogPath -Tail $Lines
    }
    
    Write-Host ""
}

# 获取最新的日志文件
$logFiles = Get-LatestLogFiles

# 根据类型显示日志
switch ($Type.ToLower()) {
    "downloader" {
        Show-Log -LogPath $logFiles.downloader_log -LogName "YouTube 下载器日志" -Color "Cyan"
    }
    "bot" {
        Show-Log -LogPath $logFiles.bot_log -LogName "Telegram 机器人日志" -Color "Green"
    }
    "error" {
        Show-Log -LogPath $logFiles.downloader_error_log -LogName "下载器错误日志" -Color "Red"
        Show-Log -LogPath $logFiles.bot_error_log -LogName "机器人错误日志" -Color "Red"
    }
    "all" {
        Show-Log -LogPath $logFiles.downloader_log -LogName "YouTube 下载器日志" -Color "Cyan"
        Show-Log -LogPath $logFiles.bot_log -LogName "Telegram 机器人日志" -Color "Green"
        
        # 只有在有错误日志内容时才显示
        if ($logFiles.downloader_error_log -and (Test-Path $logFiles.downloader_error_log) -and (Get-Item $logFiles.downloader_error_log).Length -gt 0) {
            Show-Log -LogPath $logFiles.downloader_error_log -LogName "下载器错误日志" -Color "Red"
        }
        if ($logFiles.bot_error_log -and (Test-Path $logFiles.bot_error_log) -and (Get-Item $logFiles.bot_error_log).Length -gt 0) {
            Show-Log -LogPath $logFiles.bot_error_log -LogName "机器人错误日志" -Color "Red"
        }
    }  
    default {
        Write-Host "❌ 未知的日志类型: $Type" -ForegroundColor Red
        Write-Host "可用类型: all, downloader, bot, error" -ForegroundColor Yellow
        exit 1
    }
}

if (-not $Follow) {
    Write-Host "💡 使用参数:" -ForegroundColor Yellow
    Write-Host "  -Type <all|downloader|bot|error>  # 选择日志类型" -ForegroundColor Gray
    Write-Host "  -Lines <数字>                     # 显示行数 (默认50)" -ForegroundColor Gray
    Write-Host "  -Follow                           # 实时跟踪" -ForegroundColor Gray
    Write-Host "  -List                             # 列出所有日志文件" -ForegroundColor Gray
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Yellow
    Write-Host "  ch-logs -Type downloader -Follow    # 实时查看下载器日志" -ForegroundColor Gray
    Write-Host "  ch-logs -List                       # 列出所有日志" -ForegroundColor Gray
} 