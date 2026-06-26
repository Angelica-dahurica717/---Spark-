# crawler/storage.py
# >>>【CSV存储模块 数据持久化 爬虫存储】<<<

import csv
import os
import logging
from config import OUTPUT_CSV, CSV_FIELDS

logger = logging.getLogger(__name__)


class CSVStorage:
    """将爬取的谣言数据保存为 CSV 文件"""

    def __init__(self, filepath: str = OUTPUT_CSV):
        self.filepath = filepath
        self._id_counter = 0
        self._initialized = False

    def _init_file(self):
        # >>>【CSV文件初始化 创建表头 首次启动】<<<
        """初始化 CSV 文件，写入表头（若文件不存在）"""
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
            logger.info(f"[Storage] 已创建 CSV 文件：{self.filepath}")
        else:
            # 统计已有行数，继续ID计数
            with open(self.filepath, "r", encoding="utf-8-sig") as f:
                self._id_counter = sum(1 for _ in f) - 1  # 减去表头
            logger.info(f"[Storage] 续写已有 CSV，当前已有 {self._id_counter} 条记录")
        self._initialized = True

    def save(self, record: dict):
        # >>>【保存单条数据 追加写入CSV】<<<
        """
        保存单条记录到 CSV
        :param record: dict，包含 title, url, publish_date, content, source, category
        """
        if not self._initialized:
            self._init_file()

        self._id_counter += 1
        record["id"] = self._id_counter

        with open(self.filepath, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writerow(record)

    def save_batch(self, records: list):
        """批量保存记录"""
        for record in records:
            self.save(record)
        logger.info(f"[Storage] 已批量写入 {len(records)} 条，当前总计 {self._id_counter} 条")

    def get_existing_urls(self) -> set:
        # >>>【断点续爬 获取已爬取URL集合 增量爬取去重】<<<
        """读取 CSV 中已有的 URL 集合，用于去重断点续爬"""
        urls = set()
        if not os.path.exists(self.filepath):
            return urls
        try:
            with open(self.filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("url"):
                        urls.add(row["url"])
        except Exception as e:
            logger.warning(f"[Storage] 读取已有URL失败：{e}")
        return urls
