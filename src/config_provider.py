# -*- coding: utf-8 -*-

"""

配置提供者抽象层

支持本地文件和 Notion 两种配置源

"""



import os

import sys

import yaml

import json

from abc import ABC, abstractmethod

from typing import Optional, Dict, Any, List

from datetime import datetime, timezone

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





class BaseConfigProvider(ABC):

    """配置提供者基类"""

    

    @abstractmethod

    def get_channel_groups(self, use_cache: bool = True) -> List[Dict[str, Any]]:

        """获取所有频道组配置"""

        pass

    

    @abstractmethod

    def get_telegram_token(self, group_index: int = 0) -> Optional[str]:

        """获取 Telegram Bot Token"""

        pass

    

    @abstractmethod

    def get_send_interval(self) -> int:

        """获取发送间隔（秒）"""

        pass

    

    @abstractmethod

    def get_download_interval(self) -> int:

        """获取下载间隔（秒）"""

        pass

    

    @abstractmethod

    def get_filter_days(self) -> int:

        """获取视频过滤天数"""

        pass

    

    @abstractmethod

    def get_max_videos_per_channel(self) -> int:

        """获取每个频道检查的最大视频数"""

        pass

    

    @abstractmethod

    def get_video_delay_min(self) -> int:

        """获取视频间最小延迟（秒）"""

        pass

    

    @abstractmethod

    def get_video_delay_max(self) -> int:

        """获取视频间最大延迟（秒）"""

        pass

    

    @abstractmethod

    def get_channel_delay_min(self) -> int:

        """获取频道间最小延迟（秒）"""

        pass

    

    @abstractmethod

    def get_channel_delay_max(self) -> int:

        """获取频道间最大延迟（秒）"""

        pass

    

    @abstractmethod

    def get_cookies_content(self) -> Optional[str]:

        """获取 Cookies 文件内容"""

        pass

    

    @abstractmethod

    def add_download_record(self, video_id: str, channel: str, status: str = "completed", machine_id: Optional[str] = None) -> bool:

        """添加下载记录"""

        pass

    

    @abstractmethod

    def has_download_record(self, video_id: str) -> bool:

        """检查是否已下载"""

        pass

    

    @abstractmethod

    def add_sent_record(self, video_id: str, chat_id: str, title: str, file_path: str, machine_id: Optional[str] = None) -> bool:
        """添加已发送记录到 Notion"""
        sys_logger = _get_sys_logger()

        database_id = self.config_data.get('database_ids', {}).get('sent_archive')
        if not database_id:
            if sys_logger:
                sys_logger.error("Notion 已发送记录数据库 ID 未配置")
            return False

        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "准备写入 Notion 发送记录",
                video_id=video_id,
                chat_id=chat_id,
                title=title[:50] + "..." if len(title) > 50 else title,
                database_id=database_id[:8] + "..."
            )

        properties = {
            "video_id": self.adapter.build_title_property(video_id),
            "chat_id": self.adapter.build_text_property(str(chat_id)),
            "sent_date": self.adapter.build_date_property(
                datetime.now(timezone.utc).isoformat()
            ),
            "file_path": self.adapter.build_text_property(file_path)
        }

        title_property_name = "video_title"
        title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)

        if title_prop_type is None:
            try:
                self.adapter.ensure_database_property(
                    database_id,
                    title_property_name,
                    {"type": "rich_text", "rich_text": {}}
                )
                title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)
                if sys_logger:
                    from logger import log_with_context
                    import logging
                    log_with_context(
                        sys_logger, logging.INFO,
                        "成功创建 video_title 属性",
                        property_type=title_prop_type
                    )
            except Exception as ensure_exc:
                print(f"Warning: failed to ensure video_title property: {ensure_exc}")
                if sys_logger:
                    from logger import log_with_context
                    import logging
                    log_with_context(
                        sys_logger, logging.WARNING,
                        "创建 video_title 属性失败",
                        error=str(ensure_exc)
                    )
                title_prop_type = None

        if title_prop_type is None:
            # Fallback to legacy property name for backward compatibility.
            title_property_name = "title"
            title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)

        if title_prop_type:
            if title_prop_type == "title":
                properties[title_property_name] = self.adapter.build_title_property(title)
            else:
                properties[title_property_name] = self.adapter.build_text_property(title)
        else:
            print("Warning: no usable title property found, skipping title field write")
            if sys_logger:
                sys_logger.warning("未找到可用的 title 属性，跳过 title 字段写入")

        record_machine_id = machine_id or self.config_data.get('sync', {}).get('machine_id')
        if record_machine_id:
            properties["machine_id"] = self.adapter.build_text_property(record_machine_id)

        try:
            self.adapter.add_page_to_database(database_id, properties)

            if chat_id in self._sent_archives_cache:
                self._sent_archives_cache[chat_id].add(video_id)

            if sys_logger:
                from logger import log_with_context
                import logging
                log_with_context(
                    sys_logger, logging.INFO,
                    "成功写入 Notion 已发送记录",
                    video_id=video_id,
                    chat_id=chat_id
                )
            return True
        except Exception as e:
            print(f"错误：向 Notion 写入已发送记录失败: {e}")
            if sys_logger:
                from logger import log_with_context
                import logging
                import traceback
                log_with_context(
                    sys_logger, logging.ERROR,
                    "向 Notion 写入发送记录失败",
                    video_id=video_id,
                    chat_id=chat_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc()
                )
            return False


    def has_sent_record(self, video_id: str, chat_id: str) -> bool:

        """检查是否已发送"""

        pass

    

    @abstractmethod

    def get_sent_records(self, chat_id: str) -> List[str]:

        """获取指定频道的已发送记录"""

        pass



    @abstractmethod

    def get_story_progress(self, group_name: str) -> Dict[str, Any]:

        """获取故事型频道的进度（last_video_id/timestamp 等）"""

        pass



    @abstractmethod

    def update_story_progress(self, group_name: str, progress: Dict[str, Any]) -> bool:

        """更新故事型频道进度"""

        pass





