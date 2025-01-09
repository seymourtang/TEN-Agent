from dataclasses import dataclass

from ten_ai_base.config import BaseConfig


@dataclass
class ToolConfig(BaseConfig):
    duration: str = "20"
    loop_count: str = "5"
    file_path: str = (
        "/app/agents/ten_packages/extension/tts_test_tool_python/tts_test.txt"
    )
