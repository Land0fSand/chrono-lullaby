# -*- coding: utf-8 -*-
# ChronoLullaby 日志查看工具
# 用于查看和过滤 JSONL 格式的日志

param(
    [Parameter(Position = 0)]
    [string]$Component = "all",  # 组件: bot, downloader, launcher, all
    
    [Parameter()]
    [string]$Level = "",  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    [Parameter()]
    [int]$Last = 0,  # 显示最后 N 行
    
    [Parameter()]
    [string]$Filter = "",  # 消息过滤关键词
    
    [Parameter()]
    [switch]$Follow,  # 实时跟踪日志（类似 tail -f）
    
    [Parameter()]
    [switch]$Raw,  # 显示原始 JSON 格式
    
    [Parameter()]
    [switch]$ErrorOnly,  # 只显示错误
    
    [Parameter()]
    [switch]$Stats  # 显示日志统计信息
)

# 确保在项目根目录
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$LogsDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $LogsDir)) {
    Write-Host "错误: 日志目录不存在 $LogsDir" -ForegroundColor Red
    exit 1
}

# 根据组件选择日志文件
$LogFiles = @()
if ($Component -eq "all") {
    $LogFiles = Get-ChildItem -Path $LogsDir -Filter "*.log" | Where-Object { $_.Name -notlike "*error.log" }
}
elseif ($Component -eq "bot") {
    $LogFiles = @(Get-Item (Join-Path $LogsDir "bot.log") -ErrorAction SilentlyContinue)
}
elseif ($Component -eq "downloader") {
    $LogFiles = @(Get-Item (Join-Path $LogsDir "downloader.log") -ErrorAction SilentlyContinue)
}
elseif ($Component -eq "launcher") {
    $LogFiles = @(Get-Item (Join-Path $LogsDir "launcher.log") -ErrorAction SilentlyContinue)
}
else {
    Write-Host "错误: 未知组件 '$Component'。可选: bot, downloader, launcher, all" -ForegroundColor Red
    exit 1
}

$LogFiles = $LogFiles | Where-Object { $_ -ne $null -and $_.Exists }

if ($LogFiles.Count -eq 0) {
    Write-Host "错误: 未找到日志文件" -ForegroundColor Yellow
    Write-Host "提示: 请先运行程序生成日志" -ForegroundColor Gray
    exit 1
}

# 颜色映射
function Get-LevelColor($level) {
    switch ($level) {
        "DEBUG" { return "Cyan" }
        "INFO" { return "Green" }
        "WARNING" { return "Yellow" }
        "ERROR" { return "Red" }
        "CRITICAL" { return "Magenta" }
        default { return "White" }
    }
}

# 格式化显示日志行
function Format-LogLine($logEntry) {
    if ($Raw) {
        return $logEntry | ConvertTo-Json -Compress
    }
    
    $timestamp = $logEntry.timestamp
    $level = $logEntry.level
    $component = $logEntry.component
    $message = $logEntry.message
    
    $levelColor = Get-LevelColor $level
    
    # 提取时间部分（去掉毫秒）
    $time = $timestamp -replace 'T', ' ' -replace '\.\d+', ''
    
    # 构建输出行
    $line = "$time | "
    Write-Host $line -NoNewline
    Write-Host ("{0,-8}" -f $level) -ForegroundColor $levelColor -NoNewline
    Write-Host " | " -NoNewline
    Write-Host ("{0,-20}" -f $component) -NoNewline -ForegroundColor DarkGray
    Write-Host " | " -NoNewline
    Write-Host $message
    
    # 如果有额外数据，缩进显示
    $logEntry.PSObject.Properties | Where-Object { 
        $_.Name -notin @('timestamp', 'level', 'component', 'message', 'process', 'thread') 
    } | ForEach-Object {
        Write-Host "    " -NoNewline
        Write-Host "$($_.Name): " -NoNewline -ForegroundColor DarkGray
        Write-Host $_.Value -ForegroundColor Gray
    }
}

