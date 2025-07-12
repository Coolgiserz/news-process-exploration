from __future__ import annotations
from typing import Callable, Dict, Protocol
from functools import lru_cache
import os
from dotenv import load_dotenv
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

load_dotenv()

# -------------------- 协议 -------------------- #
class AbstractSummarizer(Protocol):
    def summarize(self, text: str, max_chars: int) -> str: ...


# -------------------- 注册器 ------------------ #
_REGISTRY: Dict[str, Callable[..., AbstractSummarizer]] = {}

def register_summarizer(name: str):
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


# -------------------- Facade ------------------ #
class SummarizerService:
    """汇总多种摘要实现，按 kind 选择后端。"""

    def __init__(self, *, kind: str = "llm", **cfg):
        if kind not in _REGISTRY:
            raise ValueError(f"未知 summarizer kind: {kind}")
        self.backend = _REGISTRY[kind](**cfg)

    def summarize(self, text: str, max_chars: int) -> str:
        return self.backend.summarize(text, max_chars) 


# -------------------- LLM Summarizer ------------------ #
DEFAULT_MAX_CHARS = int(os.getenv("MAX_ABSTRACT_CHARS", "160"))
OLLAMA_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

PROMPT_TMPL = """
你是一名资深中文新闻编辑，请阅读【新闻正文】，在保持核心信息完整的前提下，
用 **一句话** 写出精炼摘要。要求：
1. **长度 ≤ {max_chars} 个汉字**（标点也计入长度，英文/数字按 1 字）。
2. 避免使用“本文”“文章”等空洞前缀。
3. 只写一句，不得分号、顿号并列多句。

【新闻正文】:
{article}
【注意】
不得编造信息，必须严格按照原文内容进行摘要。
【输出格式】
{format_instructions}
"""

class SummaryResult(BaseModel):
    summary: str = Field(
        description="摘要文本"    )

class LLMSummarizerImpl(AbstractSummarizer):
    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.max_chars = max_chars
        self.model = model
        self.base_url = base_url
        self._chain = self._build_chain()

    @lru_cache(maxsize=1)
    def _build_chain(self):
        prompt = PromptTemplate.from_template(PROMPT_TMPL)
        llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0, format="json")
        output_parser = PydanticOutputParser(pydantic_object=SummaryResult)
        chain = prompt.partial(format_instructions=output_parser.get_format_instructions()) | llm | output_parser
        return chain

    def summarize(self, text: str, max_chars: int = None) -> str:
        if max_chars is None:
            max_chars = self.max_chars
        try:
            result = self._chain.invoke({"article": text, "max_chars": max_chars})
            return result.summary
        except Exception as e:
            raise e