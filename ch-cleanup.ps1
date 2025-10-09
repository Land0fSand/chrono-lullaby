#!/usr/bin/env pwsh

Write-Host "=== ChronoLullaby 超级强制清理脚本 ===" -ForegroundColor Green
Write-Host "🔥 超级模式：将强制终止所有相关进程" -ForegroundColor Red
Write-Host "⚠️ 此脚本会终止所有Python/Poetry进程，可能影响其他项目" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "确认要执行超级清理吗？(yes/no)"
if ($confirmation -ne "yes" -and $confirmation -ne "y") {
    Write-Host "操作已取消" -ForegroundColor Yellow
    exit 0
}

$stopped = 0

# 超级模式：强制终止所有相关进程
Write-Host "🔍 查找所有Python和Poetry进程..." -ForegroundColor Cyan

# 查找所有poetry进程
$poetryProcesses = Get-Process -Name "poetry*" -ErrorAction SilentlyContinue
if ($poetryProcesses) {
    foreach ($process in $poetryProcesses) {
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "💀 强制终止: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Red
            $stopped++
        }
        catch {
            Write-Host "❌ 无法终止 $($process.ProcessName) (PID: $($process.Id)): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# 查找所有python进程
$pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    foreach ($process in $pythonProcesses) {
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "💀 强制终止: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Red
            $stopped++
        }
        catch {
            Write-Host "❌ 无法终止 $($process.ProcessName) (PID: $($process.Id)): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# 查找所有cmd进程
$cmdProcesses = Get-Process -Name "cmd*" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and ($_.CommandLine -like "*python*" -or $_.CommandLine -like "*poetry*" -or $_.CommandLine -like "*chronolullaby*")
}
if ($cmdProcesses) {
    foreach ($process in $cmdProcesses) {
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "💀 强制终止: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Red
            $stopped++
        }
        catch {
            Write-Host "❌ 无法终止 $($process.ProcessName) (PID: $($process.Id)): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# 清理进程信息文件
Write-Host "🧹 清理进程信息文件..." -ForegroundColor Cyan
$possiblePaths = @(".", (Split-Path $MyInvocation.MyCommand.Path -Parent))
foreach ($path in $possiblePaths) {
    $file = Join-Path $path "process_info.json"
    if (Test-Path $file) {
        try {
            Remove-Item $file -Force
            Write-Host "✅ 已删除: $file" -ForegroundColor Green
        }
        catch {
            Write-Host "❌ 无法删除: $file - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# 尝试清理日志文件
Write-Host "📁 等待文件释放..." -ForegroundColor Cyan
Start-Sleep -Seconds 3  # 多等待一会儿，因为是超级清理模式

Write-Host "📁 尝试清理日志文件..." -ForegroundColor Cyan
try {
    $possiblePaths = @(".", (Split-Path $MyInvocation.MyCommand.Path -Parent))
    $totalDeleted = 0
    $totalFailed = 0
    
    foreach ($path in $possiblePaths) {
        $logDir = Join-Path $path "logs"
        if (Test-Path $logDir) {
            $logFiles = Get-ChildItem -Path $logDir -File -ErrorAction SilentlyContinue
            foreach ($file in $logFiles) {
                try {
                    Remove-Item $file.FullName -Force -ErrorAction Stop
                    $totalDeleted++
                }
                catch {
                    $totalFailed++
                    # 静默失败，避免刷屏
                }
            }
        }
    }
    
    if ($totalDeleted -gt 0) {
        Write-Host "✅ 已删除 $totalDeleted 个日志文件" -ForegroundColor Green
    }
    if ($totalFailed -gt 0) {
        Write-Host "⚠️ 有 $totalFailed 个日志文件无法删除" -ForegroundColor Yellow
        Write-Host "💡 建议手动删除 logs 目录，或稍后重试" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "⚠️ 日志清理出错: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 强制结束可能残留的进程
Write-Host "🔥 最终清理..." -ForegroundColor Red
@("poetry*", "python*", "cmd*") | ForEach-Object {
    Get-Process -Name $_ -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*yt_dlp*" -or $_.CommandLine -like "*telegram*" -or $_.CommandLine -like "*chronolullaby*")
    } | ForEach-Object {
        try {
            Stop-Process -Id $_.Id -Force
            Write-Host "💀 最终终止: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Red
        }
        catch {
            Write-Host "❌ 最终终止失败: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "🔥 超级清理完成！" -ForegroundColor Green
Write-Host "💀 强制终止了 $stopped 个进程" -ForegroundColor Red
Write-Host "⚠️ 所有Python/Poetry进程已被强制终止" -ForegroundColor Yellow
Write-Host "💡 现在可以安全删除任何日志文件" -ForegroundColor Cyan
Write-Host "🎯 建议等待30秒后重新启动系统" -ForegroundColor Cyan 