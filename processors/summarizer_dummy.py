from __future__ import annotations

from common.protocol import register, Context

@register
class DummySummarizer:
    name = "dummy_summary"
    version = "0.1.0"
    requires = {"clean_text"}
    provides = {"summary"}

    def __init__(self, max_len: int = 30, **cfg):
        self.max_len = max_len

    def run(self, data: dict, ctx: Context):  # type: ignore[override]
        ct = data["clean_text"]
        summary = ct[: self.max_len]
        return {"summary": summary} 