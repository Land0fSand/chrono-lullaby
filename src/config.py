import os
from dotenv import load_dotenv

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 定义所有路径
AUDIO_FOLDER = os.path.join(PROJECT_ROOT, "au")
TEMP_AUDIO_FOLDER = os.path.join(PROJECT_ROOT, "au_temp")
CHANNELS_FILE = os.path.join(PROJECT_ROOT, "channels.txt")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
DOWNLOAD_ARCHIVE = os.path.join(PROJECT_ROOT, "download_archive.txt")
DEBUG_INFO = os.path.join(PROJECT_ROOT, "debug_closest_video.json")
STORY_FILE = os.path.join(PROJECT_ROOT, "story.txt")
COOKIES_FILE = os.path.join(PROJECT_ROOT, "youtube.cookies")

# 加载环境变量
load_dotenv(ENV_FILE)

# 确保必要的目录存在
os.makedirs(AUDIO_FOLDER, exist_ok=True)
