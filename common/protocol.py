"""common.protocol

定义 Processor 协议、Context 与注册装饰器。
"""

from __future__ import annotations
import logging
import uuid
from typing import Any, ClassVar, Dict, Protocol, Set, Type, TypeVar

from pydantic import BaseModel

# --------------------- 基础结构 --------------------- #
class Context(BaseModel):
    """在流水线中贯穿的上下文对象。"""

    trace_id: str = uuid.uuid4().hex
    logger: Any = logging.getLogger("processor")  # 可被替换
    cache: Dict[str, Any] = {}


class Processor(Protocol):
    """所有 NLP 处理组件需遵循的协议。"""

    # --- 类级元数据 ---
    name: ClassVar[str]
    version: ClassVar[str] = "1.0.0"
    requires: ClassVar[Set[str]] = set()
    provides: ClassVar[Set[str]] = set()

    def __init__(self, **config: Any) -> None: ...

    def run(self, data: Dict[str, Any], ctx: Context) -> Dict[str, Any]: ...


# --------------------- 注册中心 --------------------- #
T = TypeVar("T", bound=Type)
REGISTRY: Dict[str, Type[Processor]] = {}


def register(cls: T) -> T:  # type: ignore[valid-type]
    """类装饰器，将 Processor 注册到全局 REGISTRY。"""
    if not hasattr(cls, "name"):
        raise AttributeError("Processor 必须定义 class 属性 'name'")
    REGISTRY[cls.name] = cls  # type: ignore[index]
    return cls 