import pymysql
import json
import csv
import os
import re

# Database config
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "123456"
DB_NAME = "rumor_analysis"

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "../data/raw/piyao_rumors.csv")
TOPIC_DIST_FILE = os.path.join(BASE_DIR, "../data/json/topic_distribution.json")
LDA_TOPICS_FILE = os.path.join(BASE_DIR, "../data/json/lda_topics.json")

def create_db_and_table():
    print("正在连接 MySQL 并初始化数据库...")
    # Connect to MySQL server
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        charset='utf8mb4'
    )
    try:
        with connection.cursor() as cursor:
            # Create Database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute(f"USE {DB_NAME};")
            
            # Create Table
            cursor.execute("DROP TABLE IF EXISTS `clean_rumors`;")
            create_table_sql = """
            CREATE TABLE `clean_rumors` (
                `id` INT NOT NULL PRIMARY KEY COMMENT '文章ID',
                `title` varchar(255) NOT NULL COMMENT '文章标题',
                `url` varchar(255) NOT NULL COMMENT '原文链接',
                `publish_date` date DEFAULT NULL COMMENT '发布日期',
                `category` varchar(50) DEFAULT NULL COMMENT '分类',
                `dominant_topic` int DEFAULT NULL COMMENT 'LDA主导主题编号',
                `topic_label` varchar(50) DEFAULT NULL COMMENT '主题语义名称',
                `keywords` varchar(255) DEFAULT NULL COMMENT '关键词',
                `content_brief` text COMMENT '文章正文'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='清洗后的谣言特征库';
            """
            cursor.execute(create_table_sql)
        connection.commit()
        print(f"数据库 {DB_NAME} 和表 clean_rumors 准备完毕！")
    finally:
        connection.close()

def sync_data():
    print("正在读取本地清洗后的分析文件...")
    
    # 1. 读取主题名称映射
    topic_labels = {}
    try:
        with open(LDA_TOPICS_FILE, "r", encoding="utf-8") as f:
            topics = json.load(f)
            _TOPIC_LABELS = {
                0: "食品健康与安全", 1: "电信与账户诈骗", 2: "企业与经济金融",
                3: "社会民生与出行", 4: "地质自然灾害", 5: "极端气象事件",
                6: "公共卫生与政策", 7: "养生偏方与疾病"
            }
            for t in topics:
                tid = t["topic_id"]
                topic_labels[tid] = _TOPIC_LABELS.get(tid, f"主题{tid+1}")
    except Exception as e:
        print("读取 lda_topics.json 失败:", e)

    # 2. 读取 Spark 算出来的干净数据映射 (url -> topic)
    topic_map = {}
    try:
        with open(TOPIC_DIST_FILE, "r", encoding="utf-8") as f:
            dist_data = json.load(f)
            for item in dist_data:
                topic_map[item["url"]] = item.get("dominant_topic", -1)
    except Exception as e:
        print("读取 topic_distribution.json 失败:", e)
        
    # 3. 读取 CSV，合并数据写入数据库
    records_to_insert = []
    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url", "")
                tid = topic_map.get(url, -1)
                
                # 简单的日期格式校验
                pub_date = row.get("publish_date", "")
                if not re.match(r'\d{4}-\d{2}-\d{2}', pub_date):
                    pub_date = None
                    
                records_to_insert.append((
                    int(row.get("id", "0")) if row.get("id", "0").isdigit() else 0,
                    row.get("title", ""),
                    url,
                    pub_date,
                    row.get("category", ""),
                    tid,
                    topic_labels.get(tid, "未知主题"),
                    row.get("keywords", ""),
                    row.get("content", "")
                ))
    except Exception as e:
        print("读取 CSV 失败:", e)
        return
            
    print(f"准备插入 {len(records_to_insert)} 条干净数据到 MySQL...")
    
    # 连接数据库并批量插入
    connection = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME, charset='utf8mb4'
    )
    try:
        with connection.cursor() as cursor:
            insert_sql = """
            INSERT INTO `clean_rumors` 
            (id, title, url, publish_date, category, dominant_topic, topic_label, keywords, content_brief)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title=VALUES(title), dominant_topic=VALUES(dominant_topic), topic_label=VALUES(topic_label);
            """
            cursor.executemany(insert_sql, records_to_insert)
        connection.commit()
        print("数据同步成功！")
    except Exception as e:
        print("数据插入失败，请检查密码是否正确:", e)
    finally:
        connection.close()

if __name__ == "__main__":
    try:
        create_db_and_table()
        sync_data()
    except pymysql.err.OperationalError as e:
        if "Access denied" in str(e):
            print("\n 密码错误！")
        else:
            print("\n 数据库连接失败:", e)
