import os
# https://stackoverflow.com/questions/28521535/requests-how-to-disable-bypass-proxy
os.environ["NO_PROXY"]="localhost"
from dotenv import load_dotenv
load_dotenv()
from langchain_ollama.embeddings import OllamaEmbeddings

from langchain_postgres import  PGVector
# Replace the connection string with your own Postgres connection string
CONNECTION_STRING = os.getenv("PG_CONN")
# Replace the vector size with your own vector size
VECTOR_SIZE = 1024
embedding = OllamaEmbeddings(model="bge-m3:567m",
                             base_url="http://127.0.0.1:11434")
TABLE_NAME = "articles"
COLLECTION_NAME = "articles"
vectorstore = PGVector(
    connection=CONNECTION_STRING,
    collection_name=COLLECTION_NAME,
    embeddings=embedding,

    # embedding_function=embedding,  # 或自定义
    # embedding_column="embedding",           # 明确指定你的embedding字段
)


if __name__ == "__main__":
    # r = vectorstore.search("游戏")
    results = vectorstore.similarity_search("科技")
    print(len(results))
    print(results)

