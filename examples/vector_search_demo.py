"""
示例：向量数据库检索效果测试

本脚本用于测试 pipeline/main_vector_store_creation.py 构建的向量数据库（articles_vector），
可输入查询语句，返回最相关的新闻内容及元数据。

用法：
$ python examples/vector_search_demo.py
"""

import os
from dotenv import load_dotenv
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_postgres import PGEngine, PGVectorStore

load_dotenv()
VECTOR_CONNECTION_STRING = os.getenv("PG_VECTOR_CONN")
VECTOR_TABLE = "articles_vector"
METADATA_JSON_COLUMN = "metadata"
ID_COLUMN = "id"

vector_engine = PGEngine.from_connection_string(url=VECTOR_CONNECTION_STRING)
embedding = OllamaEmbeddings(model="bge-m3:567m", base_url="http://127.0.0.1:11434")

store = PGVectorStore.create_sync(
    engine=vector_engine,
    table_name=VECTOR_TABLE,
    metadata_json_column=METADATA_JSON_COLUMN,
    id_column=ID_COLUMN,
    embedding_service=embedding,
)

def search_and_print(query: str, k: int = 5):
    print(f"\n查询: {query}")
    results = store.similarity_search(query, k=k)
    if not results:
        print("未检索到相关内容。")
        return
    for i, doc in enumerate(results, 1):
        print(f"--- Top {i} ---")
        print("内容:", doc.page_content)
        print("元数据:", doc.metadata)
        print()

def main():
    print("向量数据库检索测试。输入查询内容，回车检索，输入 exit 退出。\n")
    while True:
        query = input("请输入检索内容：").strip()
        if not query or query.lower() == "exit":
            break
        search_and_print(query)

if __name__ == "__main__":
    main() 