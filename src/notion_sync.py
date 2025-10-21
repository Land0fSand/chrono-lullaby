# -*- coding: utf-8 -*-
"""
Notion 后台同步服务
定期将日志和记录同步到 Notion
"""

import os
import sys
import time
import threading
from typing import List, Dict, Any
from queue import Queue, Empty
from datetime import datetime, timezone

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


class NotionSyncService:
    """Notion 后台同步服务"""
    
    def __init__(self, config_provider, sync_config: Dict[str, Any]):
        """
        初始化同步服务
        
        Args:
            config_provider: 配置提供者实例（应该是 NotionConfigProvider）
            sync_config: 同步配置
        """
        self.provider = config_provider
        self.sync_config = sync_config
        
        # 日志上传间隔
        self.log_upload_interval = sync_config.get('log_upload_interval', 300)
        # 记录同步间隔
        self.archive_sync_interval = sync_config.get('archive_sync_interval', 60)
        # 机器标识
        self.machine_id = sync_config.get('machine_id', 'unknown')
        
        # 日志队列（批量上传）
        self.log_queue = Queue()
        
        # 控制标志
        self.running = False
        self.threads = []
    
    def start(self):
        """启动同步服务"""
        if self.running:
            print("Notion 同步服务已在运行")
            return
        
        self.running = True
        
        # 启动日志上传线程
        log_thread = threading.Thread(
            target=self._log_upload_worker,
            name="NotionLogUploader",
            daemon=True
        )
        log_thread.start()
        self.threads.append(log_thread)
        
        print(f"✅ Notion 同步服务已启动")
        print(f"   日志上传间隔: {self.log_upload_interval}秒")
        if self.archive_sync_interval and self.archive_sync_interval > 0:
            print(f"   存档同步间隔: {self.archive_sync_interval}秒")
        else:
            print("   存档同步间隔: 已禁用")
        print(f"   机器标识: {self.machine_id}")
    
    def stop(self):
        """停止同步服务"""
        if not self.running:
            return
        
        self.running = False
        
        # 等待所有线程结束
        for thread in self.threads:
            thread.join(timeout=5)
        
        print("Notion 同步服务已停止")
    
    def queue_log(self, log_type: str, level: str, message: str):
        """
        将日志添加到上传队列
        
        Args:
            log_type: 日志类型（downloader/bot/error）
            level: 日志级别（INFO/WARNING/ERROR）
            message: 日志消息
        """
        self.log_queue.put({
            'log_type': log_type,
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'machine_id': self.machine_id
        })
    
    def _log_upload_worker(self):
        """日志上传工作线程"""
        print(f"日志上传线程已启动，间隔: {self.log_upload_interval}秒")
        
        logs_buffer = []
        last_upload_time = time.time()
        
        while self.running:
            try:
                # 收集日志（非阻塞）
                try:
                    log_entry = self.log_queue.get(timeout=1)
                    logs_buffer.append(log_entry)
                except Empty:
                    pass
                
                # 检查是否需要上传
                current_time = time.time()
                if (current_time - last_upload_time >= self.log_upload_interval and logs_buffer) or \
                   len(logs_buffer) >= 100:  # 缓冲区满了也上传
                    
                    self._upload_logs_batch(logs_buffer)
                    logs_buffer = []
                    last_upload_time = current_time
                
            except Exception as e:
                print(f"日志上传线程错误: {e}")
                time.sleep(5)
        
        # 退出前上传剩余日志
        if logs_buffer:
            self._upload_logs_batch(logs_buffer)
    
    def _upload_logs_batch(self, logs: List[Dict]):
        """
        批量上传日志到 Notion
        
        Args:
            logs: 日志列表
        """
        if not logs:
            return
        
        print(f"正在上传 {len(logs)} 条日志到 Notion...")
        
        # 获取 Notion 适配器和数据库 ID
        adapter = self.provider.adapter
        database_id = self.provider.config_data.get('database_ids', {}).get('logs')
        
        if not database_id:
            print("警告：Logs 数据库 ID 未配置，跳过上传")
            return
        
        # 批量添加日志
        success_count = 0
        failed_count = 0
        
        for log_entry in logs:
            try:
                properties = {
                    "message": adapter.build_title_property(
                        log_entry['message'][:2000]  # Notion 标题限制
                    ),
                    "timestamp": adapter.build_date_property(log_entry['timestamp']),
                    "log_type": adapter.build_select_property(log_entry['log_type']),
                    "level": adapter.build_select_property(log_entry['level']),
                    "machine_id": adapter.build_text_property(log_entry['machine_id'])
                }
                
                adapter.add_page_to_database(database_id, properties)
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                # 避免打印过多错误
                if failed_count <= 3:
                    print(f"上传日志失败: {e}")
        
        print(f"日志上传完成: ✅ {success_count} 条成功, ❌ {failed_count} 条失败")


# 全局同步服务实例
_sync_service: NotionSyncService = None


def get_sync_service() -> NotionSyncService:
    """获取全局同步服务实例"""
    return _sync_service


def init_sync_service(config_provider, sync_config: Dict[str, Any]):
    """
    初始化并启动同步服务
    
    Args:
        config_provider: 配置提供者实例
        sync_config: 同步配置
    """
    global _sync_service
    
    if _sync_service is not None:
        print("同步服务已初始化")
        return _sync_service
    
    _sync_service = NotionSyncService(config_provider, sync_config)
    _sync_service.start()
    
    return _sync_service


def stop_sync_service():
    """停止同步服务"""
    global _sync_service
    
    if _sync_service is not None:
        _sync_service.stop()
        _sync_service = None

