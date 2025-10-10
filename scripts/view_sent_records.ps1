# 查看各个频道的发送记录

param(
    [string]$ChatId,
    [int]$Tail = 0,
    [switch]$All
)

$dataDir = Join-Path $PSScriptRoot "..\data"

# 定义频道映射
$channels = @{
    "1002441077579" = "唏噓電臺"
    "1003009234603" = "唏噓電臺Beta"
    "1003128921390" = "唏噓電臺Beta2"
}

function Show-ChannelRecords {
    param(
        [string]$CleanChatId,
        [string]$ChannelName
    )
    
    $readableFile = Join-Path $dataDir "sent_archive_${CleanChatId}_readable.txt"
    $machineFile = Join-Path $dataDir "sent_archive_${CleanChatId}.txt"
    
    Write-Host "`n================================================" -ForegroundColor Cyan
    Write-Host "频道: $ChannelName (Chat ID: $CleanChatId)" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    
    if (Test-Path $readableFile) {
        $lines = Get-Content $readableFile -Encoding UTF8
        $count = $lines.Count
        Write-Host "总发送数量: $count 个视频`n" -ForegroundColor Green
        
        if ($Tail -gt 0) {
            $lines = $lines | Select-Object -Last $Tail
            Write-Host "显示最近 $Tail 条记录:" -ForegroundColor Yellow
        }
        
        $lines | ForEach-Object {
            Write-Host $_
        }
    } else {
        Write-Host "❌ 未找到发送记录文件" -ForegroundColor Red
        Write-Host "   预期位置: $readableFile" -ForegroundColor Gray
    }
}

Write-Host @"

╔═══════════════════════════════════════════════╗
║   ChronoLullaby - 频道发送记录查看器          ║
╚═══════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

if ($ChatId) {
    # 清理 ChatId
    $cleanId = $ChatId -replace '[-+]', ''
    $channelName = if ($channels.ContainsKey($cleanId)) { $channels[$cleanId] } else { "未知频道" }
    Show-ChannelRecords -CleanChatId $cleanId -ChannelName $channelName
}
elseif ($All) {
    # 显示所有频道
    foreach ($id in $channels.Keys) {
        Show-ChannelRecords -CleanChatId $id -ChannelName $channels[$id]
    }
}
else {
    # 显示帮助信息
    Write-Host "用法:" -ForegroundColor Yellow
    Write-Host "  .\scripts\view_sent_records.ps1 -ChatId <频道ID>  # 查看特定频道" -ForegroundColor White
    Write-Host "  .\scripts\view_sent_records.ps1 -All              # 查看所有频道" -ForegroundColor White
    Write-Host "  .\scripts\view_sent_records.ps1 -ChatId <ID> -Tail 10  # 只看最近10条" -ForegroundColor White
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Yellow
    Write-Host "  .\scripts\view_sent_records.ps1 -ChatId -1002441077579" -ForegroundColor Gray
    Write-Host "  .\scripts\view_sent_records.ps1 -All -Tail 5" -ForegroundColor Gray
    Write-Host ""
    Write-Host "可用频道:" -ForegroundColor Yellow
    foreach ($id in $channels.Keys) {
        Write-Host "  -$id : $($channels[$id])" -ForegroundColor White
    }
}

Write-Host ""

