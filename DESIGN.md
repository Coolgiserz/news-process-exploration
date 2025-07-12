# 新闻语义加工平台 - 设计方案

> 版本：2024-07-12

---

## 目标
1. 将「新闻 → NLP 多任务 → 结构化结果」拆成 **可插拔 / 可组合** 的 Processor。  
2. 允许 **单点开发 & 测试**，也能通过 DAG 编排成完整流水线。  
3. 存储层与数据库实现解耦，支持 Postgres / MySQL / MongoDB / OpenSearch。

---

## 架构总览
```
┌─────────────┐  raw(title,text,meta)
│  ETL / 抓取 │
└──────┬──────┘
       ▼ dict
┌────────────────┐     manifest.yml / --steps ner
│  FlowRunner-V2 │  ◄───────────────────────────┐
│ • 依赖解析     │                             │
│ • 并行/重试    │                             │
│ • AB / Shadow  │                             │
└───┬───────┬────┘                             │
    │       │     event-bus (可选)             │
┌───▼───┐ ┌─▼────┐ … n 个 Processor            │
│Proc A │ │Proc B │  (Cleaner / NER / …)        │
└───┬───┘ └──┬────┘                             │
    └─merge─▼───────────────────────────────────┘
          ArticleNLPResult(dict/Pydantic)
                   ▼
              Repository
                   ▼
               DB / ES
```

---

## 1. Processor V2 协议
```python
class Context(BaseModel):
    trace_id: str
    logger: Any
    cache: dict = {}

class Processor:  # typing.Protocol in common/protocol.py
    name: ClassVar[str]
    version: ClassVar[str] = "1.0.0"
    requires: ClassVar[set[str]] = set()
    provides: ClassVar[set[str]] = set()

    def __init__(self, **cfg): ...
    def run(self, data: dict, ctx: Context) -> dict: ...
```
* **无状态**：输入输出均为字典 / Pydantic-Model。  
* **requires / provides**：声明依赖与产出，FlowRunner 自动拓扑排序。  
* **Context**：贯穿流水线的追踪 / 日志 / 缓存。

### Quick Demo
```python
@register
class Cleaner(Processor):
    name, requires, provides = "cleaner", {"text"}, {"clean_text"}
    def run(self, d, ctx):
        ct = d["text"].replace("\n", " ")
        return {"clean_text": ct}
```

---

## 2. Manifest – 声明式 DAG
```yaml
pipeline: news_nlp_v1
mode: inprocess            # eventbus | inprocess
steps:
  cleaner:
    impl: processors.cleaner.Cleaner
  summarizer:
    impl: processors.summarizer.LLMSummary
    after: [cleaner]
  ner_v1:
    impl: processors.ner.spacy_NER
    after: [cleaner]
    version: 1.0.0
  ner_v2:
    impl: http://ner-svc:8000/run   # 远程微服务
    after: [cleaner]
    version: 2.0.0
    ab_ratio: 0.3                   # 30% 灰度
  aggregator:
    impl: processors.aggregator.MergeEntities
    after: [summarizer, ner_v1, ner_v2]
```
* `impl` 可为 Python import-path 或 HTTP URL。  
* `ab_ratio` / `shadow:true` 支持灰度 & 影子流量。  
* CLI 指定 `--steps summarizer` 可单点运行。

---

## 3. FlowRunner-V2
| 功能 | 说明 |
|------|------|
| DAG 构建 | 解析 Manifest → NetworkX DAG |
| 依赖调度 | 自动补前置节点，拓扑排序 |
| 并行执行 | asyncio + Semaphore，如有 event-bus 改为消息分发 |
| 错误策略 | `fail_fast` / `skip_error`；错误写入 `errors[proc]` |
| 缓存幂等 | `(article_hash, proc_version)` 已存在即跳过 |
| AB / Shadow | 根据 `ab_ratio` 随机路由；`shadow` 结果仅日志 |
| 监控埋点 | OpenTelemetry trace + Prometheus metrics |

---

## 4. 存储模型优化
```
Article(id PK, source, publish_time, title, text, raw_hash)
Embedding(article_id FK, vector_id)          # 向量落 OpenSearch
ArticleNLP(article_id FK, summary, sentiment_label, sentiment_score,
           category, keywords JSON, topics JSON,
           proc_version, updated_at)
Entity(id PK, article_id FK, text, type, offset_start, offset_end,
       confidence)
Event(id PK, article_id FK, trigger, type, arguments JSONB, confidence)
ProcessorLog(article_id, processor, version, success, duration_ms, error,
             trace_id, created_at)
```
* **列可为 NULL** → 模块级写入互不影响。  
* 向量统一写 OpenSearch `dense_vector`，关系库只存 `vector_id`。  
* `confidence` 便于结果融合。  
* `proc_version` 支持回溯。

---

## 5. 插件注册
```python
REGISTRY: dict[str, type[Processor]] = {}

def register(cls):
    REGISTRY[cls.name] = cls
    return cls
```
多语言微服务遵循同一 JSON schema：
```
POST /run  {data, context, requires, provides}
```

---

## 6. 监控 & 日志
* **Trace**：OpenTelemetry SDK，`trace_id` 写入 Context → ProcessorLog。  
* **Metrics**：Prometheus exporter
  `processor_duration_seconds{proc,version}`  
  `processor_fail_total{proc}`  
* **Log**：Loki / ELK 聚合，按 `trace_id` 检索。

---

## 7. 部署演化
| 阶段 | Runner | Processor 部署 | 事件总线 |
|------|--------|----------------|----------|
| PoC 单机 | inprocess | 本地 Python | – |
| 小规模 Cron | inprocess | Docker Compose | – |
| 生产 | eventbus | K8s 部署 | Redis-Streams / RabbitMQ |
| 全量 & 灰度 | eventbus + AB | K8s + Helm | RabbitMQ |

---

## 8. 迭代路线
1. **Step-0** ⟶ 实现 Cleaner / Summarizer / Sentiment + SqlNewsRepository，手动调用。  
2. **Step-1** ⟶ 上线 FlowRunner + Manifest，支持 `--steps` 单点调试。  
3. **Step-2** ⟶ 增加 NER / Event / Keyword，跑全量 DAG。  
4. **Step-3** ⟶ 引入 AB 灰度（ner_v2），并接 OpenSearch 向量。  
5. **Step-4** ⟶ 编写 MongoNewsRepository，验证跨数据库无感迁移。

---

## 9. 代码示例
```python
# processors/summarizer_llm.py
@register
class LLMSummarizer(Processor):
    name, version = "summarizer_llm", "1.1.0"
    requires, provides = {"clean_text"}, {"summary"}

    def __init__(self, model="qwen3:4b"):
        self.llm = ChatOllama(model=model, base_url="http://localhost:11434")

    def run(self, d, ctx):
        prompt = f"概括为≤60字: {d['clean_text']}"
        summary = self.llm.invoke(prompt).strip()
        return {"summary": summary}
```

---

> 该文档替代旧版设计，体现 **类型安全、灰度发布、异步扩展、监控** 四大优化点。