# -*- mode: python ; coding: utf-8 -*-
"""
ChronoLullaby PyInstaller spec 文件
编译两个核心服务为独立可执行文件：
  - yt_dlp_downloader (.exe)
  - telegram_bot (.exe)

使用方式：
  pyinstaller build/chronolullaby.spec
"""

import sys
import os

# 项目根目录（spec 文件在 build/ 下，上一级即项目根）
project_root = os.path.abspath(os.path.join(SPECPATH, '..'))
src_dir = os.path.join(project_root, 'src')

# ── 公共配置 ─────────────────────────────────────────────
common_hiddenimports = [
    # yt-dlp 及其插件
    'yt_dlp',
    'yt_dlp.extractor',
    'yt_dlp.downloader',
    'yt_dlp.postprocessor',
    'yt_dlp_ejs',
    # Telegram Bot
    'telegram',
    'telegram.ext',
    'telegram.request',
    'telegram.error',
    'httpx',
    'httpcore',
    'apscheduler',
    'apscheduler.schedulers',
    'apscheduler.schedulers.asyncio',
    'apscheduler.triggers',
    'apscheduler.triggers.interval',
    # Notion
    'notion_client',
    'notion_client.errors',
    # 数据处理
    'yaml',
    'dotenv',
    'ffmpeg',
    # 本地模块
    'config',
    'config_provider',
    'logger',
    'runtime_guard',
    'runtime_state',
    'util',
    'notion_adapter',
    'notion_sync',
    'task',
    'task.dl_audio',
    'task.send_file',
    'commands',
    'commands.add_channel',
    'commands.init_notion',
    'commands.sync_to_notion',
    'commands.clean_notion_logs',
    'commands.migrate_youtube_channels_to_multiselect',
    'commands.update_notion_schema',
]

common_excludes = [
    'tkinter',
    'unittest',
    'test',
    'tests',
    'PIL',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
]

# ── yt_dlp_downloader ───────────────────────────────────
downloader_a = Analysis(
    [os.path.join(src_dir, 'yt_dlp_downloader.py')],
    pathex=[src_dir],
    binaries=[],
    datas=[],
    hiddenimports=common_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=common_excludes,
    noarchive=False,
    collect_submodules=['yt_dlp', 'yt_dlp_ejs'],
    collect_data=['yt_dlp'],
)

downloader_pyz = PYZ(downloader_a.pure)

downloader_exe = EXE(
    downloader_pyz,
    downloader_a.scripts,
    downloader_a.binaries,
    downloader_a.datas,
    [],
    name='yt_dlp_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ── telegram_bot ─────────────────────────────────────────
bot_a = Analysis(
    [os.path.join(src_dir, 'telegram_bot.py')],
    pathex=[src_dir],
    binaries=[],
    datas=[],
    hiddenimports=common_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=common_excludes,
    noarchive=False,
    collect_submodules=['yt_dlp', 'yt_dlp_ejs'],
    collect_data=['yt_dlp'],
)

bot_pyz = PYZ(bot_a.pure)

bot_exe = EXE(
    bot_pyz,
    bot_a.scripts,
    bot_a.binaries,
    bot_a.datas,
    [],
    name='telegram_bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
