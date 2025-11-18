# -*- coding: utf-8 -*-
"""
Notion API 适配器
提供与 Notion 数据库和页面交互的封装
"""

import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import time

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from notion_client import Client
    from notion_client.errors import APIResponseError
except ImportError:
    print("警告: notion-client 未安装，请运行: poetry install")
    Client = None
    APIResponseError = Exception

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


class NotionAdapter:
    """Notion API 适配器类"""
    
    def __init__(self, api_key: str, max_retries: int = 3):
        """
        初始化 Notion 适配器
        
        Args:
            api_key: Notion Integration Token
            max_retries: API 调用失败时的最大重试次数
        """
        if Client is None:
            raise ImportError("notion-client 未安装，请运行: poetry install")
        
        self.client = Client(auth=api_key)
        self.max_retries = max_retries
    
    def _retry_api_call(self, func, *args, **kwargs):
        """
        带重试机制的 API 调用
        
        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数
        
        Returns:
            API 调用结果
        """
        sys_logger = _get_sys_logger()
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except APIResponseError as e:
                last_error = e
                # 如果是限流错误，使用指数退避
                if e.code == 'rate_limited':
                    wait_time = (2 ** attempt) * 1
                    print(f"API 限流，等待 {wait_time} 秒后重试...")
                    if sys_logger:
                        from logger import log_with_context
                        import logging
                        log_with_context(
                            sys_logger, logging.WARNING,
                            "Notion API 限流，准备重试",
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            wait_time=wait_time,
                            func_name=func.__name__ if hasattr(func, '__name__') else str(func)
                        )
                    time.sleep(wait_time)
                else:
                    # 其他错误也进行重试
                    if attempt < self.max_retries - 1:
                        if sys_logger:
                            from logger import log_with_context
                            import logging
                            log_with_context(
                                sys_logger, logging.WARNING,
                                "Notion API 调用出错，准备重试",
                                attempt=attempt + 1,
                                max_retries=self.max_retries,
                                error=str(e),
                                error_code=e.code if hasattr(e, 'code') else 'unknown',
                                func_name=func.__name__ if hasattr(func, '__name__') else str(func)
                            )
                        time.sleep(1)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    if sys_logger:
                        from logger import log_with_context
                        import logging
                        log_with_context(
                            sys_logger, logging.WARNING,
                            "Notion API 调用异常，准备重试",
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            error=str(e),
                            error_type=type(e).__name__,
                            func_name=func.__name__ if hasattr(func, '__name__') else str(func)
                        )
                    time.sleep(1)
        
        # 所有重试都失败
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.ERROR,
                "Notion API 调用失败，已达最大重试次数",
                max_retries=self.max_retries,
                error=str(last_error),
                error_type=type(last_error).__name__,
                func_name=func.__name__ if hasattr(func, '__name__') else str(func)
            )
        raise last_error
    
    # ============================================================
    # 数据库操作
    # ============================================================
    
    def create_database(self, parent_page_id: str, title: str, properties: Dict[str, Any]) -> str:
        """
        创建数据库
        
        Args:
            parent_page_id: 父页面 ID
            title: 数据库标题
            properties: 数据库属性定义
        
        Returns:
            创建的数据库 ID
        """
        database = self._retry_api_call(
            self.client.databases.create,
            parent={
                "type": "page_id",
                "page_id": parent_page_id
            },
            title=[
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ],
            properties=properties
        )
        return database["id"]
    
    def query_database(self, database_id: str, filter_obj: Optional[Dict] = None,
                      sorts: Optional[List[Dict]] = None, page_size: int = 100) -> List[Dict]:
        """
        查询数据库
        
        Args:
            database_id: 数据库 ID
            filter_obj: 过滤条件
            sorts: 排序条件
            page_size: 每页数量
        
        Returns:
            查询结果列表
        """
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            query_params = {
                "database_id": database_id,
                "page_size": page_size
            }
            
            if filter_obj:
                query_params["filter"] = filter_obj
            if sorts:
                query_params["sorts"] = sorts
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = self._retry_api_call(
                self.client.databases.query,
                **query_params
            )
            
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return results
    
    def add_page_to_database(self, database_id: str, properties: Dict[str, Any]) -> str:
        """
        向数据库添加页面（记录）
        
        Args:
            database_id: 数据库 ID
            properties: 页面属性
        
        Returns:
            创建的页面 ID
        """
        sys_logger = _get_sys_logger()
        
        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.DEBUG,
                "Notion API: 准备添加页面到数据库",
                database_id=database_id[:8] + "...",
                properties_count=len(properties),
                property_names=list(properties.keys())
            )
        
        try:
            page = self._retry_api_call(
                self.client.pages.create,
                parent={"database_id": database_id},
                properties=properties
            )
            page_id = page["id"]
            
            if sys_logger:
                log_with_context(
                    sys_logger, logging.DEBUG,
                    "Notion API: 成功添加页面",
                    database_id=database_id[:8] + "...",
                    page_id=page_id[:8] + "..."
                )
            
            return page_id
        except Exception as e:
            if sys_logger:
                from logger import log_with_context
                import logging
                import traceback
                log_with_context(
                    sys_logger, logging.ERROR,
                    "Notion API: 添加页面失败",
                    database_id=database_id[:8] + "...",
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc()
                )
            raise
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict:
        """
        更新页面属性
        
        Args:
            page_id: 页面 ID
            properties: 要更新的属性
        
        Returns:
            更新后的页面对象
        """
        return self._retry_api_call(
            self.client.pages.update,
            page_id=page_id,
            properties=properties
        )
    
    def archive_page(self, page_id: str) -> Dict:
        """
        归档（删除）页面
        
        Args:
            page_id: 页面 ID
        
        Returns:
            归档后的页面对象
        """
        return self._retry_api_call(
            self.client.pages.update,
            page_id=page_id,
            archived=True
        )
    
    def batch_archive_pages(self, page_ids: List[str]) -> tuple:
        """
        批量归档页面
        
        Args:
            page_ids: 页面 ID 列表
        
        Returns:
            (成功数量, 失败数量)
        """
        success_count = 0
        failed_count = 0
        
        for page_id in page_ids:
            try:
                self.archive_page(page_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"归档页面失败 {page_id}: {e}")
        
        return success_count, failed_count
    
    # ============================================================
    # 页面操作
    # ============================================================
    
    def create_page(self, parent_page_id: str, title: str, content_blocks: Optional[List[Dict]] = None) -> str:
        """
        创建页面
        
        Args:
            parent_page_id: 父页面 ID
            title: 页面标题
            content_blocks: 页面内容块
        
        Returns:
            创建的页面 ID
        """
        page_data = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {"content": title}
                        }
                    ]
                }
            }
        }
        
        if content_blocks:
            page_data["children"] = content_blocks
        
        page = self._retry_api_call(
            self.client.pages.create,
            **page_data
        )
        return page["id"]
    
    def get_page(self, page_id: str) -> Dict:
        """
        获取页面信息
        
        Args:
            page_id: 页面 ID
        
        Returns:
            页面对象
        """
        return self._retry_api_call(
            self.client.pages.retrieve,
            page_id=page_id
        )
    
    def get_page_blocks(self, page_id: str) -> List[Dict]:
        """
        获取页面的所有块
        
        Args:
            page_id: 页面 ID
        
        Returns:
            块列表
        """
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            params = {"block_id": page_id}
            if start_cursor:
                params["start_cursor"] = start_cursor
            
            response = self._retry_api_call(
                self.client.blocks.children.list,
                **params
            )
            
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return results
    

    def ensure_database_property(self, database_id: str, property_name: str, property_schema: Dict[str, Any]) -> bool:
        """确保数据库存在指定属性（缺失时自动添加）"""
        database = self._retry_api_call(
            self.client.databases.retrieve,
            database_id=database_id
        )
        properties = database.get('properties', {})
        if property_name in properties:
            return False
        self._retry_api_call(
            self.client.databases.update,
            database_id=database_id,
            properties={
                property_name: property_schema
            }
        )
        return True

    def get_database_property_type(self, database_id: str, property_name: str) -> Optional[str]:
        database = self._retry_api_call(
            self.client.databases.retrieve,
            database_id=database_id
        )
        properties = database.get('properties', {})
        prop = properties.get(property_name)
        if not prop:
            return None
        return prop.get('type')

    def ensure_select_option(self, database_id: str, property_name: str, option: Dict[str, Any]) -> bool:
        """确保 select 属性包含指定选项（缺失时自动添加）"""
        database = self._retry_api_call(
            self.client.databases.retrieve,
            database_id=database_id
        )
        properties = database.get('properties', {})
        prop = properties.get(property_name)
        if not prop or prop.get('type') != 'select':
            return False
        existing = prop.get('select', {}).get('options', [])
        if any(opt.get('name') == option.get('name') for opt in existing):
            return False
        new_options = existing + [option]
        self._retry_api_call(
            self.client.databases.update,
            database_id=database_id,
            properties={
                property_name: {
                    'select': {
                        'options': new_options
                    }
                }
            }
        )
        return True
    def append_blocks(self, page_id: str, blocks: List[Dict]) -> List[Dict]:
        """
        向页面追加块
        
        Args:
            page_id: 页面 ID
            blocks: 要追加的块列表
        
        Returns:
            追加的块列表
        """
        response = self._retry_api_call(
            self.client.blocks.children.append,
            block_id=page_id,
            children=blocks
        )
        return response.get("results", [])
    
    def update_block(self, block_id: str, block_data: Dict) -> Dict:
        """
        更新块内容
        
        Args:
            block_id: 块 ID
            block_data: 新的块数据
        
        Returns:
            更新后的块对象
        """
        return self._retry_api_call(
            self.client.blocks.update,
            block_id=block_id,
            **block_data
        )
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    @staticmethod
    def build_rich_text(content: str) -> List[Dict]:
        """
        构建富文本对象
        
        Args:
            content: 文本内容
        
        Returns:
            富文本数组
        """
        return [
            {
                "type": "text",
                "text": {"content": content}
            }
        ]
    
    @staticmethod
    def build_title_property(content: str) -> Dict:
        """
        构建标题属性
        
        Args:
            content: 标题内容
        
        Returns:
            标题属性对象
        """
        return {
            "title": [
                {
                    "type": "text",
                    "text": {"content": content}
                }
            ]
        }
    
    @staticmethod
    def build_text_property(content: str) -> Dict:
        """
        构建文本属性
        
        Args:
            content: 文本内容
        
        Returns:
            文本属性对象
        """
        return {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content}
                }
            ]
        }
    
    @staticmethod
    def build_date_property(date_str: str) -> Dict:
        """
        构建日期属性
        
        Args:
            date_str: ISO 格式的日期字符串
        
        Returns:
            日期属性对象
        """
        return {
            "date": {
                "start": date_str
            }
        }
    
    @staticmethod
    def build_checkbox_property(checked: bool) -> Dict:
        """
        构建复选框属性
        
        Args:
            checked: 是否选中
        
        Returns:
            复选框属性对象
        """
        return {
            "checkbox": checked
        }
    
    @staticmethod
    def build_select_property(option: str) -> Dict:
        """
        构建选择属性
        
        Args:
            option: 选项名称
        
        Returns:
            选择属性对象
        """
        return {
            "select": {
                "name": option
            }
        }
    
    @staticmethod
    def build_multi_select_property(options: List[str]) -> Dict:
        """
        构建多选属性
        
        Args:
            options: 选项名称列表
        
        Returns:
            多选属性对象
        """
        return {
            "multi_select": [
                {"name": option} for option in options if option
            ]
        }
    
    @staticmethod
    def extract_plain_text(rich_text_array: List[Dict]) -> str:
        """
        从富文本数组提取纯文本
        
        Args:
            rich_text_array: 富文本数组
        
        Returns:
            纯文本字符串
        """
        if not rich_text_array:
            return ""
        return "".join([item.get("plain_text", "") for item in rich_text_array])
    
    @staticmethod
    def extract_code_block_text(block: Dict) -> str:
        """
        从代码块中提取文本内容
        
        Args:
            block: Notion 代码块对象
        
        Returns:
            代码块中的纯文本
        """
        if not block or block.get("type") != "code":
            return ""
        code = block.get("code", {})
        return NotionAdapter.extract_plain_text(code.get("rich_text", []))
    
    @staticmethod
    def extract_property_value(page: Dict, property_name: str) -> Any:
        """
        从页面对象提取属性值
        
        Args:
            page: 页面对象
            property_name: 属性名称
        
        Returns:
            属性值
        """
        properties = page.get("properties", {})
        prop = properties.get(property_name, {})
        prop_type = prop.get("type")
        
        if prop_type == "title":
            return NotionAdapter.extract_plain_text(prop.get("title", []))
        elif prop_type == "rich_text":
            return NotionAdapter.extract_plain_text(prop.get("rich_text", []))
        elif prop_type == "checkbox":
            return prop.get("checkbox", False)
        elif prop_type == "date":
            date_obj = prop.get("date")
            if date_obj:
                return date_obj.get("start")
            return None
        elif prop_type == "select":
            select_obj = prop.get("select")
            if select_obj:
                return select_obj.get("name")
            return None
        elif prop_type == "number":
            return prop.get("number")
        elif prop_type == "multi_select":
            multi_select_list = prop.get("multi_select", [])
            return [item.get("name") for item in multi_select_list if item.get("name")]
        else:
            return None


