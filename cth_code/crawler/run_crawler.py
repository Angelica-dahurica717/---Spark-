# crawler/run_crawler.py
# 爬虫启动入口

import logging
import sys
import os

# 将当前目录加入路径（确保能 import 同级模块）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spider import PiyaoSpider
from storage import CSVStorage
from config import OUTPUT_CSV

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),                          # 控制台输出
        logging.FileHandler("crawler.log", encoding="utf-8"),       # 文件日志
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("谣言数据爬虫启动")
    logger.info(f"数据将保存至：{OUTPUT_CSV}")

    # 初始化存储
    storage = CSVStorage()

    # 加载断点续爬（已有URL，避免重复爬取）
    existing_urls = storage.get_existing_urls()
    if existing_urls:
        logger.info(f"检测到断点续爬，已有 {len(existing_urls)} 条记录，将跳过已爬URL")

    # 初始化爬虫
    spider = PiyaoSpider(existing_urls=existing_urls)

    # 启动
    count = spider.run(storage)
    logger.info(f"爬虫任务完成，本次新增 {count} 条数据")


if __name__ == "__main__":
    main()
