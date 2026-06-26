# crawler/spider.py
# >>>【爬虫核心模块 数据采集模块】<<<
# 功能：通过 JSON 数据源获取列表 + BeautifulSoup 解析详情页正文

import re
import time
import json
import random
import logging
import requests
from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from config import (
    BASE_URL, LIST_URL,
    HEADERS, DELAY_MIN, DELAY_MAX, TIMEOUT,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)

# 数据源根URL
JRPY_BASE = "https://www.piyao.org.cn/jrpy/"


class PiyaoSpider:
    """中国互联网联合辟谣平台爬虫"""

    def __init__(self, existing_urls: set = None):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.existing_urls = existing_urls or set()

    # ==================== 工具方法 ====================

    def _sleep(self):
        # >>>【随机延迟 反反爬虫 模拟人工操作】<<<
        """随机延迟，模拟人工操作"""
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)

    def _get(self, url: str, is_json: bool = False) -> Optional[requests.Response]:
        # >>>【指数退避重试 容错机制 网络请求】<<<
        """发送GET请求，支持重试"""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                if not is_json:
                    resp.encoding = "utf-8"
                return resp
            except requests.exceptions.HTTPError as e:
                logger.warning(f"[HTTP错误] {url} | 状态码 {e.response.status_code} | 第{attempt}次")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[连接错误] {url} | 第{attempt}次")
            except requests.exceptions.Timeout:
                logger.warning(f"[超时] {url} | 第{attempt}次")
            except Exception as e:
                logger.warning(f"[未知错误] {url} | {e} | 第{attempt}次")

            if attempt < MAX_RETRIES:
                # >>>【指数退避算法 2的N次幂退避】<<<  第1次失败就1秒，第2次就2秒，第3次就4秒
                time.sleep(2 ** attempt)  # 指数退避

        logger.error(f"[放弃] 请求失败 {MAX_RETRIES} 次，跳过：{url}")
        return None

    @staticmethod
    def _extract_date_from_title(title: str) -> str:
        """从标题括号中提取日期"""
        match = re.search(r'（(\d{4})[··](\d{2})[··](\d{2})）', title)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return ""

    @staticmethod
    def _extract_date_from_url(url: str) -> str:
        """从URL路径中提取日期"""
        match = re.search(r'/(\d{4})(\d{2})(\d{2})/', url)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return ""

    # ==================== JSON数据源爬取 ====================

    def _get_datasource_id(self) -> Optional[str]:
        # >>>【正则表达式提取datasource_id 动态数据源】<<<
        """
        从 index.htm 的 HTML 中提取 datasource ID
        页面中有: <ul id="list" data="datasource:e0bb8399925745768458fc917f771895" ...>
        """
        logger.info(f"[数据源] 正在获取 datasource ID：{LIST_URL}")
        resp = self._get(LIST_URL)
        if resp is None:
            return None

        # 从 HTML 文本中匹配 datasource:xxxx
        match = re.search(r'datasource:([a-f0-9]{32})', resp.text)
        if match:
            ds_id = match.group(1)
            logger.info(f"[数据源] 找到 datasource ID：{ds_id}")
            return ds_id

        logger.error("[数据源] 未能从HTML中找到 datasource ID，请手动检查页面结构")
        return None

    def fetch_article_list_from_json(self) -> list:
        # >>>【请求JSON数据源 获取文章列表元数据 批量获取】<<<
        """
        从 JSON 数据源获取所有文章元数据
        返回包含 {title, url, publishTime, sourceText} 等信息的列表
        """
        # Step 1: 获取 datasource ID
        ds_id = self._get_datasource_id()
        if not ds_id:
            return []

        # Step 2: 构造 JSON URL 并请求
        json_url = f"{JRPY_BASE}ds_{ds_id}.json"
        logger.info(f"[数据源] 正在获取文章列表 JSON：{json_url}")

        resp = self._get(json_url, is_json=True)
        if resp is None:
            return []

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            logger.error(f"[数据源] JSON解析失败：{e}")
            return []

        # JSON 结构：data["datasource"] 是文章列表
        articles_raw = data.get("datasource", [])
        logger.info(f"[数据源] JSON中共有 {len(articles_raw)} 篇文章")

        articles = []
        for item in articles_raw:
            # 从相对路径 ../20260326/xxxxx/c.html 构造完整URL
            publish_url = item.get("publishUrl", "")
            if not publish_url:
                continue

            full_url = urljoin(JRPY_BASE, publish_url)

            # >>>【断点续爬 增量爬取 URL去重】<<<
            # 去重
            if full_url in self.existing_urls:
                continue

            articles.append({
                "url": full_url,
                "title_from_json": item.get("showTitle", item.get("title", "")),
                "publish_time": item.get("publishTime", ""),
                "source_text": item.get("sourceText", "中国互联网联合辟谣平台"),
                "summary_from_json": item.get("summary", ""),
                "keywords": item.get("keywords", ""),
                "content_id": item.get("contentId", ""),
            })

        logger.info(f"[数据源] 过滤已有记录后，待爬取 {len(articles)} 篇")
        return articles

    # ==================== 详情页爬取 ====================

    def parse_detail(self, article_meta: dict) -> Optional[dict]:
        # >>>【BeautifulSoup详情页解析 HTML正文提取】<<<
        """
        解析谣言详情页，结合 JSON 元数据和 HTML 正文
        返回字典：{title, url, publish_date, content, source, category}
        """
        url = article_meta["url"]
        resp = self._get(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # ----- 提取标题 -----
        title = article_meta.get("title_from_json", "")

        # 备用：从页面 h1 或 title 标签提取
        if not title:
            title_tag = soup.select_one(".title") or soup.select_one("h1")
            if title_tag:
                title = title_tag.get_text(strip=True)
        if not title:
            page_title = soup.find("title")
            if page_title:
                title = re.sub(r'\s*[-_|]\s*中国互联网联合辟谣平台\s*$', '', page_title.get_text(strip=True))

        # 清理标题末尾的日期括号
        title_clean = re.sub(r'（\d{4}[··]\d{2}[··]\d{2}）$', '', title).strip()

        # ----- 提取日期 -----
        publish_date = ""
        # 优先从JSON的publishTime字段提取
        pt = article_meta.get("publish_time", "")
        if pt:
            m = re.match(r'(\d{4})-(\d{2})-(\d{2})', pt)
            if m:
                publish_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # 备用：从标题或URL提取
        if not publish_date:
            publish_date = self._extract_date_from_title(title)
        if not publish_date:
            publish_date = self._extract_date_from_url(url)

        # ----- 提取正文内容 -----
        content = ""
        content_div = (
            soup.select_one("#content")
            or soup.select_one(".content")
            or soup.select_one(".article-content")
            or soup.select_one(".detail-content")
            or soup.select_one("article")
        )

        if content_div:
            # >>>【清除干扰标签 script style 干静内容过滤】<<<
            # 移除脚本、样式、导航等无关元素
            for tag in content_div.find_all(["script", "style", "nav"]):
                tag.decompose()
            raw_content = content_div.get_text(separator="\n", strip=True)

            # 清理导航面包屑
            lines = raw_content.split("\n")
            clean_lines = []
            skip_prefixes = ("首页", ">", "正文", "您当前位置", "当前位置")
            start_capturing = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if not start_capturing:
                    if any(line.startswith(p) for p in skip_prefixes):
                        continue
                    start_capturing = True
                clean_lines.append(line)
            content = "\n".join(clean_lines)

        # 若页面正文为空，使用 JSON 中的 summary 字段兜底
        if not content:
            content = article_meta.get("summary_from_json", "")

        # ----- 提取来源 -----
        source = article_meta.get("source_text", "中国互联网联合辟谣平台")
        source_tag = soup.select_one(".source") or soup.select_one(".editor")
        if source_tag:
            source_text = source_tag.get_text(strip=True)
            if "来源" in source_text:
                source = source_text.replace("来源：", "").replace("来源:", "").strip()

        # ----- 分类 -----
        category = "今日辟谣"  # 均来自 /jrpy/ 栏目

        # ----- 关键词 -----
        keywords = article_meta.get("keywords", "")

        if not title_clean:
            logger.warning(f"[详情页] 标题为空，跳过：{url}")
            return None

        return {
            "title": title_clean,
            "url": url,
            "publish_date": publish_date,
            "content": content[:3000],  # 限制正文长度
            "source": source,
            "category": category,
            "keywords": keywords,
        }

    # ==================== 主流程 ====================

    def run(self, storage) -> int:
        """
        1. 从 JSON 数据源获取所有文章元数据
        2. 逐条爬取详情页获取正文
        3. 存储到CSV
        返回成功采集的条数
        """
        logger.info("=" * 50)
        logger.info("[爬虫] 开始运行 - 中国互联网联合辟谣平台")
        logger.info("=" * 50)

        # Step 1: 从JSON获取文章列表
        logger.info("[Step 1] 从 JSON 数据源获取文章列表...")
        articles = self.fetch_article_list_from_json()

        if not articles:
            logger.warning("[爬虫] 未获取到任何文章，程序退出")
            return 0

        logger.info(f"[Step 1] 共获取到 {len(articles)} 篇待爬文章")

        # Step 2: 爬取详情页
        logger.info("[Step 2] 开始爬取详情页...")
        success_count = 0
        fail_count = 0

        for idx, article_meta in enumerate(articles, 1):
            logger.info(f"[详情页] ({idx}/{len(articles)}) {article_meta['url']}")

            record = self.parse_detail(article_meta)
            if record:
                storage.save(record)
                success_count += 1
            else:
                fail_count += 1

            self._sleep()

            # 每50条打印一次进度
            if idx % 50 == 0:
                logger.info(f"[进度] {idx}/{len(articles)} | 成功:{success_count} 失败:{fail_count}")

        logger.info("=" * 50)
        logger.info(f"[爬虫] 完成！成功:{success_count} 失败:{fail_count}")
        logger.info("[爬虫] 数据已保存到 CSV")
        logger.info("=" * 50)

        return success_count
