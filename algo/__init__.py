"""algo package: 提供算法层抽象 (SummarizerService 等)。"""

from .summarizers.summarizer_service import SummarizerService, register_summarizer

__all__ = ["SummarizerService", "register_summarizer"] 