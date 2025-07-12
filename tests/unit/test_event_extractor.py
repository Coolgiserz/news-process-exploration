from common.models import ArticleInput
from runner.flow_runner import FlowRunner
import processors.cleaner  # noqa: F401
import processors.event_extractor  # noqa: F401


def test_event_extractor():
    text = "苹果公司今日宣布推出全新iPhone 15系列。"
    art = ArticleInput(title="苹果发布会", text=text)
    runner = FlowRunner(steps=["cleaner", "event_dummy"])
    result = runner.process(art)
    assert result.events
    assert result.events[0].trigger == "宣布"
    print(result.events)