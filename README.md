# 新闻语义加工平台

本仓库旨在构建一个**可插拔、可组合、可扩展**的新闻语义处理平台，支持标题向量化、摘要生成、事件抽取、情感分析、主题分类等 NLP 能力，并且保持对数据库类型（Postgres / MySQL / MongoDB / OpenSearch）的解耦。

---

## 目标
1. **模块化**：每种 NLP 任务实现为独立 `Processor`，遵循统一协议。  
2. **组合灵活**：通过 Manifest（YAML）声明流水线，单点或全流程随意切换。  
3. **可扩展**：支持 in-process & event-bus 两种执行模式，方便从单机到分布式扩容。  
4. **类型安全**：输入 / 输出用 Pydantic 描述，LLM 调用用 `PydanticOutputParser` 强制结构化。  
5. **监控与灰度**：内置 OpenTelemetry 埋点，FlowRunner 支持 AB / Shadow 发布。  
6. **存储解耦**：Repository 抽象封装数据库操作，后端可替换。

---

## 快速开始
```bash
# 1. 安装依赖
uv sync

# 2. 运行示例摘要 & 事件提取
python - <<'PY'
from common.models import ArticleInput
from runner.flow_runner import FlowRunner
import processors.cleaner, processors.summarizer, processors.event_llm  # 注册组件

art = ArticleInput(title="苹果发布会", text="苹果公司今日发布 iPhone 15，搭载全新芯片……")
runner = FlowRunner(steps=["cleaner", "summarizer_llm", "event_llm"])
print(runner.process(art))
PY
```

> 若无 GPU / LLM，可将 `event_llm` 换成 `event_dummy`、`summarizer_llm` 换成 `dummy_summary`。

---

## 核心概念
### Processor 协议
```python
class Processor(Protocol):
    name: str
    version: str = "1.0.0"
    requires: set[str]  # 依赖字段
    provides: set[str]  # 输出字段
    def run(self, data: dict, ctx: Context) -> dict: ...
```
### FlowRunner
负责解析 Manifest / 步骤列表 → 构建 DAG → 调用 Executor（inprocess / eventbus）依序运行 Processor。

### Repository
`SqlNewsRepository` 默认实现；若需切换 MongoDB 仅需实现相同接口即可。

---

## 目录结构
```
common/       协议、Pydantic 数据模型
processors/   各类 NLP 组件 (cleaner, summarizer, event extractor…)
runner/       executor + flow_runner
repo/         SqlNewsRepository 及未来的 MongoNewsRepository
pipeline/     批处理脚本（向量回填、摘要回填）
docs/         规范文档（事件 schema 等）
```

---

## 事件抽取规范
详见 `docs/event_schema.md`。

---

## 贡献指南
1. 新增组件：在 `processors/` 添加文件并使用 `@register`；`requires/provides` 写清楚依赖。  
2. 若需数据库操作，请通过 `repo.NewsRepository` 抽象层。  
3. 编写对应单元测试放在 `tests/`，运行 `pytest` 需全部通过。

---

## TODO
- [ ] 完成 TopicClassifier Processor  
- [ ] 引入 Redis Streams 实现 EventBusExecutor  
- [ ] Prometheus / Grafana Dashboards  
- [ ] CI: GitHub Actions 运行测试 + 代码格式检查

