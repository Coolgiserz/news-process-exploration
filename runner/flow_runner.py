"""runner.flow_runner

简化版 FlowRunner，实现 inprocess 调度与依赖解析。完整 DAG/AB 等高级功能可进一步扩展。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Set

from common.models import ArticleInput, ArticleNLPResult
from common.protocol import Context, REGISTRY, Processor
from .executor import InProcExecutor, Task


class FlowRunner:
    """简化版，仅 inprocess 执行。"""

    def __init__(self, steps: List[str] | None = None):
        self.steps = steps  # None ⇒ 自动全量
        self.executor = InProcExecutor()

    def _resolve_processors(self) -> List[Processor]:
        if self.steps is None:
            selected = list(REGISTRY.keys())
        else:
            selected = self.steps
        procs = [REGISTRY[name](**{}) for name in selected]  # type: ignore[arg-type]
        # TODO: 拓扑排序；这里按列表顺序
        return procs

    async def process_async(self, article: ArticleInput) -> ArticleNLPResult:
        ctx = Context()
        article_id = article.id or ""
        data: Dict[str, Any] = article.model_dump(exclude={"id"})
        result_errors: Dict[str, str] = {}
        for proc in self._resolve_processors():
            missing = proc.requires - data.keys()
            if missing:
                result_errors[proc.name] = f"missing deps: {missing}"
                continue
            task: Task = {
                "processor": proc,
                "data": data,
                "context": ctx,
            }
            try:
                out = await self.executor.submit(task)
                data.update(out)
            except Exception as e:  # noqa: BLE001
                ctx.logger.exception(
                    "processor %s failed: %s", proc.name, str(e)
                )
                result_errors[proc.name] = str(e)
        return ArticleNLPResult(id=article_id, **data, errors=result_errors or None)

    def process(self, article: ArticleInput) -> ArticleNLPResult:
        return asyncio.run(self.process_async(article)) 