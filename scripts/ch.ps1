#!/usr/bin/env pwsh

# ChronoLullaby 统一命令入口
# 用法: ch <command> [options]
# 全局安装说明：
#   1. 将此脚本复制到 PATH 目录，如：C:\Users\你的用户名\bin\
#   2. 或运行：Add-ChToPath 命令永久添加到环境变量
#   3. 然后就可以在任意目录运行：ch start, ch status, ch logs 等

param(
    [Parameter(Position = 0)]
    [string]$Command,
    [Parameter()]
    [Alias("m")]
    [string]$Mode = "",  # 配置模式：local 或 notion（支持 --mode 或 -m）
    [Parameter()]
    [Alias("r")]
    [string]$RunMode = "",  # 运行模式：python / auto（支持 --run-mode 或 -r）
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Arguments = @()
)

# 显示帮助信息
function Show-Help {
    Write-Host "=== ChronoLullaby 命令帮助 ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法: ch <命令> [选项]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "可用命令:" -ForegroundColor Cyan
    Write-Host "  start                    启动服务 (默认命令)" -ForegroundColor White
    Write-Host "  stop                     停止服务" -ForegroundColor White
    Write-Host "  restart                  重启服务 (停止后重新启动)" -ForegroundColor White
    Write-Host "  ensure-running           仅在服务未运行时启动" -ForegroundColor White
    Write-Host "  status                   查看服务状态" -ForegroundColor White
    Write-Host "  install-autostart        安装开机自启和保活计划任务" -ForegroundColor White
    Write-Host "  uninstall-autostart      删除开机自启和保活计划任务" -ForegroundColor White
    Write-Host "  autostart-status         查看计划任务状态" -ForegroundColor White
    Write-Host "  logs     [类型] [选项]   查看日志" -ForegroundColor White
    Write-Host "  cleanup                  强制清理所有进程" -ForegroundColor White
    Write-Host "  init-notion              初始化 Notion 数据库结构" -ForegroundColor White
    Write-Host "  sync-to-notion [--data <范围>]  手动同步数据到 Notion" -ForegroundColor White
    Write-Host "  clean-notion-logs [选项] 清理 Notion 日志数据库" -ForegroundColor White
    Write-Host "  migrate-multiselect      将 youtube_channels 字段迁移为 multi_select" -ForegroundColor White
    Write-Host "  ytdlp-watch [选项]       监控 yt-dlp 新版本并自动更新重启" -ForegroundColor White
    Write-Host "  add-chtopath             永久添加到系统 PATH" -ForegroundColor White
    Write-Host "  help                     显示此帮助信息" -ForegroundColor White
    Write-Host ""
    Write-Host "日志类型 (用于 logs 命令):" -ForegroundColor Cyan
    Write-Host "  all                      显示所有日志 (默认)" -ForegroundColor Gray
    Write-Host "  downloader               只显示下载器日志" -ForegroundColor Gray
    Write-Host "  bot                      只显示机器人日志" -ForegroundColor Gray
    Write-Host "  error                    只显示错误日志" -ForegroundColor Gray
    Write-Host ""
    Write-Host "通用选项:" -ForegroundColor Cyan
    Write-Host "  --help, -h               显示帮助信息" -ForegroundColor Gray
    Write-Host "  --version, -v            显示版本信息" -ForegroundColor Gray
    Write-Host ""
    Write-Host "日志选项 (用于 logs 命令):" -ForegroundColor Cyan
    Write-Host "  --lines <数字>           显示的行数 (默认50)" -ForegroundColor Gray
    Write-Host "  --follow, -f             实时跟踪日志" -ForegroundColor Gray
    Write-Host "  --list, -l               列出所有日志文件" -ForegroundColor Gray
    Write-Host ""
    Write-Host "启动选项:" -ForegroundColor Cyan
    Write-Host "  --mode, -m <模式>        指定配置模式 (local 或 notion)，优先于配置文件" -ForegroundColor Gray
    Write-Host "  --run-mode, -r <模式>    指定运行模式 (auto / python)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "ytdlp-watch 选项:" -ForegroundColor Cyan
    Write-Host "  --interval <分钟>        检查间隔，默认 15 分钟" -ForegroundColor Gray
    Write-Host "  --once                   只检查一次后退出" -ForegroundColor Gray
    Write-Host "  --dry-run                仅检测，不执行升级和重启" -ForegroundColor Gray
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Yellow
    Write-Host "  ch start                 # 启动服务（使用配置文件中的 mode）" -ForegroundColor Gray
    Write-Host "  ch start --mode notion   # 使用 Notion 模式启动（覆盖配置文件）" -ForegroundColor Gray
    Write-Host "  ch start -m notion       # 同上，使用短参数" -ForegroundColor Gray
    Write-Host "  ch start -r python       # 强制使用 Python 源码启动" -ForegroundColor Gray
    Write-Host "  ch restart -m notion -r python  # 用 Notion 模式重启并强制源码运行" -ForegroundColor Gray
    Write-Host "  ch stop                  # 停止服务" -ForegroundColor Gray
    Write-Host "  ch restart               # 重启服务" -ForegroundColor Gray
    Write-Host "  ch ensure-running        # 仅在服务未运行时启动" -ForegroundColor Gray
    Write-Host "  ch status                # 查看状态" -ForegroundColor Gray
    Write-Host "  ch install-autostart     # 安装开机自启和 15 分钟保活任务" -ForegroundColor Gray
    Write-Host "  ch autostart-status      # 查看计划任务状态" -ForegroundColor Gray
    Write-Host "  ch logs                  # 查看所有日志" -ForegroundColor Gray
    Write-Host "  ch logs downloader -f    # 实时查看下载器日志" -ForegroundColor Gray
    Write-Host "  ch logs --list           # 列出所有日志文件" -ForegroundColor Gray
    Write-Host "  ch init-notion           # 初始化 Notion 数据库" -ForegroundColor Gray
    Write-Host "  ch sync-to-notion --data config   # 同步配置到 Notion（支持 all/archive/logs）" -ForegroundColor Gray
    Write-Host "  ch clean-notion-logs --days 30    # 预览删除 30 天前的日志" -ForegroundColor Gray
    Write-Host "  ch clean-notion-logs --days 30 --confirm  # 实际删除 30 天前的日志" -ForegroundColor Gray
    Write-Host "  ch migrate-multiselect   # 迁移 youtube_channels 字段为 multi_select" -ForegroundColor Gray
    Write-Host "  ch ytdlp-watch -m notion # 监控新版本，检测到后自动升级并重启" -ForegroundColor Gray
    Write-Host "  ch ytdlp-watch --once --dry-run # 只检测一次，不执行变更" -ForegroundColor Gray
    Write-Host "  ch cleanup               # 强制清理" -ForegroundColor Gray
    Write-Host "  ch add-chtopath          # 永久添加到系统 PATH" -ForegroundColor Gray
}

# 显示版本信息
function Show-Version {
    Write-Host "ChronoLullaby v1.0.0" -ForegroundColor Green
    Write-Host "统一命令管理工具" -ForegroundColor Gray
}

