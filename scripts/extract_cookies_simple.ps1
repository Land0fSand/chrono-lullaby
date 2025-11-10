# YouTube Cookies 提取工具

Write-Host "=== YouTube Cookies 提取工具 ===" -ForegroundColor Green
Write-Host ""

# 关闭 Chrome
Write-Host "正在关闭 Chrome..." -ForegroundColor Cyan
Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Host "Chrome 已关闭" -ForegroundColor Green
Write-Host ""

# 提取 cookies
Write-Host "正在从 Chrome 提取 Cookies..." -ForegroundColor Cyan
yt-dlp --cookies-from-browser chrome --cookies "config/youtube.cookies" "https://www.youtube.com"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "提取成功!" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步: .\ch restart" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "提取失败" -ForegroundColor Red
    Write-Host "请手动使用 Cookie-Editor 扩展导出" -ForegroundColor Yellow
}

