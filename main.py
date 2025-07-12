import os
# https://stackoverflow.com/questions/28521535/requests-how-to-disable-bypass-proxy
os.environ["NO_PROXY"]="localhost"


from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_ollama.embeddings import OllamaEmbeddings

# from langchain_postgres import PGEngine, PGVectorStore
# PGVectorStore.areindex()
# Replace the connection string with your own Postgres connection string
CONNECTION_STRING = "postgresql+psycopg3://langchain:langchain@localhost:6024/langchain"
# engine = PGEngine.from_connection_string(url=CONNECTION_STRING)

# Replace the vector size with your own vector size
VECTOR_SIZE = 1024
# proxy = {'https': 'http://127.0.0.1:你的vpn端口', 'http': 'http://127.0.0.1:你的vpn端口'}
# proxy = "http://127.0.0.1:7890"

embedding = OllamaEmbeddings(model="bge-m3:567m",
                             base_url="http://127.0.0.1:11434")

TABLE_NAME = "news"

# engine.init_vectorstore_table(
#     table_name=TABLE_NAME,
#     vector_size=VECTOR_SIZE,
# )
#
# store = PGVectorStore.create_sync(
#     engine=engine,
#     table_name=TABLE_NAME,
#     embedding_service=embedding,
# )
# embedding.embed_documents()
# PGVectorStore.search()

docs = [
    Document(page_content="Apples and oranges"),
    Document(page_content="Cars and airplanes"),
    Document(page_content="Train")
]

# store.add_documents(docs)
# query = "I'd like a fruit."
# docs = store.similarity_search(query)
# print(docs)
if __name__ == "__main__":
    text_vector = embedding.embed_query("游戏娱乐")
    # embedding.embed_documents()
    print(text_vector)
    text_vector = embedding.embed_query("科技")
    # embedding.embed_documents()
    print(text_vector)

    text_vector = embedding.embed_query("文化")
    # embedding.embed_documents()
    print(text_vector)
    print(len(text_vector))

