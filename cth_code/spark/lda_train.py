# 《基于spark的网络谣言热点发现与传播分析系统开发》
# spark/lda_train.py
# >>>【LDA主题建模 Spark MLlib TF-IDF 核心算法】<<<
# 功能：使用 Apache Spark MLlib 对预处理后的谣言语料进行 TF-IDF 特征提取和 LDA 主题建模
# 输入：preprocess.py 生成的 Parquet 文件（已分词）
# 输出：lda_topics.json / topic_distribution.json / monthly_trend.json / wordcloud_data.json


import os
import json

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, ArrayType, FloatType
from pyspark.ml.feature import CountVectorizer, IDF
from pyspark.ml.clustering import LDA

# ==================== 路径与参数配置 ========0============
# >>>【路径配置 Parquet输入路径 JSON输出路径】<<<
# 项目根目录
BASE_DIR      = "/root/rumor_project"
# Parquet 文件路径（preprocess.py 的输出）
INPUT_PARQUET = "file:///root/rumor_project/local/cleaned"
# JSON 结果输出目录（用 os 模块写入）
OUTPUT_DIR    = "/root/rumor_project/local"

# >>>【LDA参数设置 超参数 主题数K=8】<<< 
NUM_TOPICS   = 8     # 主题数量 K，通过对比实验选定
MAX_ITER     = 50    # 最大迭代次数，Online 优化器下50次足够收敛
VOCAB_SIZE   = 5000  # 词表大小，超出部分按词频截断
MIN_DOC_FREQ = 2     # 词至少出现在2篇文章中才进入词表，过滤极稀有词
TOP_WORDS    = 20    # 每个主题输出20个关键词


