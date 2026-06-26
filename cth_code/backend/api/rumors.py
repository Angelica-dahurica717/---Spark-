# backend/api/rumors.py
# >>>【谣言检索API 分页列表 关键词主题日期筛选】<<<
import csv
import json
import re
from flask import request, jsonify
from api import rumors_bp
from auth import login_required
from config import CSV_FILE, TOPIC_DIST_FILE
from api.analysis import _filter_words

_rumors_cache = None
_topic_map_cache = None   # {url: dominant_topic}


def _load_rumors():
    # >>>【从 CSV加载谣言数据到内存 内存缓存谣言记录】<<<
    """从 CSV 加载所有谣言记录"""
    global _rumors_cache
    if _rumors_cache is not None:
        return _rumors_cache
    records = []
    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "id":           row.get("id", ""),
                    "title":        row.get("title", ""),
                    "url":          row.get("url", ""),
                    "publish_date": row.get("publish_date", ""),
                    "source":       row.get("source", ""),
                    "category":     row.get("category", ""),
                    "keywords":     row.get("keywords", ""),
                    "content":      row.get("content", ""),
                })
    except Exception as e:
        print("[rumors] 加载CSV失败:", e)
    _rumors_cache = records
    return records


def _load_topic_map():
    """从 topic_distribution.json 建立 url -> dominant_topic 映射"""
    global _topic_map_cache
    if _topic_map_cache is not None:
        return _topic_map_cache
    topic_map = {}
    try:
        with open(TOPIC_DIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            topic_map[item["url"]] = item.get("dominant_topic", -1)
    except Exception as e:
        print("[rumors] 加载topic_distribution失败:", e)
    _topic_map_cache = topic_map
    return topic_map


@rumors_bp.route("/list", methods=["GET"])
@login_required
def get_list():
    # >>>【谣言分页检索接口 GET /api/rumors/list 内存级分页过滤】<<<
    """
    分页+筛选查询谣言列表
    参数：
      - page: 页码（默认1）
      - size: 每页条数（默认10，最大50）
      - keyword: 关键词（搜索标题/内容）
      - topic: 主题ID（0-7）
      - start_date: 开始日期 YYYY-MM-DD
      - end_date: 结束日期 YYYY-MM-DD
    """
    page       = max(1, int(request.args.get("page", 1)))
    size       = min(50, max(1, int(request.args.get("size", 10))))
    keyword    = request.args.get("keyword", "").strip()
    topic_str  = request.args.get("topic", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date   = request.args.get("end_date", "").strip()

    all_rumors = _load_rumors()
    topic_map  = _load_topic_map()

    # >>>【内存内多条件过滤 替代SQL WHERE语句 关键词主题日期筛选】<<<
    filtered = []
    for r in all_rumors:
        # 关键词过滤
        if keyword and keyword not in r["title"] and keyword not in r["content"]:
            continue
        # 主题过滤
        if topic_str != "":
            try:
                tid = int(topic_str)
                if topic_map.get(r["url"], -1) != tid:
                    continue
            except ValueError:
                pass
        # 日期过滤
        d = r["publish_date"]
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        # 附加主题ID与清洗标签
        r_with_topic = dict(r)
        tid = topic_map.get(r["url"], -1)

        # 新抓取的文章在 topic_distribution.json 中没有记录时，
        # 用标题关键词做快速兜底推断，避免前端出现"未知主题"
        if tid == -1:
            title = r.get("title", "")
            if any(k in title for k in ["诈骗", "骗局", "银行", "账户", "验证码", "冻结", "ETC"]):
                tid = 1
            elif any(k in title for k in ["破产", "裁员", "股", "暴雷", "投资", "理财", "倒闭"]):
                tid = 2
            elif any(k in title for k in ["高铁", "航班", "地铁", "停运", "驾照", "出行"]):
                tid = 3
            elif any(k in title for k in ["地震", "暴雨", "洪水", "滑坡", "泥石流", "震级"]):
                tid = 4
            elif any(k in title for k in ["台风", "高温", "暴雪", "寒潮", "预警"]):
                tid = 5
            elif any(k in title for k in ["疫苗", "核酸", "医保", "传染", "病毒", "政策"]):
                tid = 6
            elif any(k in title for k in ["偏方", "维生素", "排毒", "中药", "养生", "致癌"]):
                tid = 7
            elif any(k in title for k in ["食品", "添加剂", "农药", "有毒", "致病"]):
                tid = 0

        r_with_topic["dominant_topic"] = tid

        
        # 实时过滤毫无意义的特征套话与人名
        raw_kws = re.split(r'[ ,;，、|]+', str(r_with_topic.get("keywords", "")))
        r_with_topic["keywords"] = ", ".join([w for w in raw_kws if w and _filter_words(w)])
        
        filtered.append(r_with_topic)

    # >>>【内存分页 Python列表切片 替代SQL LIMIT OFFSET】<<<
    # 分页
    total = len(filtered)
    start = (page - 1) * size
    end   = start + size
    page_data = filtered[start:end]

    # 返回时截断 content（列表页不需要全文）
    for item in page_data:
        item["content_brief"] = item["content"][:100] + "..." if len(item["content"]) > 100 else item["content"]
        del item["content"]

    return jsonify({
        "code": 200,
        "data": {
            "total": total,
            "page":  page,
            "size":  size,
            "pages": (total + size - 1) // size,
            "list":  page_data
        }
    })


@rumors_bp.route("/<rid>", methods=["GET"])
@login_required
def get_detail(rid):
    # >>>【谣言详情接口 GET /api/rumors/<id> 弹窗详情展示】<<<
    """获取单条谣言详情"""
    all_rumors = _load_rumors()
    topic_map  = _load_topic_map()

    for r in all_rumors:
        if r["id"] == str(rid):
            result = dict(r)
            result["dominant_topic"] = topic_map.get(r["url"], -1)
            
            raw_kws = re.split(r'[ ,;，、|]+', str(result.get("keywords", "")))
            result["keywords"] = ", ".join([w for w in raw_kws if w and _filter_words(w)])
            
            return jsonify({"code": 200, "data": result})

    return jsonify({"code": 404, "msg": "未找到该记录"}), 404
