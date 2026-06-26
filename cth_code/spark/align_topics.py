#!/usr/bin/env python
# spark/align_topics.py
# 主题对齐脚本：把 LDA 随机输出的主题编号，映射到预设的业务分类编号
# 同时对每个主题的 top_words 做一次清洗，去掉明显的噪声词
# 运行：python spark/align_topics.py

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LDA_FILE = os.path.join(BASE_DIR, "data", "json", "lda_topics.json")

# ========================
# 根据 lda_local.py 跑出的实际主题内容，手动对齐到预设的业务编号
# 格式：{LDA输出的原始topic_id : 目标业务topic_id}
# ========================
REMAP = {
    0: 4,   # 地震/滑坡/暴雨 → 地质自然灾害
    1: 6,   # 感染/症状/病毒 → 公共卫生与政策
    2: 1,   # 诈骗/个人信息 → 电信与账户诈骗
    3: 3,   # 医保/养老金/社保 → 社会民生与出行
    4: 5,   # 天气/气温/冷空气 → 极端气象事件
    5: 2,   # 行政处罚/专项 → 企业与经济金融
    6: 0,   # 住房/公积金/贷款 → 食品健康与安全（民生政策类）
    7: 7,   # 高考/招生/教育 → 养生偏方与疾病（剩余类）
}

_TOPIC_LABELS = {
    0: "食品健康与安全",
    1: "电信与账户诈骗",
    2: "企业与经济金融",
    3: "社会民生与出行",
    4: "地质自然灾害",
    5: "极端气象事件",
    6: "公共卫生与政策",
    7: "养生偏方与疾病",
}

# 对齐后还需要过滤掉的噪声词（停词文件之外的残余）
EXTRA_NOISE = {
    "公众", "安全", "不要", "及时", "导致", "出现",
    "部门", "提醒", "要求", "提供", "方式", "任何",
    "不良信息", "网信", "全国", "主要", "中央", "我国",
    "增长", "下降", "同比", "环比", "某某", "公安机关",
    "整治", "典型", "专项", "行政处罚", "行动", "予以",
    "网上", "恶意", "警方", "博取", "流量", "社会",
    "机关", "活动", "健康", "风险", "丹丹", "地区",
}


def main():
    with open(LDA_FILE, "r", encoding="utf-8") as f:
        raw_topics = json.load(f)

    # 建立 raw_id → topic 的字典
    topic_by_raw_id = {t["topic_id"]: t for t in raw_topics}

    aligned = []
    for raw_id, target_id in sorted(REMAP.items(), key=lambda x: x[1]):
        raw = topic_by_raw_id[raw_id]
        # 过滤噪声词
        clean_words = [
            w for w in raw["top_words"]
            if w["word"] not in EXTRA_NOISE and len(w["word"]) >= 2
        ]
        aligned.append({
            "topic_id": target_id,
            "label": _TOPIC_LABELS[target_id],
            "top_words": clean_words
        })
        print(f"  主题{target_id+1}（{_TOPIC_LABELS[target_id]}）← 原LDA主题{raw_id}: "
              f"{', '.join(w['word'] for w in clean_words[:6])}")

    # 按 topic_id 排序
    aligned.sort(key=lambda x: x["topic_id"])

    with open(LDA_FILE, "w", encoding="utf-8") as f:
        json.dump(aligned, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 主题对齐完成，已更新 {LDA_FILE}")
    print("请重启 Flask 后端以清除缓存。")


if __name__ == "__main__":
    main()
