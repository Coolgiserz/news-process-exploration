"""
使用 Ollama + LangChain 自动为已存储的新闻正文生成摘要 (abstract)。

运行前准备：
1. 启动本地 Ollama 服务并确保已拉取指定模型：
   $ ollama serve
   $ ollama run qwen3:4b   # 或自定义模型
2. 设置以下环境变量（可写入 .env）：
   PG_CONN=postgresql+psycopg3://user:pwd@host:port/db
   OLLAMA_LLM_MODEL=qwen3:4b
   TABLE_NAME=articles
   ORDER_TS_COLUMN=created_at
   TEXT_COLUMN=content
   ABSTRACT_COLUMN=abstract

执行脚本：
$ python pipeline/news_abstract_process.py
"""

from __future__ import annotations

import os
import tqdm
from datetime import datetime
import argparse
import asyncio

from dotenv import load_dotenv
from repo import SqlNewsRepository
from processors.summarizer import summarize

# 加载 .env 环境变量
load_dotenv()

# --------------------------- 可配置参数 --------------------------- #
CONNECTION_STRING = os.getenv("PG_CONN")  # 必填
assert CONNECTION_STRING, "请设置 PG_CONN 环境变量"

TABLE_NAME = os.getenv("TABLE_NAME", "articles")
ORDER_TS_COLUMN = os.getenv("ORDER_TS_COLUMN", "created_at")
TEXT_COLUMN = os.getenv("TEXT_COLUMN", "text")
ABSTRACT_COLUMN = os.getenv("ABSTRACT_COLUMN", "summary")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
MAX_ABSTRACT_CHARS = int(os.getenv("MAX_ABSTRACT_CHARS", "160"))


def process_batch_sync(texts, max_chars, summarize_func):
    abstracts = []
    keywords = []
    for content in tqdm.tqdm(texts):
        result = summarize_func(content, max_chars=max_chars)
        abstracts.append(result.summary if result else None)
        keywords.append(result.keywords if result else [])
    return abstracts, keywords

async def process_batch_async(texts, max_chars, summarize_func):
    tasks = [summarize_func(content, max_chars=max_chars) for content in texts]
    results = await asyncio.gather(*tasks)
    abstracts = [r.summary if r else None for r in results]
    keywords = [r.keywords if r else [] for r in results]
    return abstracts, keywords

def main_sync():
    repo = SqlNewsRepository(CONNECTION_STRING, table_name=TABLE_NAME, time_column=ORDER_TS_COLUMN)
    cursor_ts = datetime.min
    total = 0
    while True:
        batch = repo.fetch_without_abstract(after_ts=cursor_ts, limit=BATCH_SIZE)
        if not batch:
            print("处理完成，无更多数据。")
            break

        ids = [row[0] for row in batch]
        texts = [row[2] for row in batch]

        # 生成摘要
        abstracts, keywords = process_batch_sync(texts, MAX_ABSTRACT_CHARS, summarize)
        repo.update_abstracts(list(zip(ids, abstracts, keywords)))
        total += len(batch)
        cursor_ts = batch[-1][1]
        print(f"已生成摘要 {total} 条，最新时间戳 {cursor_ts}")


async def main_async():
    repo = SqlNewsRepository(CONNECTION_STRING, table_name=TABLE_NAME, time_column=ORDER_TS_COLUMN)
    cursor_ts = datetime.min
    total = 0
    while True:
        batch = repo.fetch_without_abstract(after_ts=cursor_ts, limit=BATCH_SIZE)
        if not batch:
            print("处理完成，无更多数据。")
            break

        ids = [row[0] for row in batch]
        texts = [row[2] for row in batch]

        # 生成摘要
        abstracts, keywords = await process_batch_async(texts, MAX_ABSTRACT_CHARS, summarize)
        repo.update_abstracts(list(zip(ids, abstracts, keywords)))
        total += len(batch)
        cursor_ts = batch[-1][1]
        print(f"已生成摘要 {total} 条，最新时间戳 {cursor_ts}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use_async", action="store_true", help="使用异步pipeline")
    args = parser.parse_args()

    if args.use_async:
        asyncio.run(main_async())
    else:
        main_sync()