class NotionDatabaseSchemas:
    """Notion 数据库结构定义"""
    
    @staticmethod
    def config_database() -> Dict[str, Any]:
        """频道配置数据库结构"""
        return {
            "name": {
                "title": {}
            },
            "description": {
                "rich_text": {}
            },
            "enabled": {
                "checkbox": {}
            },
            "telegram_chat_id": {
                "rich_text": {}
            },
            "audio_folder": {
                "rich_text": {}
            },
            "youtube_channels": {
                "multi_select": {}
            },
            "channel_type": {
                "select": {
                    "options": [
                        {"name": "realtime", "color": "blue"},
                        {"name": "story", "color": "green"}
                    ]
                }
            },
            "story_last_video_id": {
                "rich_text": {}
            },
            "story_last_timestamp": {
                "number": {}
            },
            "story_interval_seconds": {
                "number": {}
            },
            "story_items_per_run": {
                "number": {}
            },
            "story_last_run_ts": {
                "number": {}
            }
        }
    
    @staticmethod
    def sent_archive_database() -> Dict[str, Any]:
        """已发送记录数据库结构"""
        return {
            "video_id": {
                "title": {}
            },
            "chat_id": {
                "rich_text": {}
            },
            "video_title": {
                "rich_text": {}
            },
            "sent_date": {
                "date": {}
            },
            "file_path": {
                "rich_text": {}
            }
        }
    
    @staticmethod
    def download_archive_database() -> Dict[str, Any]:
        """下载记录数据库结构"""
        return {
            "video_id": {
                "title": {}
            },
            "download_date": {
                "date": {}
            },
            "channel": {
                "rich_text": {}
            },
            "status": {
                "select": {
                    "options": [
                        {"name": "completed", "color": "green"},
                        {"name": "failed", "color": "red"}
                    ]
                }
            }
        }
    
    @staticmethod
    def logs_database() -> Dict[str, Any]:
        """日志数据库结构"""
        return {
            "message": {
                "title": {}
            },
            "timestamp": {
                "date": {}
            },
            "log_type": {
                "select": {
                    "options": [
                        {"name": "downloader", "color": "blue"},
                        {"name": "bot", "color": "green"},
                        {"name": "error", "color": "red"}
                    ]
                }
            },
            "level": {
                "select": {
                    "options": [
                        {"name": "INFO", "color": "gray"},
                        {"name": "WARNING", "color": "yellow"},
                        {"name": "ERROR", "color": "red"}
                    ]
                }
            },
            "machine_id": {
                "rich_text": {}
            }
        }
