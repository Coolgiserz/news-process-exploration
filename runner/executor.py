"""runner.executor

定义统一的 Executor 接口、InProcExecutor 与 (简化) EventBusExecutor。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from common.protocol import Context, Processor


class Task(dict):
    """简单任务封装：包含 processor 实例、数据、context。"""

    processor: Processor  # type: ignore[override]
    context: Context


class Executor:
    """执行器通用接口。"""

    async def submit(self, task: Task) -> Dict[str, Any]: ...

    async def shutdown(self): ...


# ----------------- In-Process 执行 ----------------- #
class InProcExecutor(Executor):
    async def submit(self, task: Task):  # type: ignore[override]
        proc: Processor = task["processor"]
        ctx: Context = task["context"]
        data = task["data"]
        # 直接同步执行，包一层 asyncio 兼容
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, proc.run, data, ctx)

    async def shutdown(self):
        return None


# -------------- EventBus 执行（简化） --------------- #
class EventBusExecutor(Executor):
    """示例 stub：真正实现需接入 Redis/Kafka，这里仅接口。"""

    def __init__(self, bus_client):
        self.bus = bus_client

    async def submit(self, task: Task):  # type: ignore[override]
        # 将任务序列化后推送消息队列；等待结果；这里简化为 NotImplemented
        raise NotImplementedError("EventBusExecutor 需要结合消息队列实现")

    async def shutdown(self):
        pass 