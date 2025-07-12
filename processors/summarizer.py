"""processors.summarizer_llm

使用 LangChain + Ollama 的正式摘要 Processor。
同样暴露 `summarize(text)` 便于脚本快速调用。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional

from dotenv import load_dotenv
from common.protocol import Processor, Context, register
from algo.summarizers.summarizer_service import  AbstractSummarizer, LLMSummarizerImpl, SummaryResult

load_dotenv()

DEFAULT_MAX_CHARS = int(os.getenv("MAX_ABSTRACT_CHARS", "160"))

# 单例 summarizer 实例
@lru_cache(maxsize=1)
def _get_llm_summarizer():
    return LLMSummarizerImpl(max_chars=DEFAULT_MAX_CHARS)

@register
class LLMSummarizer(Processor, AbstractSummarizer):
    name = "summarizer_llm"
    version = "1.0.0"
    requires = {"clean_text"}
    provides = {"summary"}

    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS, **cfg):
        super().__init__(**cfg)
        self.max_chars = max_chars
        # cfg 可用于覆盖模型参数
        self.summarizer = _get_llm_summarizer()

    def run(self, data: Dict[str, str], ctx: Context):  # type: ignore[override]
        article = data["clean_text"]
        try:
            result = self.summarizer.summarize(article, max_chars=self.max_chars)
        except Exception as e:  # noqa: BLE001
            ctx.logger.error("LLM summarizer error", exc_info=e)
            result = None
        return {"summary": result}

    def summarize(self, text: str, max_chars: int) -> SummaryResult:  # type: ignore[override]
        return self.summarizer.summarize(text, max_chars)

# 辅助函数：独立调用

def summarize(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> Optional[SummaryResult]:
    try:
        return _get_llm_summarizer().summarize(text, max_chars)
    except Exception as e:
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        content = sys.stdin.read()
    print(summarize(content)) 