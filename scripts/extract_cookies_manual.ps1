# 手动提取 Chrome Cookies 的辅助脚本

Write-Host "=== YouTube Cookies 提取工具 ===" -ForegroundColor Green
Write-Host ""

# 步骤 1: 检查并关闭 Chrome
Write-Host "步骤 1/4: 检查 Chrome 进程..." -ForegroundColor Cyan
$chromeProcesses = Get-Process -Name "chrome" -ErrorAction SilentlyContinue

if ($chromeProcesses) {
    Write-Host "  发现 $($chromeProcesses.Count) 个 Chrome 进程" -ForegroundColor Yellow
    Write-Host "  正在关闭所有 Chrome 进程..." -ForegroundColor Yellow
    
    Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    
    Write-Host "  ✅ Chrome 已关闭" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  Chrome 未运行" -ForegroundColor Gray
}

Write-Host ""

# 步骤 2: 清理可能的锁定文件
Write-Host "步骤 2/4: 清理临时文件..." -ForegroundColor Cyan

$tempDir = $env:TEMP
$cookieLocks = Get-ChildItem -Path $tempDir -Filter "*cookies*" -ErrorAction SilentlyContinue

if ($cookieLocks) {
    Write-Host "  清理 $($cookieLocks.Count) 个临时文件..." -ForegroundColor Yellow
    $cookieLocks | Remove-Item -Force -ErrorAction SilentlyContinue
}

Write-Host "  ✅ 清理完成" -ForegroundColor Green
Write-Host ""

# 步骤 3: 提取 cookies
Write-Host "步骤 3/4: 提取 Cookies..." -ForegroundColor Cyan
Write-Host "  正在从 Chrome 提取..." -ForegroundColor Yellow

$result = yt-dlp --cookies-from-browser chrome --cookies "config/youtube.cookies" "https://www.youtube.com" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Cookies 提取成功！" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  提取失败，错误信息：" -ForegroundColor Red
    Write-Host $result -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "  尝试备用方案：使用 Firefox..." -ForegroundColor Yellow
    $result = yt-dlp --cookies-from-browser firefox --cookies "config/youtube.cookies" "https://www.youtube.com" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ 从 Firefox 提取成功！" -ForegroundColor Green
    } else {
        Write-Host "  ❌ 提取失败" -ForegroundColor Red
        Write-Host ""
        Write-Host "替代方案：" -ForegroundColor Yellow
        Write-Host "1. 重启电脑后再次尝试" -ForegroundColor White
        Write-Host "2. 使用浏览器扩展手动导出 cookies" -ForegroundColor White
        Write-Host "   - 安装 Cookie-Editor 扩展" -ForegroundColor Gray
        Write-Host "   - 访问 youtube.com 并登录" -ForegroundColor Gray
        Write-Host "   - 导出为 Netscape 格式" -ForegroundColor Gray
        Write-Host "   - 保存到 config/youtube.cookies" -ForegroundColor Gray
        exit 1
    }
}

Write-Host ""

# 步骤 4: 验证
Write-Host "步骤 4/4: 验证 Cookies 文件..." -ForegroundColor Cyan

if (Test-Path "config/youtube.cookies") {
    $content = Get-Content "config/youtube.cookies" -Raw
    $lineCount = (Get-Content "config/youtube.cookies").Count
    
    if ($lineCount -gt 5 -and $content -like "*youtube.com*") {
        Write-Host "  ✅ Cookies 文件有效！" -ForegroundColor Green
        Write-Host "  包含 $lineCount 行数据" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  Cookies 文件可能不完整" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ Cookies 文件不存在" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 提取完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  .\ch restart" -ForegroundColor White
Write-Host ""

