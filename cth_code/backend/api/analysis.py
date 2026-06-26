# backend/api/analysis.py
# >>>【分析数据 API 图表数据接口】<<<
# 功能：主题关键词、词云、月度趋势、主题分布、系统统计概览、生成分析报告

import json
import os
import re
import csv
import math
from flask import jsonify
from api import analysis_bp
from auth import login_required
from config import LDA_TOPICS_FILE, MONTHLY_TREND_FILE, TOPIC_DIST_FILE, CSV_FILE


def _load(filepath):
    """加载 JSON 文件，带缓存（进程内单次加载）"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---- 启动时预加载，避免每次请求都读文件 ----
# >>>【进程内内存缓存 单次加载防止重复读文件】<<<
_cache = {}

def _get(key, filepath):
    # >>>【内存缓存获取 首次读文件后常驻内存】<<<
    if key not in _cache:
        _cache[key] = _load(filepath)
    return _cache[key]


# =====================================================================
# 停词加载：从独立文件读取，保持代码整洁
# stopwords_domain.txt 包含平台名、人名、套话等噪声词
# =====================================================================
def _load_domain_stopwords() -> set:
    # >>>【领域停用词加载 干静词过滤】<<<
    """从 data/stopwords_domain.txt 加载领域停词表"""
    sw_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "stopwords_domain.txt"
    )
    stopwords = set()
    try:
        with open(sw_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w and not w.startswith("#"):
                    stopwords.add(w)
        print(f"[analysis] 领域停词加载完成，共 {len(stopwords)} 个")
    except FileNotFoundError:
        print(f"[analysis] 警告：停词文件不存在 {sw_path}")
    return stopwords

_DOMAIN_STOPWORDS = _load_domain_stopwords()


def _filter_words(word: str) -> bool:
    """返回 True 表示保留该词"""
    if not word or len(word) <= 1:
        return False
    if word.isdigit():
        return False
    if word in _DOMAIN_STOPWORDS:
        return False
    return True


def _filter_topic_words(topics: list) -> list:
    """对每个主题的 top_words 执行停词过滤；主题名称直接使用 JSON 中的 label 字段"""
    filtered = []
    for topic in topics:
        tid = topic["topic_id"]
        new_top_words = [
            w for w in topic.get("top_words", [])
            if _filter_words(w.get("word", ""))
        ]
        topic_copy = {**topic, "top_words": new_top_words}
        # 直接沿用 JSON 中由 LDA 训练脚本自动生成的 label，不做硬编码覆盖
        filtered.append(topic_copy)
    return filtered


@analysis_bp.route("/topics", methods=["GET"])
@login_required
def get_topics():
    """返回 LDA 主题关键词列表（过滤停词后）"""
    data = _get("topics", LDA_TOPICS_FILE)
    return jsonify({"code": 200, "data": _filter_topic_words(data)})


@analysis_bp.route("/wordcloud", methods=["GET"])
@login_required
def get_wordcloud():
    # >>>【词云数据接口 GET /api/analysis/wordcloud ECharts词云图】<<<
    """词云数据：LDA 主题词权重 + CSV 关键词字段频次叠加，过滤停词"""
    # LDA 模型训练出的主题词权重
    topics_data = _get("topics", LDA_TOPICS_FILE)

    word_weights = {}
    for topic in topics_data:
        for tw in topic.get("top_words", []):
            w = tw["word"]
            weight = tw["weight"] * 100000
            word_weights[w] = word_weights.get(w, 0) + weight

    # CSV 原始数据里的 keywords 字段真实频次
    try:
        kw_freq = {}
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kws = row.get("keywords", "")
                if kws:
                    seen = set()
                    for w in re.split(r'[ ,;，、|]+', kws):
                        w = w.strip()
                        if w and w not in seen and _filter_words(w):
                            kw_freq[w] = kw_freq.get(w, 0) + 1
                            seen.add(w)
        if kw_freq:
            max_freq = max(kw_freq.values())
            for w, freq in kw_freq.items():
                scaled = int(150 + 850 * math.log(1 + freq) / math.log(1 + max_freq))
                word_weights[w] = word_weights.get(w, 0) + scaled
    except Exception as e:
        print("[wordcloud] 加载CSV提取关键字失败:", e)

    filtered_words = [
        {"word": w, "count": int(cnt)}
        for w, cnt in word_weights.items()
        if _filter_words(w) # 过滤停用词
    ]
    filtered_words.sort(key=lambda x: x["count"], reverse=True) # 按照热度降序
    return jsonify({"code": 200, "data": filtered_words})


@analysis_bp.route("/monthly-trend", methods=["GET"])
@login_required
def get_monthly_trend():
    # >>>【月度趋势接口 GET /api/analysis/monthly-trend ECharts折线图堆叠柱状图】<<<
    """返回月度趋势数据（ECharts 格式）"""
    raw = _get("monthly_trend", MONTHLY_TREND_FILE)
    topics_data = _filter_topic_words(_get("topics", LDA_TOPICS_FILE))

    months = sorted(raw.keys())
    series = []
    for tid in range(len(topics_data)):
        label = topics_data[tid]["label"] if tid < len(topics_data) else f"主题{tid+1}"
        data = [raw.get(m, {}).get(str(tid), 0) for m in months]
        series.append({"name": label, "data": data})

    return jsonify({"code": 200, "data": {"months": months, "series": series}})


@analysis_bp.route("/topic-distribution", methods=["GET"])
@login_required
def get_topic_distribution():
    # >>>【主题分布接口 GET /api/analysis/topic-distribution ECharts饰图片图】<<<
    """返回各主题文章数量（饰图数据）"""
    raw = _get("topic_dist", TOPIC_DIST_FILE)
    topics_data = _filter_topic_words(_get("topics", LDA_TOPICS_FILE))

    count_map = {}
    for article in raw:
        tid = article.get("dominant_topic", -1)
        if tid >= 0:
            count_map[tid] = count_map.get(tid, 0) + 1

    result = []
    for tid, cnt in sorted(count_map.items()):
        label = topics_data[tid]["label"] if tid < len(topics_data) else f"主题{tid+1}"
        filtered_top_words = [w["word"] for w in topics_data[tid].get("top_words", [])] if tid < len(topics_data) else []
        result.append({"name": label, "value": cnt, "top_words": filtered_top_words[:3]})

    return jsonify({"code": 200, "data": result})


@analysis_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    # >>>【系统统计概览接口 GET /api/analysis/stats 仪表盘卡片数据】<<<
    """返回系统总体统计信息"""
    raw = _get("topic_dist", TOPIC_DIST_FILE)
    monthly = _get("monthly_trend", MONTHLY_TREND_FILE)

    total = len(raw)
    months = sorted(monthly.keys())
    date_range = {"start": months[0] if months else "", "end": months[-1] if months else ""}

    count_map = {}
    for a in raw:
        tid = a.get("dominant_topic", -1)
        if tid >= 0:
            count_map[tid] = count_map.get(tid, 0) + 1

    return jsonify({
        "code": 200,
        "data": {
            "total_articles": total,
            "total_months":   len(months),
            "date_range":     date_range,
            "topic_counts":   count_map,
            "num_topics":     8
        }
    })


@analysis_bp.route("/report", methods=["GET"])
@login_required
def generate_report():
    # >>>【生成分析报告 GET /api/analysis/report HTML报告下载】<<<
    # >>>【Python动态HTML模板 f-string模板字符串 Content-Disposition下载】<<<
    """生成并下载 HTML 格式的谣言分析报告（分析员/管理员均可使用）"""
    from datetime import datetime
    from flask import make_response

    raw        = _get("topic_dist",    TOPIC_DIST_FILE)
    monthly    = _get("monthly_trend", MONTHLY_TREND_FILE)
    topics_raw = _filter_topic_words(_get("topics", LDA_TOPICS_FILE))

    total  = len(raw)
    months = sorted(monthly.keys())
    date_start = months[0]  if months else "—"
    date_end   = months[-1] if months else "—"

    # 主题文章数统计
    count_map = {}
    for a in raw:
        tid = a.get("dominant_topic", -1)
        if tid >= 0:
            count_map[tid] = count_map.get(tid, 0) + 1

    # 月度高峰计算
    month_totals = {m: sum(v.values()) for m, v in monthly.items()}
    peak_month = max(month_totals, key=month_totals.get) if month_totals else "—"
    peak_count = month_totals.get(peak_month, 0)

    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # ===== 构建主题分布表格行 =====
    topic_rows = ""
    for t in topics_raw:
        tid   = t["topic_id"]
        label = t["label"]
        cnt   = count_map.get(tid, 0)
        pct   = f"{cnt / total * 100:.1f}%" if total > 0 else "0%"
        kws   = "、".join(w["word"] for w in t["top_words"][:5])
        topic_rows += f"""
        <tr>
          <td>{tid + 1}</td>
          <td><strong>{label}</strong></td>
          <td>{cnt}</td>
          <td>{pct}</td>
          <td style="color:#555;font-size:13px">{kws}</td>
        </tr>"""

    # ===== 构建月度趋势摘要 =====
    trend_rows = ""
    for m in months[-12:]:   # 仅展示最近12个月
        total_m = sum(monthly[m].values())
        trend_rows += f"<tr><td>{m}</td><td>{total_m}</td></tr>"

    # ===== HTML 报告模板 =====
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>网络谣言分析报告</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; background: #f5f7fa; color: #333; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 40px 50px; background: #fff; }}
  h1 {{ font-size: 26px; text-align: center; color: #1a1a2e; padding-bottom: 10px;
       border-bottom: 3px solid #2563eb; margin-bottom: 6px; }}
  .subtitle {{ text-align: center; color: #888; font-size: 13px; margin-bottom: 30px; }}
  h2 {{ font-size: 17px; color: #2563eb; border-left: 4px solid #2563eb;
       padding-left: 10px; margin: 28px 0 14px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 10px; }}
  .kpi {{ background: #eff6ff; border-radius: 8px; padding: 18px 12px; text-align: center; }}
  .kpi .val {{ font-size: 28px; font-weight: 700; color: #2563eb; }}
  .kpi .lbl {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ background: #2563eb; color: #fff; padding: 9px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }}
  tr:nth-child(even) td {{ background: #f9fafb; }}
  .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #aaa;
             border-top: 1px solid #e5e7eb; padding-top: 16px; }}
  .highlight {{ background: #fef3c7; padding: 12px 16px; border-radius: 6px;
                border-left: 4px solid #f59e0b; margin-bottom: 14px; font-size: 14px; line-height: 1.8; }}
  @media print {{ body {{ background: #fff; }} .page {{ padding: 20px; }} }}
</style>
</head>
<body>
<div class="page">
  <h1>网络谣言热点发现与传播分析报告</h1>
  <p class="subtitle">生成时间：{now_str} &nbsp;|&nbsp; 数据来源：中国互联网联合辟谣平台</p>

  <h2>一、数据总览</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="val">{total}</div><div class="lbl">谣言文章总数（篇）</div></div>
    <div class="kpi"><div class="val">{len(months)}</div><div class="lbl">数据覆盖月数</div></div>
    <div class="kpi"><div class="val">{len(topics_raw)}</div><div class="lbl">LDA 挖掘主题数</div></div>
    <div class="kpi"><div class="val">{peak_count}</div><div class="lbl">单月最高篇数</div></div>
  </div>
  <div class="highlight">
    📅 数据时间范围：<strong>{date_start}</strong> 至 <strong>{date_end}</strong>，
    共跨越 <strong>{len(months)}</strong> 个月。<br>
    🔥 谣言传播高峰月份：<strong>{peak_month}</strong>，当月共记录 <strong>{peak_count}</strong> 篇辟谣文章。
  </div>

  <h2>二、主题分布分析</h2>
  <p style="font-size:13px;color:#888;margin-bottom:10px">
    系统采用 LDA（隐含狄利克雷分布）主题模型对全量谣言语料进行无监督聚类，共挖掘出 {len(topics_raw)} 个主题。
  </p>
  <table>
    <thead><tr><th>#</th><th>主题名称</th><th>文章数</th><th>占比</th><th>核心关键词（前5个）</th></tr></thead>
    <tbody>{topic_rows}</tbody>
  </table>

  <h2>三、近期月度趋势（最近12个月）</h2>
  <table>
    <thead><tr><th>月份</th><th>谣言文章总数</th></tr></thead>
    <tbody>{trend_rows}</tbody>
  </table>

  <h2>四、结论与建议</h2>
  <div class="highlight">
    根据 LDA 模型分析结果，当前网络谣言呈现多主题并发特征。
    建议监管部门重点关注文章量最多的主题领域，针对高峰月份加强舆情预警机制建设，
    同时建立谣言关键词监测词表，实现早发现、早处置。
  </div>

  <div class="footer">
    本报告由「网络谣言热点发现与传播分析系统」自动生成 &nbsp;·&nbsp; 崔天豪 毕业设计
  </div>
</div>
</body>
</html>"""

    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = \
        f'attachment; filename="rumor_report_{datetime.now().strftime("%Y%m%d_%H%M")}.html"'
    return response