# 永久添加到 PATH 的辅助函数
function Add-ChToPath {
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.ScriptName
    }
    $scriptDir = Split-Path $scriptPath -Parent

    try {
        # 检查是否需要管理员权限
        $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
        $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

        if (-not $isAdmin) {
            Write-Host "⚠️  需要管理员权限来永久修改环境变量" -ForegroundColor Yellow
            Write-Host "请以管理员身份运行 PowerShell，或手动将以下路径添加到 PATH:" -ForegroundColor Yellow
            Write-Host "  $scriptDir" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "手动添加步骤:" -ForegroundColor White
            Write-Host "1. 右键点击 '此电脑' -> 属性" -ForegroundColor Gray
            Write-Host "2. 点击 '高级系统设置' -> '环境变量'" -ForegroundColor Gray
            Write-Host "3. 在 '用户变量' 或 '系统变量' 中找到 Path" -ForegroundColor Gray
            Write-Host "4. 点击 '编辑' -> '新建'" -ForegroundColor Gray
            Write-Host "5. 添加: $scriptDir" -ForegroundColor Gray
            Write-Host "6. 点击确定保存" -ForegroundColor Gray
            return
        }

        # 获取当前用户环境变量
        $userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
        $pathArray = $userPath -split ';' | Where-Object { $_ -and $_.Trim() }

        # 检查是否已经存在
        if ($pathArray -contains $scriptDir) {
            Write-Host "✅ 项目目录已在 PATH 中: $scriptDir" -ForegroundColor Green
            return
        }

        # 添加到 PATH
        $newPath = $userPath + ';' + $scriptDir
        [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)

        Write-Host "✅ 已永久添加到用户 PATH: $scriptDir" -ForegroundColor Green
        Write-Host "💡 请重启 PowerShell 或新开命令窗口以使更改生效" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "添加成功后就可以在任意目录使用以下命令:" -ForegroundColor Cyan
        Write-Host "  ch start    # 启动服务" -ForegroundColor White
        Write-Host "  ch status   # 查看状态" -ForegroundColor White
        Write-Host "  ch logs     # 查看日志" -ForegroundColor White
        Write-Host "  ch stop     # 停止服务" -ForegroundColor White

    }
    catch {
        Write-Host "❌ 添加到 PATH 时出错: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "请手动将以下路径添加到环境变量:" -ForegroundColor Yellow
        Write-Host "  $scriptDir" -ForegroundColor Cyan
    }
}

# 获取脚本所在的绝对路径和项目根目录
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir = Split-Path $scriptPath -Parent
$projectRoot = Split-Path $scriptDir -Parent
$hiddenAutostartScript = Join-Path $scriptDir "ch-autostart-hidden.vbs"

# 检查虚拟环境或 uv
$venvPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$useVenv = Test-Path $venvPath

if (-not $useVenv -and -not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到虚拟环境或 uv" -ForegroundColor Red
    Write-Host "请运行以下命令之一来设置环境:" -ForegroundColor Yellow
    Write-Host "  1. 使用 uv: uv sync" -ForegroundColor Gray
    Write-Host "  2. 手动创建虚拟环境并安装依赖 (参见 README)" -ForegroundColor Gray
    exit 1
}

# 切换到项目根目录
Set-Location $projectRoot

# 检查是否在正确的项目目录（检查标志性文件：源码）
$hasSrc = (Test-Path "src/yt_dlp_downloader.py") -and (Test-Path "src/telegram_bot.py")
if (-not $hasSrc) {
    Write-Host "错误: 未找到项目源码，请确保脚本在正确的项目目录中" -ForegroundColor Red
    Write-Host "当前目录: $(Get-Location)" -ForegroundColor Red
    exit 1
}

# 如果没有提供命令，默认执行start
if (-not $Command) {
    $Command = "start"
}

function Invoke-ProjectPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code
    )

    if ($useVenv) {
        $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
        return & $pythonExe -c $Code
    }

    return uv run python -c $Code
}

function Invoke-ProjectYtDlpUpgrade {
    if ($useVenv) {
        $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
        return uv pip install --python $pythonExe -U --pre yt-dlp
    }

    return uv pip install -U --pre yt-dlp
}

function Get-YtDlpVersionInfo {
    $pythonCode = @'
import json
import urllib.request

result = {
    "ok": False,
    "installed": None,
    "latest": None,
    "update_available": False,
    "error": None,
}

try:
    from packaging.version import Version, InvalidVersion
    import yt_dlp

    installed = yt_dlp.version.__version__
    result["installed"] = installed

    with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=20) as resp:
        data = json.load(resp)

    versions = []
    for raw, files in (data.get("releases") or {}).items():
        if not files:
            continue
        try:
            parsed = Version(raw)
        except InvalidVersion:
            continue
        versions.append((parsed, raw))

    if not versions:
        raise RuntimeError("未从 PyPI 获取到可用版本列表")

    versions.sort(key=lambda x: x[0])
    latest = versions[-1][1]

    result["latest"] = latest
    result["update_available"] = Version(installed) < Version(latest)
    result["ok"] = True
except Exception as exc:
    result["error"] = str(exc)

print(json.dumps(result, ensure_ascii=False))
'@

    try {
        $raw = Invoke-ProjectPython -Code $pythonCode 2>&1
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{
                ok = $false
                installed = $null
                latest = $null
                update_available = $false
                error = ($raw -join "`n")
            }
        }

        $lastLine = ($raw | Select-Object -Last 1)
        return $lastLine | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            ok = $false
            installed = $null
            latest = $null
            update_available = $false
            error = $_.Exception.Message
        }
    }
}

function Get-ServiceProcessSnapshot {
    $processInfoPath = Join-Path $projectRoot "data/process_info.json"
    $result = @{
        process_info_path = $processInfoPath
        info = $null
        effective_launcher_pid = $null
        effective_downloader_pid = $null
        effective_bot_pid = $null
        launcher_running = $false
        downloader_running = $false
        bot_running = $false
    }

    if (-not (Test-Path $processInfoPath)) {
        return [pscustomobject]$result
    }

    try {
        $info = Get-Content $processInfoPath | ConvertFrom-Json
        $result.info = $info
        if ($info.launcher_pid) {
            $result.effective_launcher_pid = Get-EffectiveTrackedPid -RootPid $info.launcher_pid -Pattern "launcher.py"
            $result.launcher_running = [bool](Get-Process -Id $result.effective_launcher_pid -ErrorAction SilentlyContinue)
        }
        if ($info.downloader_pid) {
            $result.effective_downloader_pid = Get-EffectiveTrackedPid -RootPid $info.downloader_pid -Pattern "yt_dlp_downloader.py"
            $result.downloader_running = [bool](Get-Process -Id $result.effective_downloader_pid -ErrorAction SilentlyContinue)
        }
        if ($info.bot_pid) {
            $result.effective_bot_pid = Get-EffectiveTrackedPid -RootPid $info.bot_pid -Pattern "telegram_bot.py"
            $result.bot_running = [bool](Get-Process -Id $result.effective_bot_pid -ErrorAction SilentlyContinue)
        }
    }
    catch {
        return [pscustomobject]$result
    }

    return [pscustomobject]$result
}

function Test-ServiceHealthy {
    $snapshot = Get-ServiceProcessSnapshot
    return ($snapshot.downloader_running -and $snapshot.bot_running)
}

function Get-TrackedPythonProcesses {
    try {
        return @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq "python.exe" -and (
                $_.CommandLine -like "*launcher.py*" -or
                $_.CommandLine -like "*yt_dlp_downloader.py*" -or
                $_.CommandLine -like "*telegram_bot.py*"
            )
        })
    }
    catch {
        return @()
    }
}

function Get-EffectiveTrackedPid {
    param(
        [int]$RootPid,
        [string]$Pattern
    )

    if (-not $RootPid) {
        return $null
    }

    $currentPid = $RootPid
    $allTracked = Get-TrackedPythonProcesses
    if (-not $allTracked -or $allTracked.Count -eq 0) {
        return $currentPid
    }

    while ($true) {
        $matchingChildren = @($allTracked | Where-Object {
            $_.ParentProcessId -eq $currentPid -and $_.CommandLine -like "*$Pattern*"
        })

        if ($matchingChildren.Count -ne 1) {
            return $currentPid
        }

        $currentPid = $matchingChildren[0].ProcessId
    }
}