class LocalConfigProvider(BaseConfigProvider):

    """本地文件配置提供者"""

    

    def __init__(self, project_root: str, config_file: str):

        """

        初始化本地配置提供者

        

        Args:

            project_root: 项目根目录

            config_file: 配置文件路径

        """

        self.project_root = project_root

        self.config_file = config_file

        self._config_cache: Optional[Dict[str, Any]] = None

        self._download_archive: Optional[set] = None

        self._sent_archives: Dict[str, set] = {}

        self._channel_groups_cache: Optional[List[Dict[str, Any]]] = None

        self._story_progress_cache: Optional[Dict[str, Any]] = None

        self._story_progress_file = Path(self.project_root) / "data" / "story_progress.json"

    

    def _load_config(self, reload: bool = False) -> Optional[Dict[str, Any]]:

        """加载配置文件"""

        if self._config_cache is not None and not reload:

            return self._config_cache

        

        if not os.path.exists(self.config_file):

            return None

        

        try:

            with open(self.config_file, 'r', encoding='utf-8') as f:

                self._config_cache = yaml.safe_load(f)

                return self._config_cache

        except Exception as e:

            print(f"警告：加载配置文件失败: {e}")

            return None

    

    def _get_config_value(self, key_path: str, default: Any = None, reload: bool = False) -> Any:

        """从配置中获取值"""

        config = self._load_config(reload=reload)

        if config is None:

            return default

        

        keys = key_path.split('.')

        value = config

        

        try:

            for key in keys:

                value = value[key]

            return value

        except (KeyError, TypeError):

            return default

    def get_channel_groups(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """��ȡ����Ƶ��������"""
        if use_cache and self._channel_groups_cache is not None:
            return self._channel_groups_cache

        raw_groups = self._get_config_value('channel_groups', [], reload=not use_cache) or []
        processed: List[Dict[str, Any]] = []

        for group in raw_groups:
            grp = dict(group) if isinstance(group, dict) else {}
            channel_type = (grp.get('channel_type') or "realtime").lower()
            grp['channel_type'] = "story" if channel_type == "story" else "realtime"

            story_config = grp.get('story', {}) if isinstance(grp.get('story'), dict) else {}
            grp['story_interval_seconds'] = int(story_config.get('interval_seconds', 86400))
            grp['story_items_per_run'] = int(story_config.get('items_per_run', 1))
            grp['story_last_run_ts'] = None

            processed.append(grp)

        if use_cache:
            self._channel_groups_cache = processed

        return processed

    

    def get_telegram_token(self, group_index: int = 0) -> Optional[str]:

        """获取 Telegram Bot Token"""

        # 1. 尝试从指定频道组读取独立的 bot_token

        channel_groups = self.get_channel_groups()

        if channel_groups and group_index < len(channel_groups):

            group_token = channel_groups[group_index].get('bot_token')

            if group_token and group_token != "YOUR_BOT_TOKEN_HERE" and group_token.strip():

                return group_token

        

        # 2. 使用全局 telegram.bot_token

        global_token = self._get_config_value('telegram.bot_token')

        if global_token and global_token != "YOUR_BOT_TOKEN_HERE":

            return global_token

        

        # 3. 回退到环境变量

        from dotenv import load_dotenv

        load_dotenv(os.path.join(self.project_root, '.env'))

        return os.environ.get("BOT_TOKEN")

    

    def get_send_interval(self) -> int:

        """获取发送间隔（秒）"""

        return self._get_config_value('telegram.send_interval', 180)

    

    def get_download_interval(self) -> int:

        """获取下载间隔（秒）"""

        return self._get_config_value('downloader.download_interval', 29520)

    

    def get_filter_days(self) -> int:

        """获取视频过滤天数"""

        return self._get_config_value('downloader.filter_days', 3, reload=True)

    

    def get_max_videos_per_channel(self) -> int:

        """获取每个频道检查的最大视频数"""

        return self._get_config_value('downloader.max_videos_per_channel', 6, reload=True)

    

    def get_video_delay_min(self) -> int:

        """获取视频间最小延迟（秒）"""

        return self._get_config_value('downloader.video_delay_min', 120)

    

    def get_video_delay_max(self) -> int:

        """获取视频间最大延迟（秒）"""

        return self._get_config_value('downloader.video_delay_max', 240)

    

    def get_channel_delay_min(self) -> int:

        """获取频道间最小延迟（秒）"""

        return self._get_config_value('downloader.channel_delay_min', 0)

    

    def get_channel_delay_max(self) -> int:

        """获取频道间最大延迟（秒）"""

        return self._get_config_value('downloader.channel_delay_max', 0)

    

    def get_cookies_content(self) -> Optional[str]:

        """获取 Cookies 文件内容"""

        cookies_file = self._get_config_value('downloader.cookies_file', 'config/youtube.cookies')

        if not os.path.isabs(cookies_file):

            cookies_file = os.path.join(self.project_root, cookies_file)

        

        if os.path.exists(cookies_file):

            try:

                with open(cookies_file, 'r', encoding='utf-8') as f:

                    return f.read()

            except Exception as e:

                print(f"警告：读取 cookies 文件失败: {e}")

        return None

    

    def _load_download_archive(self) -> set:

        """加载下载存档"""

        if self._download_archive is not None:

            return self._download_archive



        archive_file = self._get_config_value('downloader.download_archive', 'data/download_archive.txt')

        if not os.path.isabs(archive_file):

            archive_file = os.path.join(self.project_root, archive_file)



        # 确保 data 目录存在

        os.makedirs(os.path.dirname(archive_file), exist_ok=True)



        self._download_archive = set()

        if os.path.exists(archive_file):

            try:

                with open(archive_file, 'r', encoding='utf-8') as f:

                    for line in f:

                        line = line.strip()

                        if line:
                            # 去除 youtube 前缀，只保存 video_id
                            vid = line.replace('youtube ', '')
                            self._download_archive.add(vid)

            except Exception as e:

                print(f"警告：加载下载存档失败: {e}")



        return self._download_archive

    

    def add_download_record(self, video_id: str, channel: str, status: str = "completed", machine_id: Optional[str] = None) -> bool:

        """添加下载记录"""

        archive_file = self._get_config_value('downloader.download_archive', 'data/download_archive.txt')

        if not os.path.isabs(archive_file):

            archive_file = os.path.join(self.project_root, archive_file)

        

        # 确保目录存在

        os.makedirs(os.path.dirname(archive_file), exist_ok=True)

        

        try:

            with open(archive_file, 'a', encoding='utf-8') as f:

                f.write(f"youtube {video_id}\n")

            

            # 更新缓存

            if self._download_archive is not None:

                self._download_archive.add(video_id)

            

            return True

        except Exception as e:

            print(f"错误：写入下载记录失败: {e}")

            return False

    

    def has_download_record(self, video_id: str) -> bool:

        """检查是否已下载"""

        return video_id in self._load_download_archive()

    

    def _load_sent_archive(self, chat_id: str) -> set:

        """加载已发送存档"""

        if chat_id in self._sent_archives:

            return self._sent_archives[chat_id]



        # 清理 chat_id，去除负号和特殊字符

        clean_id = str(chat_id).replace('-', '').replace('+', '')

        archive_file = os.path.join(self.project_root, 'data', f'sent_archive_{clean_id}.txt')



        # 确保 data 目录存在

        os.makedirs(os.path.dirname(archive_file), exist_ok=True)



        self._sent_archives[chat_id] = set()

        if os.path.exists(archive_file):

            try:

                with open(archive_file, 'r', encoding='utf-8') as f:

                    for line in f:

                        line = line.strip()

                        if line:

                            self._sent_archives[chat_id].add(line)

            except Exception as e:

                print(f"警告：加载已发送存档失败: {e}")



        return self._sent_archives[chat_id]

    

    def add_sent_record(self, video_id: str, chat_id: str, title: str, file_path: str, machine_id: Optional[str] = None) -> bool:

        """添加已发送记录"""

        # 清理 chat_id

        clean_id = str(chat_id).replace('-', '').replace('+', '')

        

        # 写入两个文件：machine-readable 和 human-readable

        archive_file = os.path.join(self.project_root, 'data', f'sent_archive_{clean_id}.txt')

        readable_file = os.path.join(self.project_root, 'data', f'sent_archive_{clean_id}_readable.txt')

        

        # 确保目录存在

        os.makedirs(os.path.dirname(archive_file), exist_ok=True)

        

        try:

            # Machine-readable

            with open(archive_file, 'a', encoding='utf-8') as f:

                f.write(f"{video_id}\n")

            

            # Human-readable

            with open(readable_file, 'a', encoding='utf-8') as f:

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                f.write(f"[{timestamp}] {video_id} | {title}\n")

            

            # 更新缓存

            if chat_id in self._sent_archives:

                self._sent_archives[chat_id].add(video_id)

            

            return True

        except Exception as e:

            print(f"错误：写入已发送记录失败: {e}")

            return False

    

    def has_sent_record(self, video_id: str, chat_id: str) -> bool:

        """检查是否已发送"""

        return video_id in self._load_sent_archive(chat_id)

    

    def get_sent_records(self, chat_id: str) -> List[str]:

        """获取指定频道的已发送记录"""

        return list(self._load_sent_archive(chat_id))



    def _load_story_progress(self) -> Dict[str, Any]:

        """加载故事型频道进度缓存"""

        if self._story_progress_cache is not None:

            return self._story_progress_cache



        progress: Dict[str, Any] = {}

        try:

            if self._story_progress_file.exists():

                with open(self._story_progress_file, "r", encoding="utf-8") as f:

                    progress = json.load(f)

        except Exception as e:

            print(f"警告：读取故事进度文件失败，已忽略: {e}")

            progress = {}



        self._story_progress_cache = progress

        return self._story_progress_cache



    def _save_story_progress(self):

        if self._story_progress_cache is None:

            return

        try:

            self._story_progress_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self._story_progress_file, "w", encoding="utf-8") as f:

                json.dump(self._story_progress_cache, f, ensure_ascii=False, indent=2)

        except Exception as e:

            print(f"警告：保存故事进度失败: {e}")



    def get_story_progress(self, group_name: str) -> Dict[str, Any]:
        # 优先从 story_progress.json 读取
        progress = self._load_story_progress()
        if group_name in progress and progress[group_name]:
            return progress[group_name]
        
        # 如果没有，尝试从 config.yaml 的 channel_groups 读取初始进度
        channel_groups = self.get_channel_groups()
        for group in channel_groups:
            if group.get('name') == group_name:
                initial_progress = {}
                if group.get('story_last_video_id'):
                    initial_progress['last_video_id'] = group['story_last_video_id']
                if group.get('story_last_timestamp') is not None:
                    initial_progress['last_timestamp'] = group['story_last_timestamp']
                if group.get('story_last_run_ts') is not None:
                    initial_progress['last_run_ts'] = group['story_last_run_ts']
                return initial_progress
        
        return {}



    def update_story_progress(self, group_name: str, progress: Dict[str, Any]) -> bool:

        cache = self._load_story_progress()

        cache[group_name] = progress

        self._story_progress_cache = cache

        self._save_story_progress()

        return True





