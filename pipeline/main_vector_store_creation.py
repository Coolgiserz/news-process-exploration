"""
新闻标题向量化 ETL 脚本

功能：
- 支持主库与向量库分库，自动创建向量表（如未存在）
- 批量查询主库中未同步（title_vector_synced IS NOT TRUE）的新闻
- 对新闻标题进行向量化，写入向量库（articles_vector）
- 向量化成功后，回写主库同步状态（title_vector_synced, title_vector_synced_at）
- 支持元数据补全与后续扩展

使用方法：
$ python pipeline/main_vector_store_creation.py

运行前请确保：
- 已安装 pgvector 扩展
- 已启动本地 Ollama 服务：$ ollama serve
- 已拉取模型：$ ollama pull bge-m3:567m
- .env 文件中配置了 PG_CONN（主库连接串）、PG_VECTOR_CONN（向量库连接串）

主要流程：
1. 初始化向量表（如已存在则跳过）
2. 查询主库中未同步的新闻
3. 向量化标题，写入向量库
4. 回写主库同步状态

如需扩展正文/摘要向量化、切片等，可在本脚本基础上修改。
"""

from __future__ import annotations

import os
from typing import List
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm
import sqlalchemy
from datetime import datetime
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_postgres import PGEngine, PGVectorStore
from langchain_core.documents import Document
from sqlalchemy import text

load_dotenv()
CONNECTION_STRING = os.getenv("PG_CONN")
VECTOR_CONNECTION_STRING = os.getenv("PG_VECTOR_CONN")
vector_engine = PGEngine.from_connection_string(url=VECTOR_CONNECTION_STRING)
sql_engine = sqlalchemy.create_engine(CONNECTION_STRING)

VECTOR_SIZE = 1024
VECTOR_TABLE = "articles_vector"
SOURCE_TABLE = "articles"
ID_COLUMN = "id"
METADATA_JSON_COLUMN = "metadata"


def init_vector_table() -> None:
    vector_engine.init_vectorstore_table(
        table_name=VECTOR_TABLE,
        vector_size=VECTOR_SIZE,
        metadata_json_column=METADATA_JSON_COLUMN,
        id_column=ID_COLUMN,
        # overwrite_existing=True,
        metadata_columns=[
            "title", "url", "text", "summary", "publish_date",
            "fingerprint", "source_name", "keywords"
        ],
    )
    print(f"向量表 {VECTOR_TABLE} 创建完成（如已存在则跳过）")


def fetch_unsynced_articles() -> pd.DataFrame:
    query = f"""
    SELECT a.fingerprint, a.title, a.text, a.summary, a.url, a.publish_date, a.source_name, a.keywords
    FROM {SOURCE_TABLE} a
    WHERE a.title_vector_synced IS NOT TRUE
    """
    df = pd.read_sql(query, sql_engine)
    print(f"本次需向量化新闻数：{len(df)}")
    return df


def build_documents(df: pd.DataFrame) -> List[Document]:
    docs: List[Document] = []
    for _, row in tqdm(df.iterrows(), total=len(df)):
        row["publish_date"] = row["publish_date"].strftime("%Y-%m-%d %H:%M:%S") if row["publish_date"] else None
        doc = Document(
            page_content=row["title"] or "",
            metadata={
                "fingerprint": row["fingerprint"],
                "title": row["title"],
                "text": row["text"],
                "summary": row["summary"],
                "url": row["url"],
                "publish_date": row["publish_date"],
                "source_name": row.get("source_name"),
                "keywords": row.get("keywords")
            }
        )
        docs.append(doc)
    return docs


def write_documents_to_vectorstore(docs: List[Document]) -> None:
    embedding = OllamaEmbeddings(model="bge-m3:567m", base_url="http://127.0.0.1:11434")
    store = PGVectorStore.create_sync(
        engine=vector_engine,
        table_name=VECTOR_TABLE,
        metadata_json_column=METADATA_JSON_COLUMN,
        id_column=ID_COLUMN,
        embedding_service=embedding,
    )
    print(f"开始写入向量表...{VECTOR_TABLE}")
    store.add_documents(docs)
    print(f"已写入向量表：{len(docs)} 条新闻")


def mark_articles_synced(df: pd.DataFrame) -> None:
    fingerprints = [row["fingerprint"] for _, row in df.iterrows()]
    now = datetime.now()
    update_sql = f"""
    UPDATE {SOURCE_TABLE}
    SET title_vector_synced = TRUE, title_vector_synced_at = :title_vector_synced_at
    WHERE fingerprint = ANY(:fingerprints)
    """
    with sql_engine.begin() as conn:
        conn.execute(text(update_sql), parameters={
            "title_vector_synced_at": now,
            "fingerprints": fingerprints
        })
    print(f"已回写同步状态 {len(fingerprints)} 条新闻")


def main() -> None:
    init_vector_table()
    df = fetch_unsynced_articles()
    if not df.empty:
        docs = build_documents(df)
        write_documents_to_vectorstore(docs)
        mark_articles_synced(df)
    else:
        print("无新增新闻需要向量化。")

if __name__ == "__main__":
    main()