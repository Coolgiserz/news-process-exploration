from __future__ import annotations

import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import Field, ValidationError, BaseModel

from common.protocol import register, Processor, Context
from common.models import Event

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

EVENT_TYPES = [
    "ProductLaunch", "Acquisition", "Financing", "PersonnelChange",
    "PolicyRelease", "Partnership", "Lawsuit"
]


PROMPT = PromptTemplate.from_template(
    """
你是新闻事件抽取系统，请从【句子】中识别 *真实发生* 的事件，**最多 {max_events} 条**。
事件须按如下 JSON 列表输出，若无事件返回 `[]`。严禁输出除 JSON 之外的其他字符。
单条事件 JSON 结构示例：\n{schema}\n
允许的 type 枚举: {types}

【句子】: {sentence}
JSON:
"""
)


class EventList(BaseModel):
    data: List[Event] = Field(
        description="事件列表",
        default_factory=list,
    )

@register
class LLMEvtExtractor(Processor):
    name = "event_llm"
    version = "1.0.0"
    requires = {"clean_text"}
    provides = {"events"}

    def __init__(self, max_events: int = 3, **cfg):
        super().__init__(**cfg)
        self.max_events = max_events
        # format="json"避免推理模型输出think标签
        self.llm = ChatOllama(model=OLLAMA_MODEL,
                      base_url=OLLAMA_BASE_URL,
                      temperature=0,
                     format="json"
                    )

        self.parser = PydanticOutputParser(pydantic_object=EventList)

        self.prompt = PromptTemplate(
            template="""
你是新闻事件抽取系统，请从【句子】中识别真实发生的事件，
最多 {max_events} 条，若无事件返回 []。

允许的事件类型: {types}

【句子】:
{sentence}

仅输出 JSON Array，无需输出你的推理过程，格式如下：
{format_instructions}
""",
            input_variables=["sentence", "max_events", "types"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        # 将组件串成 chain
        self.chain = self.prompt | self.llm | self.parser

    
    def run(self, data: Dict[str, str], ctx: Context):  # type: ignore[override]
        sentence = data["clean_text"]
        try:
            llm_result = self.chain.invoke(
                    {
                        "sentence": sentence,
                        "max_events": self.max_events,
                        "types": ", ".join(EVENT_TYPES),
                    },
                    config={"tags": ["event_llm", ctx.trace_id]},
                )
            if llm_result:
                events = llm_result.data[:self.max_events]                    # truncate if too many
            else:
                events = []
        except ValidationError as e:                           # JSON 字段不合法
            ctx.logger.error("event_parse_fail", exc_info=e)
            raise
        return {"events": events} 