class NotionConfigProvider(BaseConfigProvider):

    """Notion 配置提供者"""

    

    def __init__(self, notion_adapter, config_data: Dict[str, Any]):

        """

        初始化 Notion 配置提供者

        

        Args:

            notion_adapter: NotionAdapter 实例

            config_data: Notion 配置数据（包含 database_ids、page_ids 等）

        """

        self.adapter = notion_adapter

        self.config_data = config_data

        self._channel_groups_cache: Optional[List[Dict]] = None

        self._global_settings_cache: Optional[Dict] = None

        self._download_archive_cache: Optional[set] = None

        self._sent_archives_cache: Dict[str, set] = {}

        self._channel_page_id_map: Dict[str, str] = {}
    

    def _load_global_settings(self) -> Dict[str, Any]:

        """

        从 Notion 加载全局设置

        

        优先从 Notion GlobalSettings 页面读取最新配置，

        如果不存在或解析失败，则回退到本地 config.yaml

        """

        if self._global_settings_cache is not None:

            return self._global_settings_cache

        

        settings = self._load_global_settings_from_notion()

        if settings is None:

            settings = self._load_global_settings_from_yaml()

        

        self._global_settings_cache = settings or {}

        return self._global_settings_cache

    

    def _load_global_settings_from_notion(self) -> Optional[Dict[str, Any]]:

        """尝试从 Notion 页面读取全局设置"""

        page_id = self.config_data.get('page_ids', {}).get('global_settings')

        if not page_id:

            return None

        

        try:

            blocks = self.adapter.get_page_blocks(page_id)

        except Exception as e:

            print(f"警告：从 Notion 读取全局设置失败: {e}")

            return None

        

        import yaml

        

        # 从上往下遍历代码块，读取最上面的（最新的）配置

        for block in blocks:

            if block.get('type') != 'code':

                continue

            

            content = self.adapter.extract_code_block_text(block)

            if not content:

                continue

            

            try:

                data = yaml.safe_load(content) or {}

            except yaml.YAMLError as e:

                print(f"警告：解析 Notion 全局设置 YAML 失败: {e}")

                continue

            

            settings = {}

            telegram_config = data.get('telegram', {})

            downloader_config = data.get('downloader', {})

            

            if isinstance(telegram_config, dict):

                if 'bot_token' in telegram_config:

                    settings['bot_token'] = telegram_config['bot_token']

                if 'send_interval' in telegram_config:

                    settings['send_interval'] = telegram_config['send_interval']

            

            if isinstance(downloader_config, dict):

                for key in [

                    'download_interval', 'filter_days', 'max_videos_per_channel',

                    'video_delay_min', 'video_delay_max', 'channel_delay_min', 'channel_delay_max'

                ]:

                    if key in downloader_config:

                        settings[key] = downloader_config[key]

            

            if settings:

                return settings

        

        return None

    

    def _load_global_settings_from_yaml(self) -> Dict[str, Any]:

        """回退到本地 YAML 读取全局配置"""

        import config as config_module

        yaml_config = config_module.load_yaml_config()

        if not yaml_config:

            return {}

        

        settings = {}

        telegram_config = yaml_config.get('telegram', {})

        downloader_config = yaml_config.get('downloader', {})

        

        if isinstance(telegram_config, dict):

            if 'bot_token' in telegram_config:

                settings['bot_token'] = telegram_config['bot_token']

            if 'send_interval' in telegram_config:

                settings['send_interval'] = telegram_config['send_interval']

        

        if isinstance(downloader_config, dict):

            for key in [

                'download_interval', 'filter_days', 'max_videos_per_channel',

                'video_delay_min', 'video_delay_max', 'channel_delay_min', 'channel_delay_max'

            ]:

                if key in downloader_config:

                    settings[key] = downloader_config[key]

        

        return settings

    

    def get_channel_groups(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取所有频道组配置"""
        if use_cache and self._channel_groups_cache is not None:
            return self._channel_groups_cache

        database_id = self.config_data.get('database_ids', {}).get('config')
        if not database_id:
            return []

        try:
            pages = self.adapter.query_database(database_id)
            groups = []
            self._channel_page_id_map = {}

            for page in pages:
                name = self.adapter.extract_property_value(page, 'name')
                description = self.adapter.extract_property_value(page, 'description')
                enabled = self.adapter.extract_property_value(page, 'enabled')
                chat_id = self.adapter.extract_property_value(page, 'telegram_chat_id')
                audio_folder = self.adapter.extract_property_value(page, 'audio_folder')
                youtube_channels_data = self.adapter.extract_property_value(page, 'youtube_channels')
                channel_type = self.adapter.extract_property_value(page, 'channel_type') or 'realtime'
                story_last_video_id = self.adapter.extract_property_value(page, 'story_last_video_id')
                story_last_timestamp = self.adapter.extract_property_value(page, 'story_last_timestamp')
                story_interval_seconds = self.adapter.extract_property_value(page, 'story_interval_seconds')
                story_items_per_run = self.adapter.extract_property_value(page, 'story_items_per_run')
                story_last_run_ts = self.adapter.extract_property_value(page, 'story_last_run_ts')
                story_last_run_ts = self.adapter.extract_property_value(page, 'story_last_run_ts')

                youtube_channels = []
                if isinstance(youtube_channels_data, list):
                    youtube_channels = [ch.strip() for ch in youtube_channels_data if ch and ch.strip()]
                elif isinstance(youtube_channels_data, str):
                    youtube_channels = [ch.strip() for ch in youtube_channels_data.split('\n') if ch.strip()]
                normalized_type = 'story' if str(channel_type).lower() == 'story' else 'realtime'

                group = {
                    'name': name or '',
                    'description': description or '',
                    'enabled': enabled if enabled is not None else True,
                    'telegram_chat_id': chat_id or '',
                    'audio_folder': audio_folder or '',
                    'youtube_channels': youtube_channels,
                    'channel_type': normalized_type,
                    'story_interval_seconds': int(story_interval_seconds or 86400),
                    'story_items_per_run': int(story_items_per_run or 1),
                    'story_last_run_ts': int(story_last_run_ts) if story_last_run_ts is not None else None,
                }

                if normalized_type == 'story':
                    if story_last_video_id:
                        group['story_last_video_id'] = story_last_video_id
                    if story_last_timestamp is not None:
                        try:
                            group['story_last_timestamp'] = int(story_last_timestamp)
                        except Exception:
                            pass

                page_id = page.get('id') if isinstance(page, dict) else None
                if page_id:
                    group['_notion_page_id'] = page_id
                    if name:
                        self._channel_page_id_map[name] = page_id

                groups.append(group)

            if use_cache:
                self._channel_groups_cache = groups

            return groups
        except Exception as e:
            print(f"警告：从 Notion 获取频道分组失败: {e}")
            return []
    def get_telegram_token(self, group_index: int = 0) -> Optional[str]:

        """��ȡ Telegram Bot Token"""

        settings = self._load_global_settings()

        return settings.get('bot_token')

    


    def get_send_interval(self) -> int:

        """获取发送间隔（秒）"""

        settings = self._load_global_settings()

        return settings.get('send_interval', 180)

    

    def get_download_interval(self) -> int:

        """获取下载间隔（秒）"""

        settings = self._load_global_settings()

        return settings.get('download_interval', 29520)

    

    def get_filter_days(self) -> int:

        """获取视频过滤天数"""

        settings = self._load_global_settings()

        return settings.get('filter_days', 3)

    

    def get_max_videos_per_channel(self) -> int:

        """获取每个频道检查的最大视频数"""

        settings = self._load_global_settings()

        return settings.get('max_videos_per_channel', 6)

    

    def get_video_delay_min(self) -> int:

        """获取视频间最小延迟（秒）"""

        settings = self._load_global_settings()

        return settings.get('video_delay_min', 120)

    

    def get_video_delay_max(self) -> int:

        """获取视频间最大延迟（秒）"""

        settings = self._load_global_settings()

        return settings.get('video_delay_max', 240)

    

    def get_channel_delay_min(self) -> int:

        """获取频道间最小延迟（秒）"""

        settings = self._load_global_settings()

        return settings.get('channel_delay_min', 0)

    

    def get_channel_delay_max(self) -> int:

        """获取频道间最大延迟（秒）"""

        settings = self._load_global_settings()

        return settings.get('channel_delay_max', 0)

    

    def get_cookies_content(self) -> Optional[str]:

        """获取 Cookies 文件内容"""

        page_id = self.config_data.get('page_ids', {}).get('cookies')

        if not page_id:

            return None

        

        try:

            blocks = self.adapter.get_page_blocks(page_id)

            # 遍历 code block（从最新的 block 开始，方便取到最近更新的 cookies）

            for block in reversed(blocks):

                if block.get('type') == 'code':

                    code_data = block.get('code', {})

                    rich_text = code_data.get('rich_text', [])

                    return self.adapter.extract_plain_text(rich_text)

            return None

        except Exception as e:

            print(f"警告：从 Notion 读取 cookies 失败: {e}")

            return None

    

    def _load_download_archive(self) -> set:

        """从 Notion 加载下载存档"""

        if self._download_archive_cache is not None:

            return self._download_archive_cache

        

        database_id = self.config_data.get('database_ids', {}).get('download_archive')

        if not database_id:

            return set()

        

        try:

            pages = self.adapter.query_database(database_id)

            self._download_archive_cache = set()

            for page in pages:

                video_id = self.adapter.extract_property_value(page, 'video_id')

                if video_id:

                    self._download_archive_cache.add(video_id)

            return self._download_archive_cache

        except Exception as e:

            print(f"警告：从 Notion 加载下载存档失败: {e}")

            return set()

    

    def add_download_record(self, video_id: str, channel: str, status: str = "completed", machine_id: Optional[str] = None) -> bool:

        """添加下载记录到 Notion"""

        sys_logger = _get_sys_logger()

        

        database_id = self.config_data.get('database_ids', {}).get('download_archive')

        if not database_id:

            if sys_logger:

                sys_logger.error("Notion 下载记录数据库 ID 未配置")

            return False

        

        try:

            properties = {

                "video_id": self.adapter.build_title_property(video_id),

                "channel": self.adapter.build_text_property(channel),

                "download_date": self.adapter.build_date_property(

                    datetime.now(timezone.utc).isoformat()

                ),

                "status": self.adapter.build_select_property(status)

            }



            record_machine_id = machine_id or self.config_data.get('sync', {}).get('machine_id')

            if record_machine_id:

                properties["machine_id"] = self.adapter.build_text_property(record_machine_id)

            

            self.adapter.add_page_to_database(database_id, properties)



            # 更新缓存

            if self._download_archive_cache is not None:

                self._download_archive_cache.add(video_id)

            

            if sys_logger:
                from logger import log_with_context
                import logging

                log_with_context(

                    sys_logger, logging.INFO,

                    "成功写入 Notion 下载记录",

                    video_id=video_id,

                    channel=channel

                )

            

            return True

        except Exception as e:

            print(f"错误：向 Notion 写入下载记录失败: {e}")

            if sys_logger:

                from logger import log_with_context

                import logging

                import traceback

                log_with_context(

                    sys_logger, logging.ERROR,

                    "向 Notion 写入下载记录失败",

                    video_id=video_id,

                    channel=channel,

                    error=str(e),

                    error_type=type(e).__name__,

                    traceback=traceback.format_exc()

                )

            return False

    

    def has_download_record(self, video_id: str) -> bool:

        """检查是否已下载"""

        return video_id in self._load_download_archive()

    

    def _load_sent_archive(self, chat_id: str) -> set:

        """从 Notion 加载已发送存档"""

        if chat_id in self._sent_archives_cache:

            return self._sent_archives_cache[chat_id]

        

        database_id = self.config_data.get('database_ids', {}).get('sent_archive')

        if not database_id:

            return set()

        

        try:

            # 查询指定 chat_id 的记录

            filter_obj = {

                "property": "chat_id",

                "rich_text": {

                    "equals": str(chat_id)

                }

            }

            

            pages = self.adapter.query_database(database_id, filter_obj=filter_obj)

            self._sent_archives_cache[chat_id] = set()

            

            for page in pages:

                video_id = self.adapter.extract_property_value(page, 'video_id')

                if video_id:

                    self._sent_archives_cache[chat_id].add(video_id)

            

            return self._sent_archives_cache[chat_id]

        except Exception as e:

            print(f"警告：从 Notion 加载已发送存档失败: {e}")

            return set()

    

    def add_sent_record(self, video_id: str, chat_id: str, title: str, file_path: str, machine_id: Optional[str] = None) -> bool:
        """添加已发送记录到 Notion"""
        sys_logger = _get_sys_logger()

        database_id = self.config_data.get('database_ids', {}).get('sent_archive')
        if not database_id:
            if sys_logger:
                sys_logger.error("Notion 已发送记录数据库 ID 未配置")
            return False

        if sys_logger:
            from logger import log_with_context
            import logging
            log_with_context(
                sys_logger, logging.INFO,
                "准备写入 Notion 发送记录",
                video_id=video_id,
                chat_id=chat_id,
                title=title[:50] + "..." if len(title) > 50 else title,
                database_id=database_id[:8] + "..."
            )

        properties = {
            "video_id": self.adapter.build_title_property(video_id),
            "chat_id": self.adapter.build_text_property(str(chat_id)),
            "sent_date": self.adapter.build_date_property(
                datetime.now(timezone.utc).isoformat()
            ),
            "file_path": self.adapter.build_text_property(file_path)
        }

        title_property_name = "video_title"
        title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)

        if title_prop_type is None:
            try:
                self.adapter.ensure_database_property(
                    database_id,
                    title_property_name,
                    {"type": "rich_text", "rich_text": {}}
                )
                title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)
                if sys_logger:
                    from logger import log_with_context
                    import logging
                    log_with_context(
                        sys_logger, logging.INFO,
                        "成功创建 video_title 属性",
                        property_type=title_prop_type
                    )
            except Exception as ensure_exc:
                print(f"Warning: failed to ensure video_title property: {ensure_exc}")
                if sys_logger:
                    from logger import log_with_context
                    import logging
                    log_with_context(
                        sys_logger, logging.WARNING,
                        "创建 video_title 属性失败",
                        error=str(ensure_exc)
                    )
                title_prop_type = None

        if title_prop_type is None:
            # Fallback to legacy property name for backward compatibility.
            title_property_name = "title"
            title_prop_type = self.adapter.get_database_property_type(database_id, title_property_name)

        if title_prop_type:
            if title_prop_type == "title":
                properties[title_property_name] = self.adapter.build_title_property(title)
            else:
                properties[title_property_name] = self.adapter.build_text_property(title)
        else:
            print("Warning: no usable title property found, skipping title field write")
            if sys_logger:
                sys_logger.warning("未找到可用的 title 属性，跳过 title 字段写入")

        record_machine_id = machine_id or self.config_data.get('sync', {}).get('machine_id')
        if record_machine_id:
            properties["machine_id"] = self.adapter.build_text_property(record_machine_id)

        try:
            self.adapter.add_page_to_database(database_id, properties)

            if chat_id in self._sent_archives_cache:
                self._sent_archives_cache[chat_id].add(video_id)

            if sys_logger:
                from logger import log_with_context
                import logging
                log_with_context(
                    sys_logger, logging.INFO,
                    "成功写入 Notion 已发送记录",
                    video_id=video_id,
                    chat_id=chat_id
                )
            return True
        except Exception as e:
            print(f"错误：向 Notion 写入已发送记录失败: {e}")
            if sys_logger:
                from logger import log_with_context
                import logging
                import traceback
                log_with_context(
                    sys_logger, logging.ERROR,
                    "向 Notion 写入发送记录失败",
                    video_id=video_id,
                    chat_id=chat_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc()
                )
            return False


    def has_sent_record(self, video_id: str, chat_id: str) -> bool:

        """检查是否已发送"""

        return video_id in self._load_sent_archive(chat_id)

    

    def get_sent_records(self, chat_id: str) -> List[str]:

        """获取指定频道的已发送记录"""

        return list(self._load_sent_archive(chat_id))


    def get_story_progress(self, group_name: str) -> Dict[str, Any]:
        page_id = self._channel_page_id_map.get(group_name)
        if not page_id:
            return {}
        try:
            page = self.adapter.get_page(page_id)
            video_id = self.adapter.extract_property_value(page, 'story_last_video_id')
            timestamp = self.adapter.extract_property_value(page, 'story_last_timestamp')
            progress: Dict[str, Any] = {}

            if video_id:
                progress['last_video_id'] = video_id
            if timestamp is not None:
                try:
                    progress['last_timestamp'] = int(timestamp)
                except Exception:
                    pass
            last_run_ts = self.adapter.extract_property_value(page, 'story_last_run_ts')
            if last_run_ts is not None:
                try:
                    progress['last_run_ts'] = int(last_run_ts)
                except Exception:
                    pass
            return progress
        except Exception as e:
            print(f"警告：从 Notion 获取故事进度失败: {e}")
            return {}

    def update_story_progress(self, group_name: str, progress: Dict[str, Any]) -> bool:
        page_id = self._channel_page_id_map.get(group_name)
        if not page_id:
            return False
        properties: Dict[str, Any] = {}
        video_id = progress.get('last_video_id')
        timestamp = progress.get('last_timestamp')
        last_run_ts = progress.get('last_run_ts')
        if video_id:
            properties['story_last_video_id'] = self.adapter.build_text_property(str(video_id))
        if timestamp is not None:
            try:
                properties['story_last_timestamp'] = {"number": int(timestamp)}
            except Exception:
                pass
        if last_run_ts is not None:
            try:
                properties['story_last_run_ts'] = {"number": int(last_run_ts)}
            except Exception:
                pass
        if not properties:
            return False
        try:
            self.adapter.update_page(page_id, properties)
            return True
        except Exception as e:
            print(f"警告：更新 Notion 故事进度失败: {e}")
            return False
            print(f"警告：更新 Notion 故事进度失败: {e}")
            return False
