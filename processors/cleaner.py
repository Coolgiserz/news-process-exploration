from __future__ import annotations

from common.protocol import register, Processor, Context

@register
class Cleaner:
    name = "cleaner"
    version = "1.0.0"
    requires = {"text"}
    provides = {"clean_text"}

    def __init__(self, **cfg):
        pass

    def run(self, data: dict, ctx: Context):  # type: ignore[override]
        text = data["text"].strip()
        return {"clean_text": text} 