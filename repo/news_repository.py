"""repo.news_repository

上层仓储接口，以便未来新增 Mongo/Elastic 等不同实现。

定义：
    class INewsRepository (typing.Protocol)

默认实现：
    class SqlNewsRepository -> 复用 dao.NewsDAO 逻辑
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Iterable, List, Protocol, Sequence, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError

# ----------------------- 仓储接口 ----------------------- #
class INewsRepository(Protocol):
    """新闻仓储协议，屏蔽存储细节。"""

    # --- Schema 管理 ---
    def ensure_embedding_schema(self, vector_size: int = 1024) -> None: ...
    def ensure_abstract_schema(self) -> None: ...

    # --- Embedding ---
    def fetch_without_embedding(
        self, *, after_ts: datetime, limit: int
    ) -> Sequence[Tuple[int, datetime, str]]: ...

    def update_embeddings(self, rows: Iterable[Tuple[int, List[float]]]) -> None: ...

    # --- Abstract ---
    def fetch_without_abstract(
        self, *, after_ts: datetime, limit: int
    ) -> Sequence[Tuple[int, datetime, str]]: ...

    def update_abstracts(self, rows: Iterable[Tuple[int, str]]) -> None: ...

    # --- 资源释放 ---
    def dispose(self) -> None: ...


# -------------------- SQL 实现 ------------------------- #
DEFAULT_CONN_STR = os.getenv("PG_CONN") or os.getenv("DB_CONN")


class SqlNewsRepository:  # noqa: D101  (docstring above)
    def __init__(
        self,
        conn_str: str | None = None,
        *,
        table_name: str = "articles",
        time_column: str = "created_at",
    ) -> None:
        self.conn_str = conn_str or DEFAULT_CONN_STR
        if not self.conn_str:
            raise ValueError(
                "必须提供数据库连接字符串 (PG_CONN / DB_CONN) 或构造函数参数 conn_str"
            )

        self.table_name = table_name
        self.time_column = time_column

        self.engine: Engine = create_engine(self.conn_str, future=True, echo=False)
        self.dialect = self.engine.dialect.name

    # --------- Schema ---------
    def _add_column_if_not_exists(self, column_def_sql: str) -> None:
        stmt = f"ALTER TABLE {self.table_name} ADD COLUMN IF NOT EXISTS {column_def_sql};"
        with self.engine.begin() as conn:
            try:
                conn.execute(text(stmt))
            except ProgrammingError as exc:
                if "exists" not in str(exc).lower():
                    raise

    def ensure_embedding_schema(self, vector_size: int = 1024) -> None:
        if self.dialect == "postgresql":
            with self.engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            self._add_column_if_not_exists(f"embedding vector({vector_size})")
        else:
            self._add_column_if_not_exists("embedding TEXT")

        # SQLite 对部分索引或向量列不支持，直接跳过
        if self.dialect == "sqlite":
            return


    def ensure_abstract_schema(self) -> None:
        self._add_column_if_not_exists("summary TEXT")
        if self.dialect == "sqlite":
            return


    # --------- Embedding ---------
    def fetch_without_embedding(
        self, *, after_ts: datetime, limit: int
    ) -> Sequence[Tuple[int, datetime, str]]:
        with self.engine.connect() as conn:
            res = conn.execute(
                text(
                    f"""
                    SELECT id, {self.time_column}, title
                    FROM {self.table_name}
                    WHERE embedding IS NULL AND {self.time_column} > :after_ts
                    ORDER BY {self.time_column}
                    LIMIT :limit
                    """
                ),
                {"after_ts": after_ts, "limit": limit},
            )
            return res.fetchall()

    def update_embeddings(self, rows: Iterable[Tuple[int, List[float]]]) -> None:
        if self.dialect == "postgresql":
            payload = [{"id": r[0], "embedding": r[1]} for r in rows]
        else:
            payload = [{"id": r[0], "embedding": json.dumps(r[1])} for r in rows]

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"UPDATE {self.table_name} SET embedding = :embedding WHERE id = :id"
                ),
                payload,
            )

    # --------- Abstract ---------
    def fetch_without_abstract(
        self, *, after_ts: datetime, limit: int
    ) -> Sequence[Tuple[int, datetime, str]]:
        with self.engine.connect() as conn:
            res = conn.execute(
                text(
                    f"""
                    SELECT id, {self.time_column}, text
                    FROM {self.table_name}
                    WHERE summary IS NULL AND {self.time_column} > :after_ts
                    ORDER BY {self.time_column}
                    LIMIT :limit
                    """
                ),
                {"after_ts": after_ts, "limit": limit},
            )
            return res.fetchall()

    def update_abstracts(self, rows: Iterable[Tuple[int, str, list]]) -> None:
        rows_with_keywords = []
        rows_without_keywords = []
        for r in rows:
            if r[2]:  # keywords 非空
                rows_with_keywords.append({"id": r[0], "summary": r[1], "keywords": json.dumps(r[2], ensure_ascii=False)})
            else:
                rows_without_keywords.append({"id": r[0], "summary": r[1]})

        with self.engine.begin() as conn:
            if rows_with_keywords:
                conn.execute(
                    text(
                        f"UPDATE {self.table_name} SET summary = :summary, keywords = :keywords WHERE id = :id"
                    ),
                    rows_with_keywords,
                )
            if rows_without_keywords:
                conn.execute(
                    text(
                        f"UPDATE {self.table_name} SET summary = :summary WHERE id = :id"
                    ),
                    rows_without_keywords,
                )

    # --------- Dispose ---------
    def dispose(self) -> None:
        self.engine.dispose()


__all__ = ["INewsRepository", "SqlNewsRepository"] 