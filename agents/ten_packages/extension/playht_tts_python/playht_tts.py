import asyncio
from dataclasses import dataclass
import time

from websocket import WebSocketConnectionClosedException

from ten.async_ten_env import AsyncTenEnv
from ten_ai_base.config import BaseConfig
from typing import AsyncGenerator, AsyncIterable, AsyncIterator, Union
from pyht import AsyncClient, Format
from pyht.client import TTSOptions
import numpy as np


def convert_f32le_to_s16le_stream(input_bytes):
    pcm_f32_data = np.frombuffer(input_bytes, dtype=np.float32)

    pcm_s16_data = np.clip(pcm_f32_data * 32768, -32768, 32767).astype(np.int16)

    output_bytes = pcm_s16_data.tobytes()

    return bytearray(output_bytes)


@dataclass
class PlayhtTTSConfig(BaseConfig):
    user_id: str = ""
    api_key: str = ""
    # reference to https://docs.play.ht/reference/list-of-prebuilt-voices
    voice: str = (
        "s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jennifersaad/manifest.json"
    )


SAMPLE_RATE = 48000


class PlayhtTTSClientHandler:
    def __init__(
        self,
        ten_env: AsyncTenEnv,
        queue: asyncio.Queue,
        in_stream: AsyncIterator[str],
        out_stream: Union[AsyncGenerator[bytes, None], AsyncIterable[bytes]],
    ) -> None:
        self.queue = queue
        self.ten_env = ten_env
        self.in_stream = in_stream
        self.out_stream = out_stream
        self.buffer = bytearray()

    def start(self) -> None:
        asyncio.create_task(self._handle_audio_data())

    async def send_text_to_speech(self, text: str) -> None:
        if not self.in_stream:
            return
        self.ten_env.log_info(f"Sending text to speech: {text}")
        await self.in_stream(text)

    async def _handle_audio_data(self) -> None:
        self.ten_env.log_info("Handling audio data")
        if not self.out_stream:
            self.ten_env.log_error("No out stream")
            return
        async for chunk in self.out_stream:
            self.ten_env.log_info(
                f"Received pcm data: {len(chunk)} bytes,TTS_TEST_POINT_RECEIVED:{int(time.time() * 1000)}"
            )
            # Convert audio data from float32 format to int16 format, ensuring the input chunk is a multiple of 4.
            # Any extra data will be saved to the buffer.
            # First, merge the data in the buffer with the new data, then perform the conversion.
            data = self.buffer + chunk
            self.buffer = bytearray()
            if len(data) % 4 != 0:
                valid_length = len(data) - (len(data) % 4)
                self.buffer = data[valid_length:]
                data = data[:valid_length]

            await self.queue.put(convert_f32le_to_s16le_stream(data))
        self.ten_env.log_info("Audio data handling done")

    def close(self) -> None:
        self.ten_env.log_info("Closing handler")
        if self.out_stream:
            self.out_stream.close()


class PlayhtTTS:
    def __init__(self, config: PlayhtTTSConfig) -> None:
        self.config = config
        self.client = None  # Initially no synthesizer
        self.queue = asyncio.Queue()
        self.tts_options = None
        self.handler = None

    def create_synthesizer(self, ten_env: AsyncTenEnv):
        if self.client:
            self.client = None

        ten_env.log_info("Creating new synthesizer")
        self.client = AsyncClient(
            user_id=self.config.user_id,
            api_key=self.config.api_key,
        )
        ten_env.log_info(f"Config:{self.config}")
        self.tts_options = TTSOptions(
            voice=self.config.voice,
            format=Format.FORMAT_RAW,
            sample_rate=SAMPLE_RATE,
        )
        in_stream, out_stream = self.client.get_stream_pair(
            self.tts_options, voice_engine="Play3.0-mini-ws"
        )
        self.handler = PlayhtTTSClientHandler(
            ten_env, self.queue, in_stream, out_stream
        )
        self.handler.start()

    async def get_audio_bytes(self) -> bytes:
        return await self.queue.get()

    async def text_to_speech_stream(
        self, ten_env: AsyncTenEnv, text: str, end_of_segment: bool
    ) -> None:
        try:
            if not self.client:
                self.create_synthesizer(ten_env)

            await self.handler.send_text_to_speech(text)

        except WebSocketConnectionClosedException as e:
            ten_env.log_error(f"WebSocket connection closed, {e}")
            self.client = None
        except Exception as e:
            ten_env.log_error(f"Error streaming text, {e}")
            self.client = None

    def cancel(self, ten_env: AsyncTenEnv) -> None:
        if self.client:
            try:
                self.out_stream.close()
                self.out_stream = None
            except WebSocketConnectionClosedException as e:
                ten_env.log_error(f"WebSocket connection closed, {e}")
            except Exception as e:
                ten_env.log_error(f"Error cancelling streaming, {e}")
            self.handler.close()
            self.client.close()
            self.handler = None
            self.client = None
