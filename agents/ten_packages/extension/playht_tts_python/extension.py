#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import asyncio
import time
from .playht_tts import PlayhtTTS, PlayhtTTSConfig
from ten import (
    AsyncTenEnv,
)
from ten_ai_base.tts import AsyncTTSBaseExtension


class Addon(AsyncTTSBaseExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.client = None
        self.config = None

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        await super().on_init(ten_env)
        ten_env.log_debug("on_init")

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        await super().on_start(ten_env)
        ten_env.log_debug("on_start")

        self.config = await PlayhtTTSConfig.create_async(ten_env=ten_env)
        self.client = PlayhtTTS(self.config)

        asyncio.create_task(self._process_audio_data(ten_env))

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        await super().on_stop(ten_env)
        ten_env.log_debug("on_stop")

        await self.queue.put(None)

    async def on_deinit(self, ten_env: AsyncTenEnv) -> None:
        await super().on_deinit(ten_env)
        ten_env.log_debug("on_deinit")

    async def _process_audio_data(self, ten_env: AsyncTenEnv) -> None:
        while True:
            audio_data = await self.client.get_audio_bytes()

            if audio_data is None:
                break

            await self.send_audio_out(ten_env, audio_data)

    async def on_request_tts(
        self, ten_env: AsyncTenEnv, input_text: str, end_of_segment: bool
    ) -> None:
        ten_env.log_info(
            rf"on_request_tts: {input_text},TTS_TEST_POINT_SEND:{int(time.time() * 1000)}"
        )
        self.client.text_to_speech_stream(ten_env, input_text, end_of_segment)

    async def on_cancel_tts(self, ten_env: AsyncTenEnv) -> None:
        self.client.cancel(ten_env)