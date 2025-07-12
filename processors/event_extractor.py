from __future__ import annotations

import re
from typing import Dict, List

from common.protocol import register, Processor, Context
from common.models import Event, EventArg

@register
class DummyEventExtractor(Processor):
    """非常简化的事件抽取，仅示范 Processor 接口。"""

    name = "event_dummy"
    version = "0.1.0"
    requires = {"clean_text"}
    provides = {"events"}

    def __init__(self, **cfg):
        # 可接收 regex 列表、关键词等配置
        self.pattern = re.compile(r"(宣布|发布|推出|签署|完成|收购)")

    def run(self, data: Dict[str, str], ctx: Context):  # type: ignore[override]
        text = data["clean_text"]
        m = self.pattern.search(text)
        if not m:
            return {"events": []}
        trigger_word = m.group(0)
        evt = Event(trigger=trigger_word, type="STATEMENT", arguments=[EventArg(role="trigger", text=trigger_word)])
        return {"events": [evt]} 