#!/usr/bin/env pwsh

# ChronoLullaby 自动日志清理脚本
# 
# 用途：定期清理 Notion 日志数据库中的旧日志
# 建议：将此脚本添加到 Windows 任务计划程序，每周执行一次
#
# 使用方法：
#   1. 直接运行：.\scripts\auto-clean-logs.ps1
#   2. 自定义参数：.\scripts\auto-clean-logs.ps1 -Days 60 -Levels INFO,WARNING
#   3. 添加到任务计划程序：
#      程序：pwsh.exe
#      参数：-File "完整路径\auto-clean-logs.ps1"

param(
    [int]$Days = 30,  # 保留最近 N 天的日志
    [string[]]$Levels = @("INFO"),  # 只清理指定级别，默认只清理 INFO
    [switch]$DryRun = $false  # 预览模式，不实际删除
)

# 获取项目根目录
$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $scriptDir

# 切换到项目目录
Push-Location $projectRoot

try {
    Write-Host "=" * 70 -ForegroundColor Gray
    Write-Host "  ChronoLullaby 自动日志清理" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Gray
    Write-Host ""
    Write-Host "执行时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "清理策略:" -ForegroundColor Cyan
    Write-Host "  - 保留最近 $Days 天的日志" -ForegroundColor Gray
    Write-Host "  - 只清理级别: $($Levels -join ', ')" -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "  - 模式: 预览（不实际删除）" -ForegroundColor Yellow
    } else {
        Write-Host "  - 模式: 实际删除" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # 构建命令参数
    $arguments = @("clean-notion-logs", "--days", $Days)
    
    if ($Levels.Count -gt 0) {
        $arguments += "--levels"
        $arguments += $Levels
    }
    
    if (-not $DryRun) {
        $arguments += "--confirm"
    }
    
    # 执行清理
    Write-Host "执行命令: ch $($arguments -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    & "$projectRoot\scripts\ch.ps1" @arguments
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Gray
    
    if ($exitCode -eq 0) {
        Write-Host "✅ 清理完成" -ForegroundColor Green
        
        # 记录清理日志
        $logFile = "$projectRoot\logs\auto_clean_history.log"
        $logDir = Split-Path $logFile -Parent
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        
        $logEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 清理完成 - Days: $Days, Levels: $($Levels -join ','), DryRun: $DryRun"
        Add-Content -Path $logFile -Value $logEntry
        
        Write-Host "清理记录已保存到: $logFile" -ForegroundColor Gray
    } else {
        Write-Host "❌ 清理失败，退出码: $exitCode" -ForegroundColor Red
        exit $exitCode
    }
    
    Write-Host "=" * 70 -ForegroundColor Gray
}
catch {
    Write-Host ""
    Write-Host "❌ 发生错误: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}