# 统计信息
function Show-Stats($logs) {
    $total = $logs.Count
    $byLevel = $logs | Group-Object -Property level | Sort-Object Count -Descending
    $byComponent = $logs | Group-Object -Property component | Sort-Object Count -Descending
    
    Write-Host "`n=== 日志统计 ===" -ForegroundColor Cyan
    Write-Host "总日志数: $total`n" -ForegroundColor White
    
    Write-Host "按级别统计:" -ForegroundColor Yellow
    foreach ($group in $byLevel) {
        $color = Get-LevelColor $group.Name
        $percent = [math]::Round(($group.Count / $total) * 100, 1)
        Write-Host ("  {0,-10}: {1,6} ({2,5}%)" -f $group.Name, $group.Count, $percent) -ForegroundColor $color
    }
    
    Write-Host "`n按组件统计:" -ForegroundColor Yellow
    foreach ($group in $byComponent) {
        $percent = [math]::Round(($group.Count / $total) * 100, 1)
        Write-Host ("  {0,-30}: {1,6} ({2,5}%)" -f $group.Name, $group.Count, $percent) -ForegroundColor Gray
    }
    Write-Host ""
}

# 读取和过滤日志
function Get-FilteredLogs {
    $allLogs = @()
    
    foreach ($file in $LogFiles) {
        Write-Verbose "读取日志文件: $($file.FullName)"
        $lines = Get-Content $file.FullName -Encoding UTF8 -ErrorAction SilentlyContinue
        
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            
            try {
                $logEntry = $line | ConvertFrom-Json
                
                # 应用过滤器
                if ($ErrorOnly -and $logEntry.level -notin @('ERROR', 'CRITICAL')) {
                    continue
                }
                
                if ($Level -and $logEntry.level -ne $Level) {
                    continue
                }
                
                if ($Filter -and $logEntry.message -notlike "*$Filter*") {
                    continue
                }
                
                $allLogs += $logEntry
            }
            catch {
                Write-Verbose "跳过无效的日志行: $line"
            }
        }
    }
    
    return $allLogs
}

# 主逻辑
Write-Host "=== ChronoLullaby 日志查看器 ===" -ForegroundColor Cyan
Write-Host "查看组件: $Component" -ForegroundColor Gray
if ($Level) { Write-Host "日志级别: $Level" -ForegroundColor Gray }
if ($Filter) { Write-Host "过滤关键词: $Filter" -ForegroundColor Gray }
Write-Host ""

if ($Follow) {
    Write-Host "实时跟踪模式 (按 Ctrl+C 退出)..." -ForegroundColor Yellow
    Write-Host ""
    
    # 获取初始文件大小
    $fileStates = @{}
    foreach ($file in $LogFiles) {
        $fileStates[$file.FullName] = (Get-Item $file.FullName).Length
    }
    
    while ($true) {
        foreach ($file in $LogFiles) {
            $currentSize = (Get-Item $file.FullName).Length
            $lastSize = $fileStates[$file.FullName]
            
            if ($currentSize -gt $lastSize) {
                # 读取新增的内容
                $newContent = Get-Content $file.FullName -Encoding UTF8 -Tail ([math]::Max(1, ($currentSize - $lastSize) / 100))
                
                foreach ($line in $newContent) {
                    if ([string]::IsNullOrWhiteSpace($line)) { continue }
                    
                    try {
                        $logEntry = $line | ConvertFrom-Json
                        
                        # 应用过滤器
                        if ($ErrorOnly -and $logEntry.level -notin @('ERROR', 'CRITICAL')) { continue }
                        if ($Level -and $logEntry.level -ne $Level) { continue }
                        if ($Filter -and $logEntry.message -notlike "*$Filter*") { continue }
                        
                        Format-LogLine $logEntry
                    }
                    catch {
                        # 忽略解析错误
                    }
                }
                
                $fileStates[$file.FullName] = $currentSize
            }
        }
        
        Start-Sleep -Milliseconds 500
    }
}
else {
    $logs = Get-FilteredLogs
    
    if ($Stats) {
        Show-Stats $logs
        exit 0
    }
    
    if ($logs.Count -eq 0) {
        Write-Host "未找到匹配的日志" -ForegroundColor Yellow
        exit 0
    }
    
    # 应用 Last 参数
    if ($Last -gt 0) {
        $logs = $logs | Select-Object -Last $Last
    }
    
    # 显示日志
    foreach ($log in $logs) {
        Format-LogLine $log
    }
    
    Write-Host "`n共 $($logs.Count) 条日志" -ForegroundColor Gray
}

