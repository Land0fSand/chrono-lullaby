# -*- coding: utf-8 -*-
"""
Notion 后台同步服务
定期将日志和记录同步到 Notion
"""

import os
import sys
import time
import threading
import json
from typing import List, Dict, Any, Optional
from queue import Queue, Empty
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 系统日志（延迟初始化）
_sys_logger = None

def _get_sys_logger():
    """延迟初始化系统日志"""
    global _sys_logger
    if _sys_logger is None:
        try:
            from logger import get_system_logger
            _sys_logger = get_system_logger()
        except Exception:
            pass
    return _sys_logger


class NotionSyncService:
    """Notion 后台同步服务"""
    
    # 清理时间记录文件路径
    CLEANUP_TIME_FILE = "data/last_log_cleanup.json"
    
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
        
        # 自动清理配置
        auto_cleanup_config = sync_config.get('auto_cleanup', {})
        self.cleanup_enabled = auto_cleanup_config.get('enabled', False)
        self.cleanup_check_interval_days = auto_cleanup_config.get('check_interval_days', 7)
        self.cleanup_keep_days = auto_cleanup_config.get('keep_days', 30)
        self.cleanup_error_keep_days = auto_cleanup_config.get('error_keep_days', 90)
        self.cleanup_min_keep_days = auto_cleanup_config.get('min_keep_days', 7)
        
        # 安全检查：确保保留天数不小于最小值
        if self.cleanup_keep_days < self.cleanup_min_keep_days:
            print(f"⚠️  警告：keep_days ({self.cleanup_keep_days}) 小于 min_keep_days ({self.cleanup_min_keep_days})，已调整为 {self.cleanup_min_keep_days}")
            self.cleanup_keep_days = self.cleanup_min_keep_days
        
        if self.cleanup_error_keep_days < self.cleanup_min_keep_days:
            print(f"⚠️  警告：error_keep_days ({self.cleanup_error_keep_days}) 小于 min_keep_days ({self.cleanup_min_keep_days})，已调整为 {self.cleanup_min_keep_days}")
            self.cleanup_error_keep_days = self.cleanup_min_keep_days
        
        # 日志队列（批量上传）
        self.log_queue = Queue()
        
        # 控制标志
        self.running = False
        self.threads = []
        
        # 上次清理时间（用于跟踪清理间隔）- 从文件加载
        self.last_cleanup_time = self._load_last_cleanup_time()
    
    def start(self):
        """启动同步服务"""
        sys_logger = _get_sys_logger()
        
        if self.running:
            print("Notion 同步服务已在运行")
            if sys_logger:
                sys_logger.warning("尝试启动已运行的 Notion 同步服务")
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
        
        # 启动自动清理线程（如果启用）
        if self.cleanup_enabled:
            cleanup_thread = threading.Thread(
                target=self._log_cleanup_worker,
                name="NotionLogCleaner",
                daemon=True
            )
            cleanup_thread.start()
            self.threads.append(cleanup_thread)
        
        print(f"✅ Notion 同步服务已启动")
        print(f"   日志上传间隔: {self.log_upload_interval}秒")
        if self.archive_sync_interval and self.archive_sync_interval > 0:
            print(f"   存档同步间隔: {self.archive_sync_interval}秒")
        else:
            print("   存档同步间隔: 已禁用")
        print(f"   机器标识: {self.machine_id}")
        
        if self.cleanup_enabled:
            print(f"   自动清理: 已启用")
            print(f"   清理策略: 每 {self.cleanup_check_interval_days} 天检查")
            print(f"   普通日志: 保留 {self.cleanup_keep_days} 天（INFO/WARNING/DEBUG）")
            print(f"   错误日志: 保留 {self.cleanup_error_keep_days} 天（ERROR）")
        else:
            print(f"   自动清理: 已禁用")
        
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "Notion 同步服务已启动",
                log_interval=self.log_upload_interval,
                archive_interval=self.archive_sync_interval,
                machine_id=self.machine_id,
                cleanup_enabled=self.cleanup_enabled,
                thread_id=log_thread.ident
            )
    
    def stop(self):
        """停止同步服务"""
        sys_logger = _get_sys_logger()
        
        if not self.running:
            return
        
        self.running = False
        
        if sys_logger:
            sys_logger.info("开始停止 Notion 同步服务")
        
        # 等待所有线程结束
        for thread in self.threads:
            thread.join(timeout=5)
        
        print("Notion 同步服务已停止")
        if sys_logger:
            sys_logger.info("Notion 同步服务已停止")
    
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
        
        sys_logger = _get_sys_logger()
        
        print(f"正在上传 {len(logs)} 条日志到 Notion...")
        
        # 获取 Notion 适配器和数据库 ID
        adapter = self.provider.adapter
        database_id = self.provider.config_data.get('database_ids', {}).get('logs')
        
        if not database_id:
            print("警告：Logs 数据库 ID 未配置，跳过上传")
            if sys_logger:
                sys_logger.warning("Logs 数据库 ID 未配置，无法上传日志到 Notion")
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
        
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "📤 Notion 日志批量上传完成",
                total=len(logs),
                success=success_count,
                failed=failed_count
            )
    
    def _log_cleanup_worker(self):
        """日志自动清理工作线程"""
        sys_logger = _get_sys_logger()
        
        print(f"日志自动清理线程已启动")
        print(f"  检查间隔: {self.cleanup_check_interval_days} 天")
        print(f"  普通日志保留: {self.cleanup_keep_days} 天")
        print(f"  错误日志保留: {self.cleanup_error_keep_days} 天")
        
        # 显示下次清理时间预估
        if self.last_cleanup_time:
            next_cleanup = self.last_cleanup_time + timedelta(days=self.cleanup_check_interval_days)
            time_until_next = next_cleanup - datetime.now(timezone.utc)
            days_until = max(0, time_until_next.days)
            print(f"⏰ 下次清理预计: {days_until} 天后")
        else:
            print(f"⏰ 首次启动，启动 60 秒后执行首次清理检查")
        
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "日志自动清理线程已启动",
                check_interval_days=self.cleanup_check_interval_days,
                keep_days=self.cleanup_keep_days,
                error_keep_days=self.cleanup_error_keep_days,
                last_cleanup_time=self.last_cleanup_time.isoformat() if self.last_cleanup_time else None
            )
        
        # 等待一段时间后再开始清理（避免启动时立即清理）
        initial_wait_seconds = 60  # 启动后等待 60 秒
        time.sleep(initial_wait_seconds)
        
        while self.running:
            try:
                # 检查是否需要清理
                should_cleanup = False
                
                if self.last_cleanup_time is None:
                    # 首次运行，执行清理
                    should_cleanup = True
                else:
                    # 检查距离上次清理是否已经超过间隔天数
                    time_since_last = datetime.now(timezone.utc) - self.last_cleanup_time
                    if time_since_last >= timedelta(days=self.cleanup_check_interval_days):
                        should_cleanup = True
                
                if should_cleanup:
                    print(f"\n🧹 开始自动清理 Notion 日志...")
                    
                    if sys_logger:
                        log_with_context(
                            sys_logger, logging.INFO,
                            "开始自动清理 Notion 日志",
                            keep_days=self.cleanup_keep_days,
                            error_keep_days=self.cleanup_error_keep_days
                        )
                    
                    # 执行清理
                    success = self._perform_cleanup()
                    
                    # 更新上次清理时间并保存到文件
                    self.last_cleanup_time = datetime.now(timezone.utc)
                    self._save_last_cleanup_time(self.last_cleanup_time)
                    
                    if success:
                        print(f"✅ 自动清理完成，下次清理时间: {self.cleanup_check_interval_days}天后")
                    else:
                        print(f"⚠️  自动清理遇到错误，将在下次间隔时重试")
                
                # 每小时检查一次是否需要清理
                check_interval_seconds = 3600  # 1小时
                
                # 分多次短暂睡眠，以便快速响应停止信号
                for _ in range(int(check_interval_seconds)):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                print(f"日志清理线程错误: {e}")
                if sys_logger:
                    log_with_context(
                        sys_logger, logging.ERROR,
                        "日志清理线程错误",
                        error=str(e)
                    )
                # 出错后等待较长时间再重试
                time.sleep(3600)  # 1小时
        
        print("日志清理线程已退出")
    
    def _perform_cleanup(self) -> bool:
        """
        执行实际的清理操作
        分两步清理：
        1. 清理普通日志（INFO/WARNING/DEBUG）- keep_days 天前的
        2. 清理错误日志（ERROR）- error_keep_days 天前的
        
        Returns:
            是否成功
        """
        sys_logger = _get_sys_logger()
        adapter = self.provider.adapter
        database_id = self.provider.config_data.get('database_ids', {}).get('logs')
        
        if not database_id:
            print("⚠️  警告：Logs 数据库 ID 未配置，跳过清理")
            return False
        
        all_success = True
        total_cleaned = 0
        
        # 第 1 步：清理普通日志（非 ERROR 的日志）
        print(f"   [1/2] 清理普通日志（INFO/WARNING/DEBUG）- {self.cleanup_keep_days} 天前...")
        success, count = self._cleanup_logs_by_level(
            adapter, 
            database_id, 
            self.cleanup_keep_days,
            exclude_error=True
        )
        all_success = all_success and success
        total_cleaned += count
        
        # 第 2 步：清理错误日志（ERROR）
        print(f"   [2/2] 清理错误日志（ERROR）- {self.cleanup_error_keep_days} 天前...")
        success, count = self._cleanup_logs_by_level(
            adapter,
            database_id,
            self.cleanup_error_keep_days,
            only_error=True
        )
        all_success = all_success and success
        total_cleaned += count
        
        # 总结
        if total_cleaned > 0:
            print(f"   ✅ 总计清理: {total_cleaned} 条日志")
        else:
            print(f"   ✅ 没有需要清理的日志")
        
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "自动清理日志完成",
                total_cleaned=total_cleaned,
                keep_days=self.cleanup_keep_days,
                error_keep_days=self.cleanup_error_keep_days
            )
        
        return all_success
    
    def _cleanup_logs_by_level(
        self, 
        adapter, 
        database_id: str, 
        days: int,
        exclude_error: bool = False,
        only_error: bool = False
    ) -> tuple:
        """
        按级别清理日志
        
        Args:
            adapter: NotionAdapter 实例
            database_id: 数据库 ID
            days: 保留天数
            exclude_error: 是否排除 ERROR 级别
            only_error: 是否只清理 ERROR 级别
        
        Returns:
            (是否成功, 清理数量)
        """
        try:
            # 计算截止日期
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # 构建过滤条件
            filters = [{
                "property": "timestamp",
                "date": {
                    "before": cutoff_date.isoformat()
                }
            }]
            
            # 添加级别过滤
            if exclude_error:
                # 排除 ERROR：只清理 INFO、WARNING、DEBUG
                filters.append({
                    "property": "level",
                    "select": {
                        "does_not_equal": "ERROR"
                    }
                })
            elif only_error:
                # 只清理 ERROR
                filters.append({
                    "property": "level",
                    "select": {
                        "equals": "ERROR"
                    }
                })
            
            # 组合过滤条件
            filter_obj = {"and": filters} if len(filters) > 1 else filters[0]
            
            # 查询需要清理的日志
            pages = adapter.query_database(
                database_id,
                filter_obj=filter_obj,
                page_size=100
            )
            
            if not pages:
                print(f"      → 无需清理")
                return True, 0
            
            # 批量删除
            total = len(pages)
            page_ids = [page['id'] for page in pages]
            success_count, failed_count = adapter.batch_archive_pages(page_ids)
            
            print(f"      → 清理 {total} 条: ✅ {success_count} 成功, ❌ {failed_count} 失败")
            
            return failed_count == 0, success_count
            
        except Exception as e:
            print(f"      → ❌ 清理失败: {e}")
            return False, 0
    
    def _load_last_cleanup_time(self) -> Optional[datetime]:
        """
        从文件加载上次清理时间
        
        Returns:
            上次清理时间，如果文件不存在或解析失败则返回 None
        """
        try:
            cleanup_file = Path(self.CLEANUP_TIME_FILE)
            if not cleanup_file.exists():
                return None
            
            with open(cleanup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            timestamp_str = data.get('last_cleanup_time')
            if timestamp_str:
                # 解析 ISO 格式时间
                last_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # 显示加载的信息
                time_diff = datetime.now(timezone.utc) - last_time
                days_ago = time_diff.days
                print(f"📅 上次清理: {days_ago} 天前 ({last_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                return last_time
        except Exception as e:
            print(f"警告：加载上次清理时间失败: {e}")
        
        return None
    
    def _save_last_cleanup_time(self, cleanup_time: datetime):
        """
        保存清理时间到文件
        
        Args:
            cleanup_time: 清理时间
        """
        try:
            cleanup_file = Path(self.CLEANUP_TIME_FILE)
            
            # 确保目录存在
            cleanup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为 ISO 格式
            data = {
                'last_cleanup_time': cleanup_time.isoformat(),
                'machine_id': self.machine_id,
                'keep_days': self.cleanup_keep_days,
                'error_keep_days': self.cleanup_error_keep_days
            }
            
            with open(cleanup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"警告：保存清理时间失败: {e}")


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
    sys_logger = _get_sys_logger()
    
    if _sync_service is not None:
        print("同步服务已初始化")
        if sys_logger:
            sys_logger.warning("尝试重复初始化 Notion 同步服务")
        return _sync_service
    
    if sys_logger:
        from logger import log_with_context
        import logging
        log_with_context(
            sys_logger, logging.DEBUG,
            "初始化 Notion 同步服务",
            sync_config=sync_config
        )
    
    _sync_service = NotionSyncService(config_provider, sync_config)
    _sync_service.start()
    
    return _sync_service


def stop_sync_service():
    """停止同步服务"""
    global _sync_service
    sys_logger = _get_sys_logger()
    
    if _sync_service is not None:
        if sys_logger:
            sys_logger.info("请求停止 Notion 同步服务")
        _sync_service.stop()
        _sync_service = None

