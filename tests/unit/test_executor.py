import asyncio

from common.protocol import Context
from runner.executor import InProcExecutor, Task
from processors.summarizer_dummy import DummySummarizer


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_inproc_executor_summary():
    proc = DummySummarizer(max_len=10)
    data = {"clean_text": "苹果公司推出新款 iPhone。"}
    ctx = Context()
    task = {"processor": proc, "data": data, "context": ctx}

    executor = InProcExecutor()
    result = run_async(executor.submit(task))

    assert result["summary"] == "苹果公司推出新款 i" 