function Ensure-HiddenAutostartScript {
    $pwshExe = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $pwshExe) {
        $pwshExe = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
    }
    if (-not $pwshExe) {
        $pwshExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    }

    $escapedPwsh = $pwshExe.Replace("""", """""")
    $escapedScript = $PSCommandPath.Replace("""", """""")
    $commandLine = """" + $escapedPwsh + """ -NoProfile -ExecutionPolicy Bypass -File """ + $escapedScript + """ ensure-running -r python"

    $vbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.Run "$commandLine", 0, False
"@

    Set-Content -Path $hiddenAutostartScript -Value $vbsContent -Encoding ASCII
    return $hiddenAutostartScript
}

function Get-AutostartTaskDefinitions {
    $wscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"
    $hiddenScriptPath = Ensure-HiddenAutostartScript
    $taskCommand = "`"$wscriptExe`" //B //NoLogo `"$hiddenScriptPath`""
    return @(
        @{
            Name = "ChronoLullaby-Autostart"
            Schedule = "ONLOGON"
            Modifier = $null
            Description = "ChronoLullaby 开机/登录自启"
            Command = $taskCommand
        },
        @{
            Name = "ChronoLullaby-KeepAlive"
            Schedule = "MINUTE"
            Modifier = 15
            Description = "ChronoLullaby 每 15 分钟保活检查"
            Command = $taskCommand
        }
    )
}

# 启动命令实现
function Invoke-StartCommand {
    Write-Host "=== ChronoLullaby 服务启动 ===" -ForegroundColor Green
    
    # 设置配置模式环境变量（命令行参数优先于配置文件）
    if ($Mode) {
        $env:CONFIG_MODE = $Mode
        Write-Host "配置模式: $Mode (命令行指定，覆盖配置文件)" -ForegroundColor Cyan
    }

    $normalizedRunMode = ""
    if ($RunMode) {
        $normalizedRunMode = $RunMode.ToLowerInvariant()
        if ($normalizedRunMode -notin @("auto", "python")) {
            Write-Host "错误: --run-mode 只支持 auto / python" -ForegroundColor Red
            return
        }
    }
    else {
        Write-Host "配置模式: 使用配置文件中的 mode 设置" -ForegroundColor Gray
    }

    # 检查是否已有实例在运行
    $processInfoPath = Join-Path $projectRoot "data/process_info.json"
    if (Test-Path $processInfoPath) {
        try {
            $existingInfo = Get-Content $processInfoPath | ConvertFrom-Json

            # 检查进程是否还在运行
            $launcherRunning = $null
            if ($existingInfo.launcher_pid) {
                $launcherRunning = Get-Process -Id $existingInfo.launcher_pid -ErrorAction SilentlyContinue
            }
            $downloaderRunning = Get-Process -Id $existingInfo.downloader_pid -ErrorAction SilentlyContinue
            $botRunning = Get-Process -Id $existingInfo.bot_pid -ErrorAction SilentlyContinue

            if ($launcherRunning -or $downloaderRunning -or $botRunning) {
                Write-Host "⚠️  检测到已有实例在运行：" -ForegroundColor Yellow
                if ($launcherRunning) { Write-Host "  Launcher 监护进程 (PID: $($existingInfo.launcher_pid))" -ForegroundColor Gray }
                if ($downloaderRunning) { Write-Host "  YouTube 下载器 (PID: $($existingInfo.downloader_pid))" -ForegroundColor Gray }
                if ($botRunning) { Write-Host "  Telegram 机器人 (PID: $($existingInfo.bot_pid))" -ForegroundColor Gray }
                Write-Host ""
                Write-Host "检测到已有实例，默认先停止旧实例再启动，避免重复进程冲突。" -ForegroundColor Yellow
                Write-Host "正在停止现有实例..." -ForegroundColor Cyan
                if ($launcherRunning) { Stop-Process -Id $existingInfo.launcher_pid -Force -ErrorAction SilentlyContinue }
                if ($downloaderRunning) { Stop-Process -Id $existingInfo.downloader_pid -Force -ErrorAction SilentlyContinue }
                if ($botRunning) { Stop-Process -Id $existingInfo.bot_pid -Force -ErrorAction SilentlyContinue }
                Start-Sleep 2
                Write-Host "现有实例已停止，即将重新启动..." -ForegroundColor Green
            }
            else {
                # 进程已不存在，删除过期的信息文件
                Remove-Item $processInfoPath -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            Write-Host "无法读取现有进程信息，继续启动..." -ForegroundColor Yellow
        }
    }

    if ($normalizedRunMode -eq "python") {
        Write-Host "已指定 --run-mode python，强制使用 Python 启动模式" -ForegroundColor Yellow
    }
    Push-Location src

    try {
        # 创建日志目录（使用绝对路径）
        $logDir = Join-Path $projectRoot "logs"
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }

        Write-Host "使用 Python 启动" -ForegroundColor Gray

        Write-Host "日志目录: $logDir" -ForegroundColor Gray
        Write-Host "日志文件由程序自动管理 (logs/downloader.log, logs/bot.log 等)" -ForegroundColor Gray

        if ($useVenv) {
            $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
            Write-Host "后台启动 Launcher 监护进程..." -ForegroundColor Cyan
            $launcherProcess = Start-Process -FilePath $pythonExe -ArgumentList "launcher.py" -WindowStyle Hidden -PassThru
        }
        else {
            Write-Host "后台启动 Launcher 监护进程..." -ForegroundColor Cyan
            $launcherProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "launcher.py" -WindowStyle Hidden -PassThru
        }

        # 创建进程信息文件（使用绝对路径）
        $processInfoPath = Join-Path $projectRoot "data/process_info.json"
        Start-Sleep -Seconds 3
        if (-not (Test-Path $processInfoPath)) {
            $processInfo = @{
                "launcher_pid" = $launcherProcess.Id
                "start_time"   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                "project_root" = $projectRoot
                "log_dir"      = $logDir
                "launch_mode"  = "python-launcher"
            }
            $processInfo | ConvertTo-Json | Out-File -FilePath $processInfoPath -Encoding UTF8
        }

        Write-Host ""
        Write-Host "=== 服务启动完成 ===" -ForegroundColor Green
        Write-Host "启动模式: python + launcher 监护" -ForegroundColor White
        Write-Host "Launcher PID: $($launcherProcess.Id)" -ForegroundColor White
        Write-Host "进程信息已保存到: $processInfoPath" -ForegroundColor White
        Write-Host ""
        Write-Host "使用 'ch status' 查看状态，'ch logs' 查看日志，'ch stop' 停止服务" -ForegroundColor Yellow

    }
    catch {
        Write-Host "启动过程中发生错误: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        if (-not $useExe) {
            Pop-Location
        }
    }
}

