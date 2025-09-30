# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
ChronoLullaby 启动器
同时启动 YouTube 下载器和 Telegram 机器人
"""

import os
import sys

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import os
import sys
import time
import signal
import subprocess
import multiprocessing
from pathlib import Path

class ProcessManager:
    def __init__(self):
        self.downloader_process = None
        self.bot_process = None
        self.running = False
    
    def start_downloader(self):
        """启动 YouTube 下载器"""
        try:
            print("🚀 启动 YouTube 下载器...")
            sys.stdout.flush()
            
            # 使用subprocess启动，确保使用poetry环境
            result = subprocess.run([
                "poetry", "run", "python", "yt_dlp_downloader.py"
            ], cwd=Path(__file__).parent)
            
        except Exception as e:
            print(f"❌ YouTube 下载器错误: {e}")
            sys.stdout.flush()
    
    def start_bot(self):
        """启动 Telegram 机器人"""
        try:
            print("🤖 启动 Telegram 机器人...")
            sys.stdout.flush()
            
            # 使用subprocess启动，确保使用poetry环境
            result = subprocess.run([
                "poetry", "run", "python", "telegram_bot.py"
            ], cwd=Path(__file__).parent)
            
        except Exception as e:
            print(f"❌ Telegram 机器人错误: {e}")
            sys.stdout.flush()
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n🛑 接收到停止信号，正在关闭所有进程...")
        self.stop_all()
        sys.exit(0)
    
    def stop_all(self):
        """停止所有进程"""
        self.running = False
        
        if self.downloader_process and self.downloader_process.is_alive():
            print("停止 YouTube 下载器...")
            self.downloader_process.terminate()
            self.downloader_process.join(timeout=5)
            if self.downloader_process.is_alive():
                self.downloader_process.kill()
        
        if self.bot_process and self.bot_process.is_alive():
            print("停止 Telegram 机器人...")
            self.bot_process.terminate()
            self.bot_process.join(timeout=5)
            if self.bot_process.is_alive():
                self.bot_process.kill()
        
        print("✅ 所有进程已停止")
    
    def start(self):
        """启动所有服务"""
        print("=== ChronoLullaby 启动器 ===")
        print("按 Ctrl+C 停止所有服务")
        print()
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # 启动下载器进程
            self.downloader_process = multiprocessing.Process(
                target=self.start_downloader,
                name="YouTubeDownloader"
            )
            self.downloader_process.start()
            print(f"✅ YouTube 下载器已启动 (PID: {self.downloader_process.pid})")
            
            # 等待2秒再启动机器人
            time.sleep(2)
            
            # 启动机器人进程
            self.bot_process = multiprocessing.Process(
                target=self.start_bot,
                name="TelegramBot"
            )
            self.bot_process.start()
            print(f"✅ Telegram 机器人已启动 (PID: {self.bot_process.pid})")
            
            self.running = True
            
            # 保存进程信息
            process_info = {
                'downloader_pid': self.downloader_process.pid,
                'bot_pid': self.bot_process.pid,
                'start_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            import json
            with open('../process_info.json', 'w', encoding='utf-8') as f:
                json.dump(process_info, f, indent=2, ensure_ascii=False)
            
            print("\n📊 进程信息已保存到 process_info.json")
            print("🔄 服务正在运行...")
            
            # 监控进程状态
            while self.running:
                time.sleep(10)  # 每10秒检查一次
                
                # 检查进程是否还在运行
                if not self.downloader_process.is_alive():
                    print("⚠️  YouTube 下载器进程意外退出")
                    break
                
                if not self.bot_process.is_alive():
                    print("⚠️  Telegram 机器人进程意外退出")
                    break
        
        except KeyboardInterrupt:
            print("\n🛑 接收到中断信号...")
        except Exception as e:
            print(f"❌ 启动过程中发生错误: {e}")
        finally:
            self.stop_all()

def main():
    # 确保在正确的目录中
    os.chdir(Path(__file__).parent)
    
    # 创建并启动进程管理器
    manager = ProcessManager()
    manager.start()

if __name__ == "__main__":
    main() 