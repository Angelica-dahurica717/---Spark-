# crawler/config.py
# >>>【爬虫配置文件】<<<  搜索关键词: 爬虫配置
# 本文件集中管理所有爬虫运行所需的常量参数，修改爬取行为只需改这里。

# ==================== 目标网站配置 ====================
# >>>【目标网站 数据来源配置】<<<
BASE_URL = "https://www.piyao.org.cn"

# 今日辟谣 - 列表页
LIST_URL = "https://www.piyao.org.cn/jrpy/index.htm"

# 分页机制说明：网站通过动态JSON数据源加载，无传统分页URL
# >>>【动态JSON数据源 网站反爬机制】<<<
# 数据源ID从 index.htm 的 HTML 中提取，完整数据一次性从 ds_{id}.json 获取

# ==================== 请求配置 ====================
# >>>【请求头伪装 反反爬虫 User-Agent配置】<<<
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.piyao.org.cn/",
}

# >>>【随机延迟 反反爬虫 防IP封禁】<<<
# 请求延迟配置（秒）：每次请求后随机休眠 1.5~3.5 秒，模拟人类操作
DELAY_MIN = 1.5
DELAY_MAX = 3.5

# 请求超时（秒）
TIMEOUT = 15

# >>>【失败重试次数 指数退避重试配置】<<<
MAX_RETRIES = 3

# ==================== 数据配置 ====================
# >>>【路径配置 相对路径 数据存储路径】<<<
# 利用 __file__ 动态定位项目根目录，保证在不同电脑/操作系统上都能正确找到数据文件夹
import os
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)

# >>>【CSV文件输出路径 原始数据存放位置】<<<
OUTPUT_CSV = os.path.join(DATA_DIR, "piyao_rumors.csv")

# CSV 字段列表
CSV_FIELDS = [
    "id",           # 自增ID
    "title",        # 谣言标题
    "url",          # 详情页URL
    "publish_date", # 发布日期 (YYYY-MM-DD)
    "content",      # 正文内容（辟谣详情）
    "source",       # 信息来源
    "category",     # 分类标签
    "keywords",     # 关键词（来自JSON元数据）
]
