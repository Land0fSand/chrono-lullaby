# 测试 data 目录自动创建功能
param([switch]$Test)

$projectRoot = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $projectRoot "data"

Write-Host "🔍 检查 data 目录状态..." -ForegroundColor Cyan

# 检查 data 目录是否存在
if (Test-Path $dataDir) {
    Write-Host "✅ data 目录已存在: $dataDir" -ForegroundColor Green
} else {
    Write-Host "❌ data 目录不存在: $dataDir" -ForegroundColor Red
}

# 测试 Python 程序是否能自动创建目录
Write-Host "🚀 测试 Python 程序自动创建 data 目录..." -ForegroundColor Cyan

try {
    # 临时删除 data 目录（如果存在）
    if (Test-Path $dataDir) {
        Write-Host "🗑️ 临时删除 data 目录进行测试..." -ForegroundColor Yellow
        Remove-Item $dataDir -Recurse -Force
    }

    # 运行一个简单的 Python 测试
    $pythonTest = @"
import os
import sys

# 添加项目路径
sys.path.insert(0, 'src')

# 导入配置模块，这应该会创建 data 目录
from config import get_config_value

# 尝试获取一个需要 data 目录的值
try:
    # 这会触发 _load_download_archive 或类似函数，创建 data 目录
    from config_provider import LocalConfigProvider
    provider = LocalConfigProvider('.', 'config/config.yaml')
    result = provider._load_download_archive()
    print("✅ Python 程序成功创建了 data 目录")
except Exception as e:
    print(f"❌ Python 程序创建 data 目录失败: {e}")

# 检查目录是否被创建
if os.path.exists('data'):
    print("✅ data 目录已被成功创建")
else:
    print("❌ data 目录未能被创建")
"@

    $pythonTest | Out-File -FilePath "test_data_dir.py" -Encoding UTF8

    python test_data_dir.py

    # 清理测试文件
    Remove-Item "test_data_dir.py" -ErrorAction SilentlyContinue

} catch {
    Write-Host "❌ 测试过程中出错: $($_.Exception.Message)" -ForegroundColor Red
}

# 最终检查
Write-Host "`n📊 最终检查:" -ForegroundColor Cyan
if (Test-Path $dataDir) {
    $items = Get-ChildItem $dataDir
    Write-Host "✅ data 目录存在，包含 $($items.Count) 个项目" -ForegroundColor Green
    $items | ForEach-Object {
        Write-Host "  $($_.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ data 目录仍然不存在" -ForegroundColor Red
}

Write-Host "`n✨ 测试完成！" -ForegroundColor Green
