# backend/config.py
# 全局配置，定义所有 JSON 数据文件的路径、JWT 密钥和过期时间、内置用户账号
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(BASE_DIR, "data", "json")

# JSON 数据文件路径
LDA_TOPICS_FILE       = os.path.join(JSON_DIR, "lda_topics.json")
TOPIC_DIST_FILE       = os.path.join(JSON_DIR, "topic_distribution.json")
MONTHLY_TREND_FILE    = os.path.join(JSON_DIR, "monthly_trend.json")
WORDCLOUD_FILE        = os.path.join(JSON_DIR, "wordcloud_data.json")
CSV_FILE              = os.path.join(BASE_DIR, "data", "raw", "piyao_rumors.csv")

# JWT
JWT_SECRET  = "rumor_analysis_secret_2026"
JWT_EXPIRE_HOURS = 24

# 内置用户（用户名: {password, role}）
USERS = {
    "admin": {"password": "admin123", "role": "admin",   "name": "管理员"},
    "analyst": {"password": "analyst123", "role": "analyst", "name": "分析员"},
}
