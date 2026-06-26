# spark/preprocess.py
# 数据清洗与中文分词


import re
import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from pyspark.ml.feature import RegexTokenizer, StopWordsRemover


# 路径配置
BASE_DIR       = "/root/rumor_project"
INPUT_CSV      = "file:///root/rumor_project/data/piyao_rumors.csv"
OUTPUT_DIR     = "/root/rumor_project/local"   # os.makedirs 不支持 file:// 前缀
OUTPUT_PARQUET = "file:///root/rumor_project/local/cleaned"
STOPWORDS_FILE = "/root/rumor_project/spark/stopwords_zh.txt"


def load_stopwords(path):
    """从文件加载停用词列表"""
    stopwords = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    stopwords.append(w)
        print("[预处理] 停用词加载完成，共 {} 个".format(len(stopwords)))
    except Exception as e:
        print("[预处理] 加载停用词失败（将使用空列表）：{}".format(e))
    return stopwords


def main():
    spark = SparkSession.builder \
        .appName("PiyaoPreprocess") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    print("=" * 60)
    print("[预处理] Spark 启动成功")
    print("=" * 60)

    # ---- 读取 CSV ----
    print("[预处理] 读取 CSV：{}".format(INPUT_CSV))
    df = spark.read.csv(
        INPUT_CSV,
        header=True,
        inferSchema=False,
        multiLine=True,
        escape='"',
        encoding="utf-8"
    )
    print("[预处理] 原始数据行数：{}".format(df.count()))

    # ---- 数据清洗 ----
    # 1. 过滤空正文
    df = df.filter(
        F.col("content").isNotNull() & (F.length(F.col("content")) > 10)
    )
    # 2. URL 去重
    df = df.dropDuplicates(["url"])

    # 3. 日期格式统一（只保留 YYYY-MM-DD）
    df = df.withColumn(
        "publish_date",
        F.regexp_extract(F.col("publish_date"), r"(\d{4}-\d{2}-\d{2})", 1)
    ).filter(F.col("publish_date") != "")

    # 4. 清洗正文：去除辟谣平台固定套话 / URL / 日期括号
    clean_expr = F.col("content")
    noise_patterns = [
        (r"来源：?中国互联网联合辟谣平台", ""),
        (r"统筹：屈绍辉", ""),
        (r"执行：董晓",   ""),
        (r"策划：董晓",   ""),
        (r"文字：[\u4e00-\u9fff]+", ""),
        (r"设计：[\u4e00-\u9fff\s]+", ""),
        (r"责任编辑：[\u4e00-\u9fff]+", ""),
        (r"https?://\S+", ""),
        (r"（\d{4}[··]\d{2}[··]\d{2}）", ""),
    ]
    for pattern, repl in noise_patterns:
        clean_expr = F.regexp_replace(clean_expr, pattern, repl)

    df = df.withColumn("content_clean", clean_expr)

    # 5. 合并 title + content 为分析文本
    df = df.withColumn(
        "text_raw",
        F.regexp_replace(
            F.concat_ws(" ", F.col("title"), F.col("content_clean")),
            r"[^\u4e00-\u9fff]",   # 只保留汉字，其余替换成空格
            " "
        )
    )

    print("[预处理] 清洗后行数：{}".format(df.count()))

    # ---- 分词：RegexTokenizer（按非汉字分割，保留 ≥2 字的词） ----
    tokenizer = RegexTokenizer(
        inputCol="text_raw",
        outputCol="tokens_raw",
        pattern=r"\s+",          # 按空格分割（已把非汉字替换成空格）
        minTokenLength=2
    )
    df = tokenizer.transform(df)

    # ---- 去停用词 ----
    stopwords = load_stopwords(STOPWORDS_FILE)
    remover = StopWordsRemover(
        inputCol="tokens_raw",
        outputCol="tokens",
        stopWords=stopwords,
        caseSensitive=False
    )
    df = remover.transform(df)

    # 过滤词数过少（< 5）的记录
    df = df.filter(F.size(F.col("tokens")) >= 5)
    total_clean = df.count()
    print("[预处理] 分词完成，有效文章数：{}".format(total_clean))

    # ---- 抽样检查 ----
    print("\n[预处理] 抽样检查（前3条）：")
    df.select("id", "title", "publish_date", "tokens").show(3, truncate=80)

    # ---- 保存 Parquet ----
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.select(
        "id", "title", "url", "publish_date", "category", "keywords", "tokens"
    ).write.parquet(OUTPUT_PARQUET, mode="overwrite")

    print("[预处理] 完成！Parquet 保存至：{}".format(OUTPUT_PARQUET))
    print("=" * 60)
    spark.stop()


if __name__ == "__main__":
    main()
