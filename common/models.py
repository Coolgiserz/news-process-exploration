"""common.models

核心数据模型：ArticleInput、ArticleNLPResult 及子结构。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


class ArticleInput(BaseModel):
    id: Optional[str] = None
    source: Optional[str] = None
    publish_time: datetime = Field(default_factory=datetime.utcnow)
    title: str
    text: str


# -------- NLP 结果子对象 -------- #
class Entity(BaseModel):
    text: str
    type: str  # PER/ORG/LOC/…
    offset: Tuple[int, int]
    confidence: float | None = None


class EventArg(BaseModel):
    role: str
    text: str


class Event(BaseModel):
    trigger: str
    type: str
    arguments: List[EventArg]
    summary: str | None = ""


class Sentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"]
    score: float


class ArticleNLPResult(BaseModel):
    id: str

    summary: Optional[str] = None
    events: Optional[List[Event]] = None
    entities: Optional[List[Entity]] = None
    sentiment: Optional[Sentiment] = None
    keywords: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    category: Optional[str] = None

    errors: Optional[dict[str, str]] = None  # proc -> err msg 