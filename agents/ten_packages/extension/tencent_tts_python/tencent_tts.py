import asyncio
from dataclasses import dataclass

from websocket import WebSocketConnectionClosedException

from ten.async_ten_env import AsyncTenEnv
from ten_ai_base.config import BaseConfig
from .tencentcloud_speech_sdk.common import credential
from .tencentcloud_speech_sdk.flowing_speech_synthesizer import (
    FlowingSpeechSynthesisListener,
    FlowingSpeechSynthesizer,
)


@dataclass
class TencentTTSConfig(BaseConfig):
    app_id: str = ""
    secret_id: str = ""
    secret_key: str = ""
    voice_type: int = 0
    codec: str = "pcm"
    enable_subtitle: bool = False
    sample_rate: str = "16000"


class AsyncIteratorCallback(FlowingSpeechSynthesisListener):
    def __init__(self, ten_env: AsyncTenEnv, queue: asyncio.Queue) -> None:
        self.closed = False
        self.ten_env = ten_env
        self.loop = asyncio.get_event_loop()
        self.queue = queue

    def close(self):
        self.closed = True

    def on_synthesis_start(self, session_id):
        self.ten_env.log_info(f"Speech synthesis start: session_id={session_id}")

    def on_synthesis_end(self):
        self.ten_env.log_info("Speech synthesis task complete successfully.")
        self.close()

    def on_audio_result(self, audio_bytes):
        self.ten_env.log_info(
            f"On_audio_result: recv audio bytes, len={len(audio_bytes)}"
        )
        if self.closed:
            self.ten_env.log_warn(
                f"Received data: {len(audio_bytes)} bytes but connection was closed"
            )
            return
        self.ten_env.log_info(f"Received data: {len(audio_bytes)} bytes")
        asyncio.run_coroutine_threadsafe(self.queue.put(audio_bytes), self.loop)

    def on_synthesis_fail(self, response):
        self.ten_env.log_error(
            f"On_synthesis_fail: code={response['code']} msg={response['message']}"
        )


class TencentTTS:
    def __init__(self, config: TencentTTSConfig) -> None:
        self.config = config
        self.synthesizer = None  # Initially no synthesizer
        self.queue = asyncio.Queue()

    def create_synthesizer(self, ten_env: AsyncTenEnv):
        if self.synthesizer:
            self.synthesizer = None

        ten_env.log_info(f"Creating new synthesizer,config:{self.config}")
        credential_var = credential.Credential(
            self.config.secret_id, self.config.secret_key
        )
        callback = AsyncIteratorCallback(ten_env, self.queue)
        synthesizer = FlowingSpeechSynthesizer(
            self.config.app_id, credential_var, callback
        )

        synthesizer.set_voice_type(self.config.voice_type)
        synthesizer.set_codec(self.config.codec)
        synthesizer.set_sample_rate(int(self.config.sample_rate))
        synthesizer.set_enable_subtitle(self.config.enable_subtitle)

        self.synthesizer = synthesizer

    def start(self, ten_env: AsyncTenEnv) -> None:
        if self.synthesizer:
            self.synthesizer.start()
            ten_env.log_info("Synthesizer started")
        else:
            ten_env.log_warn("Synthesizer is not initialized")

    async def get_audio_bytes(self) -> bytes:
        return await self.queue.get()

    def text_to_speech_stream(self, ten_env: AsyncTenEnv, text: str, _: bool) -> None:
        if not self.synthesizer:
            ten_env.log_error("Synthesizer is not initialized")
            return

        try:
            self.synthesizer.process(text)

        except WebSocketConnectionClosedException as e:
            ten_env.log_error(f"WebSocket connection closed, {e}")
            self.synthesizer = None
        except Exception as e:
            ten_env.log_error(f"Error streaming text, {e}")
            self.synthesizer = None

    def cancel(self, ten_env: AsyncTenEnv) -> None:
        if self.synthesizer:
            self.synthesizer = None