def main():
    # 启动spark
    spark = SparkSession.builder \
        .appName("PiyaoLDA") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()

    # 将 Spark 日志级别设为 WARN，减少控制台输出
    spark.sparkContext.setLogLevel("WARN")
    print("[LDA] Spark 启动，主题数 K={}".format(NUM_TOPICS))

    # 确保输出目录存在，exist_ok=True 表示目录已存在时不报错
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    # Step 1: 读取 Parquet 文件

    print("[LDA] 读取 Parquet: {}".format(INPUT_PARQUET))
    # spark.read.parquet 以列式格式读取，比 CSV 快且保留数据类型
    df = spark.read.parquet(INPUT_PARQUET)
    print("[LDA] 共 {} 篇文章".format(df.count())) #统计文章数


    # Step 2: CountVectorizer —— 把词列表转成稀疏词频向量
    # 建立一个 5000 词的词典，把每篇文章从 ["病毒","感染","口罩"] 
    # 这样的词列表，变成 [0, 0, 1, 0, 2, ...] 这样的数字稀疏向量——词典里第几个词出现了几次。

    print("[LDA] Step1: CountVectorizer ...")
    # >>>【CountVectorizer词频向量化 文本转数字矩阵】<<<
    cv = CountVectorizer(
        inputCol="tokens",       # 输入列：分词后的词列表（List[String]）
        outputCol="raw_features", # 输出列：稀疏词频向量（SparseVector）
        vocabSize=VOCAB_SIZE,    # 词表数量
        minDF=MIN_DOC_FREQ       # 词至少出现在2篇文档中才纳入词表
    )
    # 扫描所有文章，统计词频，建立词典
    cv_model = cv.fit(df)
    # 获取词表
    vocabulary = cv_model.vocabulary
    print("[LDA] 词表大小：{}".format(len(vocabulary)))
    # 把每篇文章的词列表转换成稀疏词频向量
    df_cv = cv_model.transform(df)


    # Step 3: IDF —— 逆文档频率加权，降低高频套话的影响

    print("[LDA] Step2: IDF ...")
    # >>>【TF-IDF加权 权重计算 降低高频套话影响】<<<
    # IDF 计算公式：IDF(t) = log((N+1)/(df(t)+1))，N为文档总数，df(t)为含词 t 的文档数
    # 词在越多文档中出现，IDF值越低，权重越小
    # 创建IDF模型
    idf = IDF(inputCol="raw_features", outputCol="features")
    # fit：计算每个词的 IDF 值，重要程度
    idf_model = idf.fit(df_cv)
    # transform：转换 TF × IDF，得到 TF-IDF 加权向量
    df_tfidf = idf_model.transform(df_cv)


    # Step 4: LDA 训练 —— 发现隐藏的主题结构

    print("[LDA] Step3: 训练 LDA (K={}, maxIter={}) ...".format(NUM_TOPICS, MAX_ITER))
    # >>>【LDA主题模型训练 无监督聊类 Online变分贝叶斯】<<<
    lda = LDA(
        k=NUM_TOPICS,                      # 主题数量，决定模型输出几个主题
        maxIter=MAX_ITER,                  # 最大迭代次数
        optimizer="online",                # Online 变分贝叶斯优化，分批流式学习，收敛速度极快
        featuresCol="features",            # 输入特征列（TF-IDF 向量）
        topicDistributionCol="topic_dist"  # 输出列：每篇文章在8个主题上的概率分布
    )
    # fit 是最耗时的步骤，在全量 TF-IDF 矩阵上迭代优化 LDA 参数
    lda_model = lda.fit(df_tfidf)
    # >>>【困惑度Perplexity 模型评估指标准确率】<<<
    # logPerplexity：对数困惑度，衡量模型对语料的拟合程度，值越小越好
    lp = lda_model.logPerplexity(df_tfidf)
    print("[LDA] 训练完成，LogPerplexity={:.4f}".format(lp))


    # Step 5: 提取主题关键词 → 保存 lda_topics.json

    print("[LDA] Step4: 提取主题关键词 ...")
    # >>>【提取主题关键词 describeTopics 词表索引转汉字】<<<
    # describeTopics 返回每个主题 Top N 词的索引和权重
    topics_rows = lda_model.describeTopics(maxTermsPerTopic=TOP_WORDS).collect()

    lda_topics = []
    for row in topics_rows:
        tid = int(row["topic"])  # 主题编号，从0开始
        # termIndices：词在词表中的索引列表；termWeights：对应权重列表
        # zip 把两个列表配对，vocabulary[i] 把索引转换回汉字词
        words = [
            {"word": vocabulary[int(i)], "weight": round(float(w), 6)}
            for i, w in zip(row["termIndices"], row["termWeights"])
        ]
        lda_topics.append({
            "topic_id": tid,
            "label": "主题{}".format(tid + 1),  # 可读标签（后端会替换为业务名称）
            "top_words": words
        })
        print("  主题{}: {}".format(tid + 1, ", ".join(x["word"] for x in words[:6])))

    out_topics = os.path.join(OUTPUT_DIR, "lda_topics.json")
    with open(out_topics, "w", encoding="utf-8") as f:
        # ensure_ascii=False：中文直接写入，不转义为 \uXXXX
        # indent=2：格式化输出，便于人工阅读和调试
        json.dump(lda_topics, f, ensure_ascii=False, indent=2)
    print("[LDA] lda_topics.json 已保存")


    # Step 6: 计算每篇文章的主题归属 → 保存 topic_distribution.json

    print("[LDA] Step5: 计算文章主题归属 ...")
    # >>>【文章主题分布推断 argmax取概率最大主题】<<<
    # transform：对每篇文章输出 topic_dist 列（8维概率向量）
    df_pred = lda_model.transform(df_tfidf)

    # argmax_fn：从概率向量中取概率最大的主题编号
    def argmax_fn(v):
        if v is None:
            return -1                    # 异常情况返回 -1
        return int(v.toArray().argmax()) # toArray() 把 SparseVector 转为 numpy 数组

    # probs_fn：把概率向量转为普通 Python 列表，保留4位小数
    def probs_fn(v):
        if v is None:
            return []
        return [round(float(x), 4) for x in v.toArray()]

    # F.udf 把 Python 函数注册为 Spark UDF（用户自定义函数），可在 DataFrame 列上并行执行
    argmax_udf = F.udf(argmax_fn, IntegerType())       # 返回值类型：整数
    probs_udf  = F.udf(probs_fn,  ArrayType(FloatType()))  # 返回值类型：浮点数列表

    # withColumn：在 DataFrame 上新增一列，不修改原列
    df_pred = df_pred.withColumn("dominant_topic", argmax_udf(F.col("topic_dist")))
    df_pred = df_pred.withColumn("topic_probs",    probs_udf(F.col("topic_dist")))

    # collect()：把分布式 DataFrame 的数据收集到 Driver 节点内存（返回 Python list）
    rows = df_pred.select(
        "id", "title", "url", "publish_date", "category",
        "dominant_topic", "topic_probs"
    ).collect()

    # 构建 JSON 序列化格式，str/int/list 强制类型转换防止序列化失败
    topic_dist = [
        {
            "id":             str(r["id"]),
            "title":          str(r["title"]),
            "url":            str(r["url"]),
            "publish_date":   str(r["publish_date"]),
            "category":       str(r["category"]),
            "dominant_topic": int(r["dominant_topic"]),  # 主导主题编号（0~7）
            "topic_probs":    list(r["topic_probs"])     # 8个主题的概率分布
        }
        for r in rows
    ]
    out_dist = os.path.join(OUTPUT_DIR, "topic_distribution.json")
    with open(out_dist, "w", encoding="utf-8") as f:
        json.dump(topic_dist, f, ensure_ascii=False, indent=2)
    print("[LDA] topic_distribution.json 已保存（{} 条）".format(len(topic_dist)))


    # Step 7: 月度趋势统计 → 保存 monthly_trend.json

    print("[LDA] Step6: 月度趋势统计 ...")
    # >>>【月度趋势统计 groupBy分组计数 写入monthly_trend.json】<<<
    # F.substring 截取日期字符串的前7位，如 "2024-03-15" → "2024-03"
    df_month = df_pred.withColumn("month", F.substring("publish_date", 1, 7))
    # groupBy + count：统计每个（月份, 主题）组合的文章数
    # orderBy 保证结果按时间顺序排列
    monthly_rows = df_month.groupBy("month", "dominant_topic") \
        .count().orderBy("month", "dominant_topic").collect()

    monthly_trend = {}
    for r in monthly_rows:
        mo = str(r["month"])                    # 月份字符串，如 "2024-03"
        tp = str(int(r["dominant_topic"]))       # 主题编号转字符串，作为 JSON key
        ct = int(r["count"])                     # 该月该主题的文章数量
        # setdefault：如果 mo 不存在则初始化为空字典，再设置 tp: ct
        monthly_trend.setdefault(mo, {})[tp] = ct

    out_monthly = os.path.join(OUTPUT_DIR, "monthly_trend.json")
    with open(out_monthly, "w", encoding="utf-8") as f:
        json.dump(monthly_trend, f, ensure_ascii=False, indent=2)
    print("[LDA] monthly_trend.json 已保存（{} 个月份）".format(len(monthly_trend)))


    # Step 8: 词云数据（全局词频 Top100，过滤停词）→ 保存 wordcloud_data.json

    print("[LDA] Step7: 词云数据 ...")
    # F.explode：把每篇文章的词列表"炸开"成一行一词
    # groupBy("word").count()：统计每个词在全部文章中出现的总次数
    # orderBy(desc).limit(150)：取频率最高的150个词，后续过滤后剩约100个
    wc_rows = df.select(F.explode(F.col("tokens")).alias("word")) \
        .groupBy("word").count() \
        .orderBy(F.col("count").desc()) \
        .limit(150).collect()

    # 停词集合：过滤掉平台署名、人名、行政套话等无内容价值的高频词
    _wc_stopwords = {
        "今日辟谣", "中国互联网联合辟谣平台", "科学辟谣平台", "科普中国", "网信中国",
        "重庆辟谣", "上海网络辟谣", "北京网络举报", "公安部网安局", "健康中国",
        "央视新闻", "人民日报", "新华社", "闫丹丹", "荆克", "贾玉韬", "霍晶莹",
        "周文婧", "芮静", "董晋", "李洪雷", "李亚琼", "吴炎",
        "中央", "联合", "辟谣", "平台", "网信办", "举报", "案例",
        "案例一", "案例二", "案例三", "案例四", "案例五",
        "通报", "依法", "发布", "目前", "相关", "进行", "需要", "已经",
        "其中", "同时", "此外", "然而", "所谓", "那么", "主要",
        "同比增长", "环比增长", "同比下降", "环比下降", "万件",
        "造成不良社会影响", "造成不良影响", "造成恶劣社会影响",
        "扰乱公共秩序", "扰乱社会公共秩序", "严重扰乱公共秩序",
        "网络谣言案", "谣言案", "经公安机关调查",
        "月全国受理网络违法和不良信息举报",
        "中央网信办举报中心指导全国各级网信举报工作部门",
        "全国主要网站平台受理举报",
        "引发网民关注", "引发关注", "引发社会关注",
        "谨防上当受骗", "现将部分典型案例通报如下",
        "专项行动", "清朗", "清朗行动",
        "自媒体", "抖音账号", "快手账号", "微博账号", "网络账号",
        "吸粉引流", "吸引流量", "博取关注",
        "涉及的账号已被依法依约关闭", "相关账号已被依法依约处置",
        "公安机关已依法对其处以行政处罚",
    }
    # 列表推导式：过滤停词、单字、纯数字，取前100条
    wordcloud = [
        {"word": r["word"], "count": int(r["count"])}
        for r in wc_rows
        if len(r["word"]) >= 2          # 过滤单字
        and not r["word"].isdigit()     # 过滤纯数字
        and r["word"] not in _wc_stopwords  # 过滤停词
    ][:100]

    out_wc = os.path.join(OUTPUT_DIR, "wordcloud_data.json")
    with open(out_wc, "w", encoding="utf-8") as f:
        json.dump(wordcloud, f, ensure_ascii=False, indent=2)
    print("[LDA] wordcloud_data.json 已保存")

    # 打印各主题的文章数分布，用于快速验证主题均衡性
    print("\n[LDA] 各主题文章数：")
    for r in df_pred.groupBy("dominant_topic").count() \
            .orderBy("dominant_topic").collect():
        print("  主题{}: {} 篇".format(int(r["dominant_topic"]) + 1, r["count"]))

    print("=" * 60)
    print("[LDA] 全部完成！结果保存在：{}".format(OUTPUT_DIR))
    print("  lda_topics.json / topic_distribution.json")
    print("  monthly_trend.json / wordcloud_data.json")
    print("=" * 60)
    # 释放 Spark 资源，关闭 JVM
    spark.stop()


if __name__ == "__main__":
    main()
