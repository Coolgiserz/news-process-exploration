### 当前向量数据库的设计与实现方案总结

#### 1. 设计目标
- 支持新闻数据的高效语义检索与后续AI应用。
- 主库与向量库分离，便于扩展、维护和资源隔离。
- 支持增量同步、元数据补全、幂等写入。

#### 2. 主要表结构

- **主库（如 news.articles）**
  - 主要字段：id/fingerprint、title、text、summary、url、publish_date、source_name、keywords
  - 增加同步标记字段：`title_vector_synced`（bool）、`title_vector_synced_at`（timestamp）

- **向量库（如 articles_vector）**
  - 主要字段：id、fingerprint、title、text、summary、url、publish_date、source_name、keywords、embedding（vector）、metadata（jsonb）

#### 3. ETL与同步流程

- 只抽取主库中 `title_vector_synced IS NOT TRUE` 的数据，避免重复处理。
- 对标题（可扩展为正文/摘要/切片）进行向量化，写入向量库。
- 向量化成功后，回写主库同步状态。
- 支持元数据补全，后续可通过 update 语句修正。

#### 4. 主要代码实现

- `pipeline/main_vector_store_creation.py`：ETL主脚本，已重构为函数式结构，便于维护和扩展。
- `examples/vector_search_demo.py`：只做向量库检索，便于效果测试和演示。

#### 5. 检索与应用

- 支持通过 LangChain 的 PGVectorStore 进行语义检索，返回内容和元数据，便于下游AI应用（如摘要、问答、推荐等）。

---

### 后续 TODO

1. **支持正文/摘要/多字段向量化**
   - 增加对正文、摘要或“标题+正文”拼接的向量化与检索。
   - 支持长文本自动切片（chunking）。

2. **批量/并发处理优化**
   - 支持大批量数据分批处理，提升效率。
   - 增加异常重试、失败日志记录。

3. **多模型/多版本支持**
   - 支持不同 embedding 模型、不同向量表的管理与切换。

4. **元数据补全与修正**
   - 增加自动/手动元数据补全脚本。
   - 支持后续 update 修正向量库中的元数据。

5. **检索效果评测与可视化**
   - 增加自动化评测脚本，支持批量查询与召回率/准确率统计。
   - 可视化检索结果，便于调优。

6. **权限与安全**
   - 加强数据库连接、数据访问的权限管理。

7. **文档与测试**
   - 完善开发文档、接口说明和单元测试。

8. **支持多语言/多源数据**
   - 适配多语种新闻、不同来源的数据同步与向量化。

---
