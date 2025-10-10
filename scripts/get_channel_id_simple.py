# -*- coding: utf-8 -*-
"""
Telegram 频道 ID 简单获取工具

此脚本通过发送测试消息到频道来获取频道ID，不需要轮询监听，
因此不会与正在运行的主bot冲突。

使用方法：
1. 确保 bot 已被添加为频道管理员（至少具有"发送消息"权限）
2. 在频道中 @你的bot用户名（或者直接写频道的公开链接/用户名）
3. 运行此脚本，输入频道的用户名（如 @mychannel）或频道ID
4. 脚本会尝试向频道发送测试消息并显示频道ID
"""

import sys
import os
import asyncio

# 添加父目录到路径，以便导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from telegram import Bot
from telegram.error import TelegramError
from src.config import get_telegram_token

# 获取 Bot Token
TOKEN = get_telegram_token()

if not TOKEN:
    print("❌ 错误：未找到 BOT_TOKEN！")
    print("请确保在 config/config.yaml 中配置了 bot_token")
    sys.exit(1)

print("=" * 60)
print("📋 Telegram 频道 ID 简单获取工具")
print("=" * 60)
print()
print("💡 使用说明：")
print()
print("1. 确保你的 Bot 已被添加到目标频道")
print("2. 在频道设置中，将 Bot 设为管理员")
print("   （至少给予 '发送消息' 权限）")
print()
print("3. 准备频道信息：")
print("   • 如果频道有公开用户名：@你的频道用户名")
print("   • 如果是私有频道：需要先通过方案1获取ID")
print()
print("=" * 60)
print()

async def test_channel_access(bot, channel_identifier):
    """测试频道访问权限并获取频道ID"""
    try:
        print(f"🔍 正在测试频道：{channel_identifier}")
        print()
        
        # 尝试向频道发送一条消息
        message = await bot.send_message(
            chat_id=channel_identifier,
            text="🤖 这是一条测试消息，用于获取频道ID。\n\n✅ Bot 访问正常！"
        )
        
        chat = message.chat
        
        print("=" * 60)
        print("✅ 成功！频道信息如下：")
        print("=" * 60)
        print()
        print(f"📍 频道类型: {chat.type}")
        print(f"📍 频道 ID: {chat.id}")
        
        if chat.title:
            print(f"📍 频道名称: {chat.title}")
        
        if chat.username:
            print(f"📍 频道用户名: @{chat.username}")
        
        print()
        print("=" * 60)
        print("💡 配置建议：")
        print("=" * 60)
        print()
        print(f"在 config/config.yaml 中使用以下配置：")
        print()
        print(f"channel_groups:")
        print(f"  - name: \"{chat.title or '你的频道名称'}\"")
        print(f"    telegram_chat_id: \"{chat.id}\"")
        print(f"    audio_folder: \"au\"")
        print()
        print("=" * 60)
        print()
        
        # 删除测试消息
        try:
            await message.delete()
            print("🧹 已删除测试消息")
        except:
            print("💡 提示：如需删除测试消息，请给予 Bot '删除消息' 权限")
        
        return chat.id
        
    except TelegramError as e:
        print("=" * 60)
        print("❌ 错误：无法访问频道")
        print("=" * 60)
        print()
        print(f"错误详情：{e}")
        print()
        print("📋 可能的原因：")
        print("  1. Bot 还未被添加到频道")
        print("  2. Bot 没有管理员权限")
        print("  3. Bot 没有 '发送消息' 权限")
        print("  4. 频道标识符不正确")
        print()
        print("💡 解决方法：")
        print("  • 确认 Bot 已添加为频道管理员")
        print("  • 公开频道使用：@频道用户名")
        print("  • 私有频道需要先通过方案1获取ID")
        print()
        return None

async def get_bot_info(bot):
    """获取Bot信息"""
    try:
        me = await bot.get_me()
        return me
    except TelegramError as e:
        print(f"❌ 无法获取Bot信息：{e}")
        return None

async def main():
    """主函数"""
    bot = Bot(token=TOKEN)
    
    # 获取并显示Bot信息
    print("🤖 正在连接到 Telegram...")
    me = await get_bot_info(bot)
    
    if not me:
        print("❌ 无法连接到 Telegram，请检查 Bot Token 是否正确")
        return
    
    print(f"✅ Bot 连接成功：@{me.username}")
    print()
    print("=" * 60)
    print()
    
    # 交互式输入频道标识符
    while True:
        print("请输入频道信息（输入 'q' 退出）：")
        print()
        print("  格式示例：")
        print("    • 公开频道：@mychannel")
        print("    • 使用用户名：mychannel （自动添加@）")
        print("    • 已知ID：-1001234567890")
        print()
        
        channel_input = input("👉 频道标识: ").strip()
        
        if channel_input.lower() == 'q':
            print()
            print("👋 退出程序")
            break
        
        if not channel_input:
            print("❌ 请输入有效的频道标识符")
            print()
            continue
        
        # 处理输入
        if not channel_input.startswith('@') and not channel_input.startswith('-') and not channel_input.isdigit():
            channel_input = '@' + channel_input
        
        print()
        
        # 测试频道访问
        channel_id = await test_channel_access(bot, channel_input)
        
        if channel_id:
            print()
            choice = input("是否继续测试其他频道？(y/n): ").strip().lower()
            if choice != 'y':
                break
        
        print()
        print("=" * 60)
        print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n")
        print("=" * 60)
        print("👋 已停止运行")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 程序错误：{e}")
        import traceback
        traceback.print_exc()

