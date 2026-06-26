#!/bin/bash
# spark/run_pipeline.sh


set -e  # 任何命令失败则退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=================================================="
echo " 谣言分析系统 - Spark 数据处理流水线"
echo " 工作目录: $SCRIPT_DIR"
echo "=================================================="

# 确保结果目录存在
mkdir -p "$SCRIPT_DIR/../data/processed"
mkdir -p "$SCRIPT_DIR/../data/results"

# Step 1: 数据预处理
echo ""
echo "[Step 1] 运行数据预处理 (preprocess.py)..."
spark-submit \
  --master local[*] \
  --driver-memory 2g \
  --executor-memory 2g \
  "$SCRIPT_DIR/preprocess.py"

echo "[Step 1] ✅ 预处理完成"

# Step 2: LDA 建模
echo ""
echo "[Step 2] 运行 LDA 建模 (lda_train.py)..."
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  "$SCRIPT_DIR/lda_train.py"

echo "[Step 2] ✅ LDA 建模完成"

echo ""
echo "=================================================="
echo " ✅ 全部完成！结果 JSON 文件位于："
echo "    $SCRIPT_DIR/../data/results/"
echo "=================================================="