# 停止命令实现
function Invoke-StopCommand {
    param (
        [switch]$Silent = $false  # 静默模式，用于 restart 时不显示过多信息
    )
    
    if (-not $Silent) {
        Write-Host "=== ChronoLullaby 服务停止 ===" -ForegroundColor Green
    }

    $stoppedCount = 0
    $processInfoPath = Join-Path $projectRoot "data/process_info.json"

    # 查找所有相关进程
    if (-not $Silent) {
        Write-Host "🔍 查找所有相关进程..." -ForegroundColor Cyan
    }
    $allProcesses = Get-AllRelatedProcesses

    if ($allProcesses.Count -gt 0) {
        if (-not $Silent) {
            Write-Host "发现 $($allProcesses.Count) 个相关进程" -ForegroundColor Yellow
        }

        foreach ($process in $allProcesses) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                if (-not $Silent) {
                    Write-Host "✅ 已停止: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Green
                }
                $stoppedCount++
            }
            catch {
                if (-not $Silent) {
                    Write-Host "❌ 停止 $($process.ProcessName) (PID: $($process.Id)) 时出错: $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        }
    }
    else {
        if (-not $Silent) {
            Write-Host "ℹ️ 未找到相关进程" -ForegroundColor Gray
        }
    }

    # 检查进程信息文件
    if (Test-Path $processInfoPath) {
        try {
            $processInfo = Get-Content $processInfoPath | ConvertFrom-Json
            $snapshot = Get-ServiceProcessSnapshot

            if (-not $Silent) {
                Write-Host "从进程信息文件中读取 PID..." -ForegroundColor Cyan
            }

            $trackedTargets = @(
                @{ Name = "Launcher 监护进程"; RecordedPid = $processInfo.launcher_pid; EffectivePid = $snapshot.effective_launcher_pid },
                @{ Name = "YouTube 下载器"; RecordedPid = $processInfo.downloader_pid; EffectivePid = $snapshot.effective_downloader_pid },
                @{ Name = "Telegram 机器人"; RecordedPid = $processInfo.bot_pid; EffectivePid = $snapshot.effective_bot_pid }
            )
            $stoppedPids = New-Object System.Collections.Generic.HashSet[int]

            foreach ($target in $trackedTargets) {
                if (-not $target.RecordedPid) {
                    continue
                }

                $pidCandidates = @()
                if ($target.EffectivePid) {
                    $pidCandidates += [int]$target.EffectivePid
                }
                if ($target.RecordedPid) {
                    $pidCandidates += [int]$target.RecordedPid
                }

                foreach ($pid in ($pidCandidates | Select-Object -Unique)) {
                    if (-not $stoppedPids.Add($pid)) {
                        continue
                    }
                    try {
                        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                        if ($process) {
                            Stop-Process -Id $pid -Force
                            if (-not $Silent) {
                                if ($pid -eq $target.RecordedPid -or -not $target.EffectivePid) {
                                    Write-Host "$($target.Name) (PID: $pid) 已停止" -ForegroundColor Green
                                }
                                else {
                                    Write-Host "$($target.Name) 实际工作进程 (PID: $pid) 已停止" -ForegroundColor Green
                                }
                            }
                        }
                        elseif (-not $Silent) {
                            Write-Host "$($target.Name) 进程已不存在 (PID: $pid)" -ForegroundColor Yellow
                        }
                    }
                    catch {
                        if (-not $Silent) {
                            Write-Host "停止 $($target.Name) (PID: $pid) 时出错: $($_.Exception.Message)" -ForegroundColor Red
                        }
                    }
                }
            }

            if (-not $Silent -and $processInfo.launcher_pid -and $snapshot.effective_launcher_pid -and $snapshot.effective_launcher_pid -ne $processInfo.launcher_pid) {
                Write-Host "Launcher 记录PID: $($processInfo.launcher_pid) -> 实际工作PID: $($snapshot.effective_launcher_pid)" -ForegroundColor Gray
            }
            if (-not $Silent -and $processInfo.downloader_pid -and $snapshot.effective_downloader_pid -and $snapshot.effective_downloader_pid -ne $processInfo.downloader_pid) {
                Write-Host "下载器 记录PID: $($processInfo.downloader_pid) -> 实际工作PID: $($snapshot.effective_downloader_pid)" -ForegroundColor Gray
            }
            if (-not $Silent -and $processInfo.bot_pid -and $snapshot.effective_bot_pid -and $snapshot.effective_bot_pid -ne $processInfo.bot_pid) {
                Write-Host "Bot 记录PID: $($processInfo.bot_pid) -> 实际工作PID: $($snapshot.effective_bot_pid)" -ForegroundColor Gray
            }

            if ($processInfo.launcher_pid -and -not $snapshot.effective_launcher_pid) {
                try {
                    $launcherProcess = Get-Process -Id $processInfo.launcher_pid -ErrorAction SilentlyContinue
                    if ($launcherProcess) {
                        Stop-Process -Id $processInfo.launcher_pid -Force
                        if (-not $Silent) {
                            Write-Host "Launcher 监护进程 (PID: $($processInfo.launcher_pid)) 已停止" -ForegroundColor Green
                        }
                    }
                    elseif (-not $Silent) {
                        Write-Host "Launcher 监护进程已不存在" -ForegroundColor Yellow
                    }
                }
                catch {
                    if (-not $Silent) {
                        Write-Host "停止 Launcher 时出错: $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }

            # 停止下载器进程
            if ($processInfo.downloader_pid -and -not $snapshot.effective_downloader_pid) {
                try {
                    $process = Get-Process -Id $processInfo.downloader_pid -ErrorAction SilentlyContinue
                    if ($process) {
                        Stop-Process -Id $processInfo.downloader_pid -Force
                        if (-not $Silent) {
                            Write-Host "YouTube 下载器 (PID: $($processInfo.downloader_pid)) 已停止" -ForegroundColor Green
                        }
                    }
                    else {
                        if (-not $Silent) {
                            Write-Host "YouTube 下载器进程已不存在" -ForegroundColor Yellow
                        }
                    }
                }
                catch {
                    if (-not $Silent) {
                        Write-Host "停止 YouTube 下载器时出错: $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }

            # 停止机器人进程
            if ($processInfo.bot_pid -and -not $snapshot.effective_bot_pid) {
                try {
                    $process = Get-Process -Id $processInfo.bot_pid -ErrorAction SilentlyContinue
                    if ($process) {
                        Stop-Process -Id $processInfo.bot_pid -Force
                        if (-not $Silent) {
                            Write-Host "Telegram 机器人 (PID: $($processInfo.bot_pid)) 已停止" -ForegroundColor Green
                        }
                    }
                    else {
                        if (-not $Silent) {
                            Write-Host "Telegram 机器人进程已不存在" -ForegroundColor Yellow
                        }
                    }
                }
                catch {
                    if (-not $Silent) {
                        Write-Host "停止 Telegram 机器人时出错: $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }

            # 删除进程信息文件
            Remove-Item $processInfoPath -Force
            if (-not $Silent) {
                Write-Host "已清理进程信息文件" -ForegroundColor Green
            }

        }
        catch {
            if (-not $Silent) {
                Write-Host "读取进程信息文件时出错: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }

    # 注意：现在日志由程序自动管理，通常不需要手动清理
    # 如果确实需要清理，请使用 'ch-cleanup' 命令

    if (-not $Silent) {
        Write-Host "🎯 停止操作完成 - 共停止了 $stoppedCount 个进程" -ForegroundColor Green
        if ($stoppedCount -gt 0) {
            Write-Host "✅ 所有相关进程已停止" -ForegroundColor Green
        }
        else {
            Write-Host "⚠️ 未找到相关进程，可能需要使用 'ch cleanup' 强制清理" -ForegroundColor Yellow
        }
    }
    
    return $stoppedCount
}

# 重启命令实现
function Invoke-RestartCommand {
    Write-Host "=== ChronoLullaby 服务重启 ===" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "📍 第 1 步: 停止现有服务..." -ForegroundColor Cyan
    $stoppedCount = Invoke-StopCommand -Silent
    
    if ($stoppedCount -gt 0) {
        Write-Host "✅ 已停止 $stoppedCount 个进程" -ForegroundColor Green
    }
    else {
        Write-Host "ℹ️ 没有发现运行中的进程" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "⏳ 等待进程完全退出..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    Write-Host ""
    Write-Host "📍 第 2 步: 启动服务..." -ForegroundColor Cyan
    Invoke-StartCommand
    
    Write-Host ""
    Write-Host "=== 重启完成 ===" -ForegroundColor Green
    Write-Host "使用 'ch status' 检查服务状态" -ForegroundColor Yellow
}

function Invoke-EnsureRunningCommand {
    Write-Host "=== ChronoLullaby 保活检查 ===" -ForegroundColor Green

    if (Test-ServiceHealthy) {
        $snapshot = Get-ServiceProcessSnapshot
        Write-Host "服务已在运行，跳过启动" -ForegroundColor Green
        $downloaderPid = if ($snapshot.effective_downloader_pid) { $snapshot.effective_downloader_pid } else { $snapshot.info.downloader_pid }
        $botPid = if ($snapshot.effective_bot_pid) { $snapshot.effective_bot_pid } else { $snapshot.info.bot_pid }
        Write-Host "  下载器 PID: $downloaderPid" -ForegroundColor Gray
        Write-Host "  Bot PID: $botPid" -ForegroundColor Gray
        return
    }

    Write-Host "检测到服务未完全运行，开始拉起..." -ForegroundColor Yellow
    Invoke-StartCommand
}

function Invoke-InstallAutostartCommand {
    Write-Host "=== 安装开机自启与保活任务 ===" -ForegroundColor Green

    foreach ($task in Get-AutostartTaskDefinitions) {
        $args = @(
            "/Create",
            "/F",
            "/TN", $task.Name,
            "/SC", $task.Schedule,
            "/TR", $task.Command
        )

        if ($task.Modifier) {
            $args += @("/MO", "$($task.Modifier)")
        }

        & schtasks.exe @args | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ 安装计划任务失败: $($task.Name)" -ForegroundColor Red
            return
        }

        Write-Host "✅ 已安装: $($task.Name)" -ForegroundColor Green
        Write-Host "  说明: $($task.Description)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "计划任务已安装完成。" -ForegroundColor Green
    Write-Host "它们会调用: ch ensure-running -r python" -ForegroundColor Gray
}

function Invoke-UninstallAutostartCommand {
    Write-Host "=== 删除开机自启与保活任务 ===" -ForegroundColor Green

    foreach ($task in Get-AutostartTaskDefinitions) {
        & schtasks.exe /Delete /F /TN $task.Name | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 已删除: $($task.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "ℹ️ 未找到任务: $($task.Name)" -ForegroundColor Gray
        }
    }
}

function Invoke-AutostartStatusCommand {
    Write-Host "=== 计划任务状态 ===" -ForegroundColor Green

    foreach ($task in Get-AutostartTaskDefinitions) {
        $queryOutput = & schtasks.exe /Query /TN $task.Name /FO LIST /V 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $($task.Name)" -ForegroundColor Green
            $queryOutput | Select-String "状态:|Status:|上次运行时间:|Last Run Time:|下次运行时间:|Next Run Time:|任务计划:|Schedule:" | ForEach-Object {
                Write-Host "  $($_.ToString().Trim())" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "❌ $($task.Name) 未安装" -ForegroundColor Red
        }
        Write-Host ""
    }
}

function Invoke-YtDlpWatchCommand {
    $intervalMinutes = 15
    $once = $false
    $dryRun = $false

    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        switch ($Arguments[$i]) {
            "--interval" {
                if ($i + 1 -lt $Arguments.Count) {
                    $intervalMinutes = [int]$Arguments[$i + 1]
                    $i++
                }
            }
            "-interval" {
                if ($i + 1 -lt $Arguments.Count) {
                    $intervalMinutes = [int]$Arguments[$i + 1]
                    $i++
                }
            }
            "--once" { $once = $true }
            "--dry-run" { $dryRun = $true }
        }
    }

    if ($intervalMinutes -lt 1) {
        $intervalMinutes = 1
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "❌ ytdlp-watch 需要 uv 命令来执行升级" -ForegroundColor Red
        return
    }

    Write-Host "=== yt-dlp 自动监控与恢复 ===" -ForegroundColor Green
    Write-Host "检查间隔: $intervalMinutes 分钟" -ForegroundColor White
    Write-Host "模式: $(if ($Mode) { $Mode } else { '使用配置文件默认 mode' })" -ForegroundColor Gray
    if ($dryRun) {
        Write-Host "当前为 dry-run：只检测，不执行升级/重启" -ForegroundColor Yellow
    }
    Write-Host ""

    while ($true) {
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "[$now] 正在检查 yt-dlp 版本..." -ForegroundColor Cyan

        $info = Get-YtDlpVersionInfo
        if (-not $info.ok) {
            Write-Host "❌ 版本检查失败: $($info.error)" -ForegroundColor Red
        }
        else {
            Write-Host "  当前版本: $($info.installed)" -ForegroundColor White
            Write-Host "  最新版本: $($info.latest)" -ForegroundColor White

            if ($info.update_available) {
                Write-Host "✅ 检测到新版本，准备执行自动恢复流程" -ForegroundColor Green

                if ($dryRun) {
                    Write-Host "dry-run：跳过升级与重启" -ForegroundColor Yellow
                }
                else {
                    Write-Host "📦 执行项目环境升级: yt-dlp" -ForegroundColor Cyan
                    Invoke-ProjectYtDlpUpgrade
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "❌ yt-dlp 升级失败，本轮结束后继续监控" -ForegroundColor Red
                    }
                    else {
                        $verifyVersion = (Invoke-ProjectPython -Code "import yt_dlp; print(yt_dlp.version.__version__)") | Select-Object -Last 1
                        Write-Host "✅ 项目环境当前 yt-dlp 版本: $verifyVersion" -ForegroundColor Green

                        Write-Host "✅ yt-dlp 升级成功，开始重启服务..." -ForegroundColor Green
                        Invoke-RestartCommand
                        Write-Host "🎯 自动恢复完成，退出监控" -ForegroundColor Green
                        return
                    }
                }
            }
            else {
                Write-Host "ℹ️ 暂无新版本" -ForegroundColor Gray
            }
        }

        if ($once) {
            Write-Host "单次检查完成，退出" -ForegroundColor Gray
            return
        }

        Write-Host "下次检查将在 $intervalMinutes 分钟后进行..." -ForegroundColor Gray
        Write-Host ""
        Start-Sleep -Seconds ($intervalMinutes * 60)
    }
}

# 状态命令实现
function Invoke-StatusCommand {
    Write-Host "=== ChronoLullaby 状态检查 ===" -ForegroundColor Green
    Write-Host ""

    function Check-ProcessStatus {
        param (
            [int]$ProcessId,
            [string]$ProcessName
        )

        if ($ProcessId -le 0) {
            Write-Host "$ProcessName" -ForegroundColor Yellow
            Write-Host "  状态: PID 尚未写入或进程尚未拉起" -ForegroundColor Yellow
            return $false
        }

        try {
            $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
            if ($process) {
                $uptime = (Get-Date) - $process.StartTime
                Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Green
                Write-Host "  状态: 运行中" -ForegroundColor Green
                Write-Host "  运行时间: $($uptime.ToString('hh\:mm\:ss'))" -ForegroundColor White
                Write-Host "  CPU 使用: $($process.CPU.ToString('F2'))秒" -ForegroundColor White
                Write-Host "  内存使用: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                return $true
            }
            else {
                Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Red
                Write-Host "  状态: 未运行" -ForegroundColor Red
                return $false
            }
        }
        catch {
            Write-Host "$ProcessName (PID: $ProcessId)" -ForegroundColor Red
            Write-Host "  状态: 检查失败 - $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }

    $processInfoPath = Join-Path $projectRoot "data/process_info.json"

    # 检查进程信息文件
    if (Test-Path $processInfoPath) {
        try {
            $processInfo = Get-Content $processInfoPath | ConvertFrom-Json
            $snapshot = Get-ServiceProcessSnapshot

            Write-Host "从进程信息文件读取状态:" -ForegroundColor Cyan
            Write-Host "项目目录: $($processInfo.project_root)" -ForegroundColor Gray
            Write-Host "启动时间: $($processInfo.start_time)" -ForegroundColor White
            $launchMode = if ($processInfo.launch_mode) { $processInfo.launch_mode } else { "python" }
            $launchModeLabel = switch ($launchMode) {
                "python-launcher" { "python + launcher 监护" }
                default { "python (解释器)" }
            }
            Write-Host "启动模式: $launchModeLabel" -ForegroundColor White
            Write-Host "日志目录: $($processInfo.log_dir)" -ForegroundColor Gray
            Write-Host "使用 'ch logs' 查看日志" -ForegroundColor Gray
            Write-Host ""

            $launcherRunning = $false
            if ($processInfo.launcher_pid) {
                $launcherPidToCheck = if ($snapshot.effective_launcher_pid) { $snapshot.effective_launcher_pid } else { $processInfo.launcher_pid }
                $launcherRunning = Check-ProcessStatus -ProcessId $launcherPidToCheck -ProcessName "Launcher 监护进程"
                if ($launcherPidToCheck -ne $processInfo.launcher_pid) {
                    Write-Host "  记录PID: $($processInfo.launcher_pid) -> 实际工作PID: $launcherPidToCheck" -ForegroundColor Gray
                }
                Write-Host ""
            }
            $downloaderPidToCheck = if ($snapshot.effective_downloader_pid) { $snapshot.effective_downloader_pid } else { $processInfo.downloader_pid }
            $downloaderRunning = Check-ProcessStatus -ProcessId $downloaderPidToCheck -ProcessName "YouTube 下载器"
            if ($downloaderPidToCheck -and $downloaderPidToCheck -ne $processInfo.downloader_pid) {
                Write-Host "  记录PID: $($processInfo.downloader_pid) -> 实际工作PID: $downloaderPidToCheck" -ForegroundColor Gray
            }
            Write-Host ""
            $botPidToCheck = if ($snapshot.effective_bot_pid) { $snapshot.effective_bot_pid } else { $processInfo.bot_pid }
            $botRunning = Check-ProcessStatus -ProcessId $botPidToCheck -ProcessName "Telegram 机器人"
            if ($botPidToCheck -and $botPidToCheck -ne $processInfo.bot_pid) {
                Write-Host "  记录PID: $($processInfo.bot_pid) -> 实际工作PID: $botPidToCheck" -ForegroundColor Gray
            }
            Write-Host ""

            if ($launchMode -eq "python-launcher") {
                if ($launcherRunning -and $downloaderRunning -and $botRunning) {
                    Write-Host "✅ 所有服务运行正常" -ForegroundColor Green
                }
                elseif ($launcherRunning -or $downloaderRunning -or $botRunning) {
                    Write-Host "⚠️  部分服务运行异常" -ForegroundColor Yellow
                }
                else {
                    Write-Host "❌ 所有服务都未运行" -ForegroundColor Red
                }
            }
            elseif ($downloaderRunning -and $botRunning) {
                Write-Host "✅ 所有服务运行正常" -ForegroundColor Green
            }
            elseif ($downloaderRunning -or $botRunning) {
                Write-Host "⚠️  部分服务运行异常" -ForegroundColor Yellow
            }
            else {
                Write-Host "❌ 所有服务都未运行" -ForegroundColor Red
            }

        }
        catch {
            Write-Host "读取进程信息文件时出错: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "未找到进程信息文件，手动搜索相关进程..." -ForegroundColor Yellow
        Write-Host ""

        # 搜索相关的 uv、Python 和 exe 进程
        $allProcesses = @()
        $allProcesses += Get-Process -Name "uv*" -ErrorAction SilentlyContinue
        $allProcesses += Get-Process -Name "python*" -ErrorAction SilentlyContinue
        $allProcesses += Get-Process -Name "launcher" -ErrorAction SilentlyContinue
        $allProcesses += Get-Process -Name "yt_dlp_downloader" -ErrorAction SilentlyContinue
        $allProcesses += Get-Process -Name "telegram_bot" -ErrorAction SilentlyContinue
        $foundProcesses = $false

        foreach ($process in $allProcesses) {
            try {
                $processName = $process.ProcessName
                $commandLine = $process.CommandLine
                if ($processName -eq "launcher" -or $commandLine -like "*launcher.py*") {
                    Write-Host "找到 Launcher 监护进程:" -ForegroundColor Green
                    Write-Host "  进程名: $processName" -ForegroundColor White
                    Write-Host "  PID: $($process.Id)" -ForegroundColor White
                    Write-Host "  内存: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                    $foundProcesses = $true
                }
                elseif ($processName -eq "yt_dlp_downloader" -or $commandLine -like "*yt_dlp_downloader.py*") {
                    Write-Host "找到 YouTube 下载器进程:" -ForegroundColor Green
                    Write-Host "  进程名: $processName" -ForegroundColor White
                    Write-Host "  PID: $($process.Id)" -ForegroundColor White
                    Write-Host "  内存: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                    $foundProcesses = $true
                }
                elseif ($processName -eq "telegram_bot" -or $commandLine -like "*telegram_bot.py*") {
                    Write-Host "找到 Telegram 机器人进程:" -ForegroundColor Green
                    Write-Host "  进程名: $processName" -ForegroundColor White
                    Write-Host "  PID: $($process.Id)" -ForegroundColor White
                    Write-Host "  内存: $([math]::Round($process.WorkingSet64/1MB, 2))MB" -ForegroundColor White
                    $foundProcesses = $true
                }
            }
            catch {
                # 无法获取命令行信息，可能权限不足
            }
        }

        if (-not $foundProcesses) {
            Write-Host "未找到相关进程" -ForegroundColor Yellow
            Write-Host "提示: 如果进程正在运行，可能需要管理员权限来查看详细信息" -ForegroundColor Gray
        }
    }

    Write-Host ""
    Write-Host "状态检查完成" -ForegroundColor Green
}

# 日志命令实现
function Invoke-LogsCommand {
    # 默认参数
    $LogType = "all"
    $Lines = 50
    $Follow = $false
    $List = $false

    # 解析参数
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        switch ($Arguments[$i]) {
            "--lines" {
                if ($i + 1 -lt $Arguments.Count) {
                    $Lines = [int]$Arguments[$i + 1]
                    $i++
                }
            }
            "-lines" {
                if ($i + 1 -lt $Arguments.Count) {
                    $Lines = [int]$Arguments[$i + 1]
                    $i++
                }
            }
            "--follow" { $Follow = $true }
            "-f" { $Follow = $true }
            "--list" { $List = $true }
            "-l" { $List = $true }
            default {
                if ($Arguments[$i] -match "^\d+$") {
                    $Lines = [int]$Arguments[$i]
                }
                elseif ($Arguments[$i] -in @("all", "downloader", "bot", "error")) {
                    $LogType = $Arguments[$i]
                }
            }
        }
    }

    Write-Host "=== ChronoLullaby 日志查看器 ===" -ForegroundColor Green

    $logDir = Join-Path $projectRoot "logs"

    # 检查日志目录是否存在
    if (-not (Test-Path $logDir)) {
        Write-Host "❌ 日志目录不存在: $logDir" -ForegroundColor Red
        Write-Host "请先使用 'ch start' 启动程序" -ForegroundColor Yellow
        return
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
        return
    }

    # 获取最新的日志文件
    $logFiles = Get-LatestLogFiles

    # 根据类型显示日志
    switch ($LogType.ToLower()) {
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
            Write-Host "❌ 未知的日志类型: $LogType" -ForegroundColor Red
            Write-Host "可用类型: all, downloader, bot, error" -ForegroundColor Yellow
            return
        }
    }

    if (-not $Follow) {
        Write-Host "💡 使用参数:" -ForegroundColor Yellow
        Write-Host "  --lines <数字>           # 显示行数 (默认50)" -ForegroundColor Gray
        Write-Host "  --follow, -f             # 实时跟踪" -ForegroundColor Gray
        Write-Host "  --list, -l               # 列出所有日志文件" -ForegroundColor Gray
    }
}

# init-notion 命令实现
function Invoke-InitNotionCommand {
    Write-Host "=== ChronoLullaby Notion 初始化 ===" -ForegroundColor Green
    Write-Host ""
    
    # 进入源代码目录
    Push-Location src
    
    try {
        Write-Host "🚀 正在启动 Notion 初始化工具..." -ForegroundColor Cyan
        Write-Host ""
        
        if ($useVenv) {
            $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
            & $pythonExe "commands\init_notion.py"
        }
        else {
            uv run python "commands\init_notion.py"
        }
        
        $exitCode = $LASTEXITCODE
        
        Write-Host ""
        if ($exitCode -eq 0) {
            Write-Host "✅ Notion 初始化成功完成！" -ForegroundColor Green
        }
        else {
            Write-Host "❌ Notion 初始化失败，请检查错误信息" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 执行 Notion 初始化时发生错误: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Pop-Location
    }
}

function Invoke-UpgradeNotionSchemaCommand {
    Write-Host "=== ChronoLullaby Notion Schema 升级 ===" -ForegroundColor Green
    Write-Host ""

    Push-Location src
    try {
        if ($useVenv) {
            $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
            & $pythonExe "commands\update_notion_schema.py"
        }
        else {
            uv run python "commands\update_notion_schema.py"
        }

        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            Write-Host "✅ Schema 升级完成" -ForegroundColor Green
        }
        else {
            Write-Host "❌ Schema 升级失败，请检查输出" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 执行 Schema 升级时发生异常: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Pop-Location
    }
}


# sync-to-notion 命令实现
function Invoke-SyncToNotionCommand {
    Write-Host "=== ChronoLullaby 数据同步到 Notion ===" -ForegroundColor Green
    Write-Host ""
    
    # 进入源代码目录
    Push-Location src
    
    try {
        Write-Host "🚀 正在启动数据同步工具..." -ForegroundColor Cyan
        Write-Host ""
        
        # 构建参数
        $syncArgs = @("commands\sync_to_notion.py")
        $rawArgs = @()
        if ($Mode) {
            $rawArgs += $Mode
        }
        if ($Arguments.Count -gt 0) {
            $rawArgs += $Arguments
        }

        if ($rawArgs.Count -gt 0) {
            $validDataValues = @("all", "config", "archive", "logs")
            $index = 0
            while ($index -lt $rawArgs.Count) {
                $token = $rawArgs[$index]

                if ($token -match '^--data=(.+)$') {
                    $syncArgs += "--data"
                    $syncArgs += $Matches[1]
                    $index++
                    continue
                }

                if ($token -eq "--data" -or $token -eq "-data") {
                    $syncArgs += "--data"
                    if ($index + 1 -lt $rawArgs.Count) {
                        $syncArgs += $rawArgs[$index + 1]
                        $index += 2
                    }
                    else {
                        $index++
                    }
                    continue
                }

                if ($validDataValues -contains $token.ToLowerInvariant()) {
                    $syncArgs += "--data"
                    $syncArgs += $token
                    $index++
                    continue
                }

                $syncArgs += $token
                $index++
            }
        }
        
        if ($useVenv) {
            $pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
            & $pythonExe $syncArgs
        }
        else {
            uv run python $syncArgs
        }
        
        $exitCode = $LASTEXITCODE
        
        Write-Host ""
        if ($exitCode -eq 0) {
            Write-Host "✅ 数据同步成功完成！" -ForegroundColor Green
        }
        else {
            Write-Host "❌ 数据同步失败，请检查错误信息" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 执行数据同步时发生错误: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Pop-Location
    }
}

# migrate-multiselect 命令实现
function Invoke-MigrateMultiselectCommand {
    Write-Host "=== ChronoLullaby YouTube 频道字段迁移工具 ===" -ForegroundColor Green
    Write-Host ""
    
    # 进入源代码目录
    Push-Location src
    
    try {
        Write-Host "🚀 正在启动字段迁移工具..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "此工具将把 Notion Config Database 中的 youtube_channels 字段" -ForegroundColor Yellow
        Write-Host "从 rich_text 格式迁移到 multi_select 格式" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "迁移后的优势：" -ForegroundColor Cyan
        Write-Host "  ✓ 每个 YouTube 频道作为独立的选项" -ForegroundColor Green
        Write-Host "  ✓ 可以随时添加/删除频道选项" -ForegroundColor Green
        Write-Host "  ✓ 不需要删除频道，只需取消勾选即可" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  注意：此操作会修改 Notion 数据库结构，建议先备份" -ForegroundColor Red
        Write-Host ""
        
        # 执行迁移脚本
        & uv run python "commands/migrate_youtube_channels_to_multiselect.py"
        
        $exitCode = $LASTEXITCODE
        
        Write-Host ""
        if ($exitCode -eq 0) {
            Write-Host "✅ 字段迁移成功完成！" -ForegroundColor Green
            Write-Host ""
            Write-Host "现在你可以在 Notion 中使用 multi_select 格式管理 YouTube 频道了" -ForegroundColor Cyan
        }
        else {
            Write-Host "❌ 字段迁移失败，请检查错误信息" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 执行字段迁移时发生错误: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Pop-Location
    }
}

# Notion 日志清理命令实现
function Invoke-CleanNotionLogsCommand {
    Write-Host "=== ChronoLullaby - Notion 日志清理 ===" -ForegroundColor Green
    Write-Host ""
    
    $projectRoot = $PSScriptRoot | Split-Path -Parent
    
    try {
        Push-Location $projectRoot
        
        # 传递所有参数给 Python 脚本
        $pythonArgs = @()
        foreach ($arg in $Arguments) {
            $pythonArgs += $arg
        }
        
        Write-Host "执行命令: uv run python -m src.commands.clean_notion_logs $($pythonArgs -join ' ')" -ForegroundColor Gray
        Write-Host ""
        
        uv run python -m src.commands.clean_notion_logs @pythonArgs
        
        $exitCode = $LASTEXITCODE
        
        Write-Host ""
        if ($exitCode -eq 0) {
            Write-Host "✅ 日志清理操作完成" -ForegroundColor Green
        }
        else {
            Write-Host "❌ 日志清理失败，请检查错误信息" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 执行日志清理时发生错误: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Pop-Location
    }
}

# 清理命令实现
function Invoke-CleanupCommand {
    Write-Host "=== ChronoLullaby 超级强制清理 ===" -ForegroundColor Green
    Write-Host "🔥 超级模式：将强制终止所有相关进程" -ForegroundColor Red
    Write-Host "⚠️ 此命令会终止所有Python/uv进程，可能影响其他项目" -ForegroundColor Yellow
    Write-Host ""

    $confirmation = Read-Host "确认要执行超级清理吗？(yes/no)"
    if ($confirmation -ne "yes" -and $confirmation -ne "y") {
        Write-Host "操作已取消" -ForegroundColor Yellow
        return
    }

    $stopped = 0

    # 查找所有 uv 进程
    $uvProcesses = Get-Process -Name "uv*" -ErrorAction SilentlyContinue
    if ($uvProcesses) {
        foreach ($process in $uvProcesses) {
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
        $_.CommandLine -and ($_.CommandLine -like "*python*" -or $_.CommandLine -like "*uv*" -or $_.CommandLine -like "*chronolullaby*")
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
        $file = Join-Path $path "data/process_info.json"
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
    Start-Sleep -Seconds 3
    
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

    Write-Host ""
    Write-Host "🔥 超级清理完成！" -ForegroundColor Green
    Write-Host "💀 强制终止了 $stopped 个进程" -ForegroundColor Red
    Write-Host "⚠️ 所有Python/uv进程已被强制终止" -ForegroundColor Yellow
    Write-Host "💡 现在可以安全删除任何日志文件" -ForegroundColor Cyan
}

# 辅助函数
function Get-AllRelatedProcesses {
    param (
        [string[]]$Keywords = @("launcher.py", "yt_dlp_downloader.py", "telegram_bot.py", "chronolullaby")
    )

    $allProcesses = @()

    # 查找 uv 进程
    $uvProcesses = Get-Process -Name "uv*" -ErrorAction SilentlyContinue | Where-Object {
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
    $allProcesses += $uvProcesses

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

function Get-LatestLogFiles {
    # 查找最新的日志文件（由 logger.py 自动创建）
    $logDir = Join-Path $projectRoot "logs"
    
    # 优先查找固定名称的日志文件（logger.py 的默认输出）
    $downloaderLog = Join-Path $logDir "downloader.log"
    $botLog = Join-Path $logDir "bot.log"
    $downloaderErrorLog = Join-Path $logDir "downloader_error.log"
    $botErrorLog = Join-Path $logDir "bot_error.log"
    
    # 如果固定名称的日志不存在，查找带时间戳的日志（兼容旧版）
    if (-not (Test-Path $downloaderLog)) {
        $latestDownloader = Get-ChildItem -Path $logDir -Name "downloader_*.log" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*error*" } | Sort-Object -Descending | Select-Object -First 1
        $downloaderLog = if ($latestDownloader) { Join-Path $logDir $latestDownloader } else { $null }
    }
    
    if (-not (Test-Path $botLog)) {
        $latestBot = Get-ChildItem -Path $logDir -Name "bot_*.log" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*error*" } | Sort-Object -Descending | Select-Object -First 1
        $botLog = if ($latestBot) { Join-Path $logDir $latestBot } else { $null }
    }
    
    if (-not (Test-Path $downloaderErrorLog)) {
        $latestDownloaderError = Get-ChildItem -Path $logDir -Name "downloader_error_*.log" -ErrorAction SilentlyContinue | Sort-Object -Descending | Select-Object -First 1
        $downloaderErrorLog = if ($latestDownloaderError) { Join-Path $logDir $latestDownloaderError } else { $null }
    }
    
    if (-not (Test-Path $botErrorLog)) {
        $latestBotError = Get-ChildItem -Path $logDir -Name "bot_error_*.log" -ErrorAction SilentlyContinue | Sort-Object -Descending | Select-Object -First 1
        $botErrorLog = if ($latestBotError) { Join-Path $logDir $latestBotError } else { $null }
    }

    return @{
        "downloader_log"       = $downloaderLog
        "bot_log"              = $botLog
        "downloader_error_log" = $downloaderErrorLog
        "bot_error_log"        = $botErrorLog
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


# 解析命令和参数
switch ($Command.ToLower()) {
    "start" {
        Invoke-StartCommand
    }
    "stop" {
        Invoke-StopCommand
    }
    "restart" {
        Invoke-RestartCommand
    }
    "ensure-running" {
        Invoke-EnsureRunningCommand
    }
    "status" {
        Invoke-StatusCommand
    }
    "install-autostart" {
        Invoke-InstallAutostartCommand
    }
    "uninstall-autostart" {
        Invoke-UninstallAutostartCommand
    }
    "autostart-status" {
        Invoke-AutostartStatusCommand
    }
    "logs" {
        Invoke-LogsCommand
    }
    "cleanup" {
        Invoke-CleanupCommand
    }
    "init-notion" {
        Invoke-InitNotionCommand
    }
    "sync-to-notion" {
        Invoke-SyncToNotionCommand
    }
    "migrate-multiselect" {
        Invoke-MigrateMultiselectCommand
    }
    "ytdlp-watch" {
        Invoke-YtDlpWatchCommand
    }
    "upgrade-notion-schema" {
        Invoke-UpgradeNotionSchemaCommand
    }
    "clean-notion-logs" {
        Invoke-CleanNotionLogsCommand
    }
    "add-chtopath" {
        Add-ChToPath
    }
    "help" {
        Show-Help
    }
    "version" {
        Show-Version
    }
    "--help" {
        Show-Help
    }
    "-h" {
        Show-Help
    }
    "--version" {
        Show-Version
    }
    "-v" {
        Show-Version
    }
    default {
        Write-Host "未知命令: $Command" -ForegroundColor Red
        Write-Host "使用 'ch help' 查看可用命令" -ForegroundColor Yellow
        exit 1
    }
}

# 永久添加到 PATH 的辅助函数
function Add-ChToPath {
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.ScriptName
    }
    $scriptDir = Split-Path $scriptPath -Parent

    try {
        # 检查是否需要管理员权限
        $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
        $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

        if (-not $isAdmin) {
            Write-Host "⚠️  需要管理员权限来永久修改环境变量" -ForegroundColor Yellow
            Write-Host "请以管理员身份运行 PowerShell，或手动将以下路径添加到 PATH:" -ForegroundColor Yellow
            Write-Host "  $scriptDir" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "手动添加步骤:" -ForegroundColor White
            Write-Host "1. 右键点击 '此电脑' -> 属性" -ForegroundColor Gray
            Write-Host "2. 点击 '高级系统设置' -> '环境变量'" -ForegroundColor Gray
            Write-Host "3. 在 '用户变量' 或 '系统变量' 中找到 Path" -ForegroundColor Gray
            Write-Host "4. 点击 '编辑' -> '新建'" -ForegroundColor Gray
            Write-Host "5. 添加: $scriptDir" -ForegroundColor Gray
            Write-Host "6. 点击确定保存" -ForegroundColor Gray
            return
        }

        # 获取当前用户环境变量
        $userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
        $pathArray = $userPath -split ';' | Where-Object { $_ -and $_.Trim() }

        # 检查是否已经存在
        if ($pathArray -contains $scriptDir) {
            Write-Host "✅ 项目目录已在 PATH 中: $scriptDir" -ForegroundColor Green
            return
        }

        # 添加到 PATH
        $newPath = $userPath + ';' + $scriptDir
        [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)

        Write-Host "✅ 已永久添加到用户 PATH: $scriptDir" -ForegroundColor Green
        Write-Host "💡 请重启 PowerShell 或新开命令窗口以使更改生效" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "添加成功后就可以在任意目录使用以下命令:" -ForegroundColor Cyan
        Write-Host "  ch start    # 启动服务" -ForegroundColor White
        Write-Host "  ch status   # 查看状态" -ForegroundColor White
        Write-Host "  ch logs     # 查看日志" -ForegroundColor White
        Write-Host "  ch stop     # 停止服务" -ForegroundColor White

    }
    catch {
        Write-Host "❌ 添加到 PATH 时出错: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "请手动将以下路径添加到环境变量:" -ForegroundColor Yellow
        Write-Host "  $scriptDir" -ForegroundColor Cyan
    }
}
