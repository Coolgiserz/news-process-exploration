"""
批量对已有 articles 表的数据进行标题向量化回填（新增字段）。

使用方法：
$ python backfill_embeddings.py

脚本会：
1. 确保 pgvector 扩展已安装；
2. 确保 news 表存在 embedding 向量列；
3. 分批查询 embedding 为空的新闻标题，调用 OllamaEmbedding
   生成 1024 维向量后写回数据库。

运行前请先启动本地 Ollama 服务：
$ ollama serve
并保证模型 "bge-m3:567m" 已经被拉取：
$ ollama pull bge-m3:567m
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
import sys
sys.path.append(str(BASE_DIR))
load_dotenv()
from datetime import datetime
from repo import SqlNewsRepository
from langchain_ollama.embeddings import OllamaEmbeddings

# ----------------------------- 配置区域 ----------------------------- #
# PostgreSQL 连接串
CONNECTION_STRING = os.getenv("PG_CONN")

# 需要写入的向量维度
VECTOR_SIZE = 1024

# Ollama 模型与服务地址
OLLAMA_MODEL = "bge-m3:567m"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"

# 每批处理条数，根据机器内存/显卡适当调整
BATCH_SIZE = 128

TABLE_NAME = "articles"
# 用于分页排序的时间戳列名
ORDER_TS_COLUMN = "created_at"  # 若表字段名不同可自行修改
# ------------------------------------------------------------------ #

def main() -> None:
    repo = SqlNewsRepository(CONNECTION_STRING, table_name=TABLE_NAME, time_column=ORDER_TS_COLUMN)

    # 若需要可确保 embedding 列
    repo.ensure_embedding_schema(vector_size=VECTOR_SIZE)

    # 初始化 Ollama Embeddings
    embedding_model = OllamaEmbeddings(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    total_updated = 0
    last_seen_ts = datetime.min  # 时间戳游标
    while True:
        batch = repo.fetch_without_embedding(after_ts=last_seen_ts, limit=BATCH_SIZE)
        if not batch:
            print("Batch length 0, End.")
            break

        # 解包结果
        ids = [row[0] for row in batch]
        titles = [row[2] for row in batch]

        vectors = embedding_model.embed_documents(list(titles))

        # 写回
        repo.update_embeddings(list(zip(ids, vectors)))
        total_updated += len(batch)
        last_seen_ts = batch[-1][1]  # 更新游标
        print(f"已回填 {total_updated} 条新闻向量（最新时间戳 {last_seen_ts}）")

    print("全部完成！")


if __name__ == "__main__":
    main() 