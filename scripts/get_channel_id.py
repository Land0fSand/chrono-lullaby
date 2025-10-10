# -*- coding: utf-8 -*-
"""
Telegram 频道 ID 获取工具

使用方法：
1. 确保 bot 已被添加为频道管理员
2. 运行此脚本
3. 按照提示操作：
   - 方法1：在频道中发送任意消息（需要频道是公开讨论的）
   - 方法2：转发频道中的任意消息给bot（推荐）
4. 脚本会自动显示频道ID

注意：
- Bot 必须先被添加到频道并设为管理员
- 如果是私有频道，推荐使用转发消息的方法
"""

import sys
import os

# 添加父目录到路径，以便导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from src.config import get_telegram_token

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 获取 Bot Token
TOKEN = get_telegram_token()

if not TOKEN:
    print("❌ 错误：未找到 BOT_TOKEN！")
    print("请确保在 config/config.yaml 中配置了 bot_token")
    sys.exit(1)

print("=" * 60)
print("📋 Telegram 频道 ID 获取工具")
print("=" * 60)
print()
print("使用步骤：")
print("1. 确保你的 Bot 已被添加到目标频道")
print("2. 在频道设置中，将 Bot 设为管理员（至少给予 '发送消息' 权限）")
print("3. 选择以下任一方法：")
print()
print("   方法A（推荐）- 转发消息：")
print("   • 打开 Telegram，找到目标频道的任意消息")
print("   • 长按消息，选择 '转发'")
print("   • 将消息转发给你的 Bot")
print()
print("   方法B - 直接消息（需要频道支持评论）：")
print("   • 在频道中评论或发送消息（如果频道开启了讨论）")
print()
print("4. Bot 会自动显示频道信息")
print()
print("=" * 60)
print("⏳ 等待消息中...")
print("=" * 60)
print()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    await update.message.reply_text(
        "👋 你好！我是频道 ID 获取助手。\n\n"
        "要获取频道 ID，请按以下步骤操作：\n\n"
        "1️⃣ 将我添加到你的频道\n"
        "2️⃣ 设置我为管理员\n"
        "3️⃣ 转发频道中的任意消息给我\n\n"
        "我会立即告诉你频道的 ID！"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理接收到的消息"""
    
    # 获取聊天信息
    chat = update.effective_chat
    user = update.effective_user
    
    print()
    print("=" * 60)
    print("✅ 接收到消息！")
    print("=" * 60)
    
    # 显示聊天信息
    print(f"\n📍 聊天类型: {chat.type}")
    print(f"📍 聊天 ID: {chat.id}")
    
    if chat.title:
        print(f"📍 频道/群组名称: {chat.title}")
    
    if chat.username:
        print(f"📍 用户名: @{chat.username}")
    
    # 如果是转发的消息，显示原始来源
    if update.message and update.message.forward_from_chat:
        forward_chat = update.message.forward_from_chat
        print()
        print("-" * 60)
        print("📨 转发来源信息：")
        print("-" * 60)
        print(f"📍 原始频道类型: {forward_chat.type}")
        print(f"📍 原始频道 ID: {forward_chat.id}")
        
        if forward_chat.title:
            print(f"📍 原始频道名称: {forward_chat.title}")
        
        if forward_chat.username:
            print(f"📍 原始频道用户名: @{forward_chat.username}")
        
        print()
        print("=" * 60)
        print("💡 配置建议：")
        print("=" * 60)
        print(f"\n在 config/config.yaml 中使用以下配置：")
        print()
        print(f"channel_groups:")
        print(f"  - name: \"{forward_chat.title or '你的频道名称'}\"")
        print(f"    telegram_chat_id: \"{forward_chat.id}\"")
        print(f"    audio_folder: \"au\"")
        print()
    else:
        # 直接消息
        print()
        print("=" * 60)
        print("💡 配置建议：")
        print("=" * 60)
        
        if chat.type in ['channel', 'supergroup', 'group']:
            print(f"\n在 config/config.yaml 中使用以下配置：")
            print()
            print(f"channel_groups:")
            print(f"  - name: \"{chat.title or '你的频道名称'}\"")
            print(f"    telegram_chat_id: \"{chat.id}\"")
            print(f"    audio_folder: \"au\"")
            print()
        else:
            print("\n这是一个私聊消息。")
            print("要获取频道 ID，请转发频道中的消息给我。")
            print()
    
    print("=" * 60)
    print()
    print("提示：可以继续转发其他频道的消息，或按 Ctrl+C 退出")
    print()
    
    # 回复用户
    if update.message and update.message.forward_from_chat:
        try:
            await update.message.reply_text(
                f"✅ 已获取频道信息！\n\n"
                f"频道名称: {update.message.forward_from_chat.title}\n"
                f"频道 ID: `{update.message.forward_from_chat.id}`\n\n"
                f"请将此 ID 添加到 config.yaml 配置文件中。",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"提示：无法回复消息（可能 bot 没有发送权限）：{e}")
    elif update.message and chat.type in ['channel', 'supergroup', 'group']:
        try:
            await update.message.reply_text(
                f"✅ 频道 ID: `{chat.id}`",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"提示：无法回复消息（可能 bot 没有发送权限）：{e}")

def main():
    """主函数"""
    try:
        # 创建应用
        application = Application.builder().token(TOKEN).build()
        
        # 添加命令处理器
        application.add_handler(CommandHandler("start", start_command))
        
        # 添加消息处理器（接收所有消息）
        application.add_handler(MessageHandler(
            filters.ALL, 
            handle_message
        ))
        
        # 启动轮询
        print("🤖 Bot 已启动，等待接收消息...\n")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("\n\n")
        print("=" * 60)
        print("👋 已停止运行")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

