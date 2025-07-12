from common.models import ArticleInput
from runner.flow_runner import FlowRunner
import processors.cleaner  # noqa: F401  (register)
import processors.summarizer_dummy  # noqa: F401


def test_flow_runner_summary():
    article = ArticleInput(title="T", text="苹果公司\n推出新款 iPhone。")
    runner = FlowRunner(steps=["cleaner", "dummy_summary"])
    result = runner.process(article)

    assert result.summary is not None
    # summary 应去掉换行且长度<=30
    assert "\n" not in result.summary
    assert len(result.summary) <= 30
    assert not result.errors 