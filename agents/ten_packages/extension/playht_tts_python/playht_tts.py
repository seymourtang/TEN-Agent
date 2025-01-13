import asyncio
from dataclasses import dataclass
import time

from websocket import WebSocketConnectionClosedException

from ten.async_ten_env import AsyncTenEnv
from ten_ai_base.config import BaseConfig
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback


@dataclass
class PlayhtTTSConfig(BaseConfig):
    user_id: str = ""
    api_key: str = ""
    voice: str = ""
    sample_rate: int = 16000

class PlayhtTTS:
    def __init__(self, config: PlayhtTTSConfig) -> None:
        self.config = config
        self.synthesizer = None  # Initially no synthesizer
        self.queue = asyncio.Queue()

    def _create_synthesizer(
        self, ten_env: AsyncTenEnv, callback: AsyncIteratorCallback
    ):
        if self.synthesizer:
            self.synthesizer = None

        ten_env.log_info("Creating new synthesizer")
        self.synthesizer = SpeechSynthesizer(
            model=self.config.model,
            voice=self.config.voice,
            format=AudioFormat.PCM_16000HZ_MONO_16BIT,
            callback=callback,
        )

    async def get_audio_bytes(self) -> bytes:
        return await self.queue.get()

    def text_to_speech_stream(
        self, ten_env: AsyncTenEnv, text: str, end_of_segment: bool
    ) -> None:
        try:
            callback = AsyncIteratorCallback(ten_env, self.queue)

            if not self.synthesizer or end_of_segment:
                self._create_synthesizer(ten_env, callback)

            self.synthesizer.streaming_call(text)

            if end_of_segment:
                ten_env.log_info("Streaming complete")
                self.synthesizer.streaming_complete()
                self.synthesizer = None
        except WebSocketConnectionClosedException as e:
            ten_env.log_error(f"WebSocket connection closed, {e}")
            self.synthesizer = None
        except Exception as e:
            ten_env.log_error(f"Error streaming text, {e}")
            self.synthesizer = None

    def cancel(self, ten_env: AsyncTenEnv) -> None:
        if self.synthesizer:
            try:
                self.synthesizer.streaming_cancel()
            except WebSocketConnectionClosedException as e:
                ten_env.log_error(f"WebSocket connection closed, {e}")
            except Exception as e:
                ten_env.log_error(f"Error cancelling streaming, {e}")
            self.synthesizer = None
