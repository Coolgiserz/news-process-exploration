from __future__ import annotations
from typing import  Protocol, List
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
    def summarize(self, text: str, max_chars: int) -> SummaryResult: ...

class SummaryResult(BaseModel):
    summary: str = Field(description="摘要文本")
    keywords: List[str] = Field(description="新闻主题关键词列表")

# -------------------- LLM Summarizer ------------------ #
DEFAULT_MAX_CHARS = int(os.getenv("MAX_ABSTRACT_CHARS", "160"))
OLLAMA_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

PROMPT_TMPL = """
你是一名资深中文新闻编辑，请阅读【新闻正文】，在保持核心信息完整的前提下，
用 **一句话** 写出精炼摘要并提取新闻的主题关键词。要求：
1. **长度 ≤ {max_chars} 个汉字**（标点也计入长度，英文/数字按 1 字）。
2. 避免使用“本文”“文章”等空洞前缀。
3. 只写一句，不得分号、顿号并列多句。

【新闻正文】:
{article}
【注意】
1. 不得编造信息，必须严格按照原文内容进行摘要。
2. 提取关键词时需规避常见的广告、营销等干扰信息。
【输出格式】
{format_instructions}
"""



class LLMSummarizerImpl(AbstractSummarizer):
    def __init__(
        self,
        max_chars: int = DEFAULT_MAX_CHARS,
        model: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        chain=None,  # 新增参数
    ):
        self.max_chars = max_chars
        self.model = model
        self.base_url = base_url
        self._chain = chain or self._build_chain()  # 支持注入

    @lru_cache(maxsize=1)
    def _build_chain(self):
        prompt = PromptTemplate.from_template(PROMPT_TMPL)
        llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0, format="json")
        output_parser = PydanticOutputParser(pydantic_object=SummaryResult)
        chain = prompt.partial(format_instructions=output_parser.get_format_instructions()) | llm | output_parser
        return chain

    def summarize(self, text: str, max_chars: int = None) -> SummaryResult:
        if max_chars is None:
            max_chars = self.max_chars
        try:
            result = self._chain.invoke({"article": text, "max_chars": max_chars})
            # TODO 停用词，LLM输出关键词可能含有广告
            return result
        except Exception as e:
            raise e