from unittest.mock import patch

from common.models import ArticleInput
from runner.flow_runner import FlowRunner
import processors.cleaner  # noqa: F401  ensure registration
import processors.event_llm  # noqa: F401  ensure registration

MOCK_RESPONSE = (
    '[{"trigger":"发布","type":"ProductLaunch","arguments":'
    '[{"role":"主体","text":"苹果公司"},{"role":"客体","text":"iPhone 15"}]}]'
)

def test_event_llm_processor(monkeypatch):
    # Mock ChatOllama.invoke to return predefined JSON
    with patch("processors.event_llm.ChatOllama.invoke", return_value=MOCK_RESPONSE):
        article = ArticleInput(title="发布会", text="苹果公司今日发布 iPhone 15。")
        runner = FlowRunner(steps=["cleaner", "event_llm"])
        result = runner.process(article)

        assert result.events, "应解析到事件"
        evt = result.events[0]
        assert evt.type == "ProductLaunch"
        assert evt.trigger == "发布"
        roles = {arg.role for arg in evt.arguments}
        assert "主体" in roles and "客体" in roles

def test_event_llm_processor_real():
    # Mock ChatOllama.invoke to return predefined JSON
    article = ArticleInput(title="发布会", text="苹果公司今日发布 iPhone 15。")
    runner = FlowRunner(steps=["cleaner", "event_llm"])
    result = runner.process(article)

    assert result.events, "应解析到事件"
    evt = result.events[0]
    assert evt.type == "ProductLaunch"
    assert evt.trigger == "发布"
    roles = {arg.role for arg in evt.arguments}
    assert roles, "应解析到主体客体"
    print(result)