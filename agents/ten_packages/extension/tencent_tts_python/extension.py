#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import traceback
import asyncio
from .tencent_tts import TencentTTS, TencentTTSConfig
from ten import (
    AsyncTenEnv,
)
from ten_ai_base.tts import AsyncTTSBaseExtension


class TencentTTSExtension(AsyncTTSBaseExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.client = None
        self.config = None

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        await super().on_init(ten_env)
        ten_env.log_info("on_init")

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        try:
            await super().on_start(ten_env)
            ten_env.log_info("on_start")

            self.config = await TencentTTSConfig.create_async(ten_env=ten_env)
            ten_env.log_info(f"config: {self.config}")

            if not self.config.app_id:
                raise ValueError("app_id is required")

            if not self.config.secret_id:
                raise ValueError("secret_id is required")

            if not self.config.secret_key:
                raise ValueError("secre_key is required")

            self.client = TencentTTS(self.config)
            self.client.create_synthesizer(ten_env=ten_env)
            self.client.start(ten_env=ten_env)

        except Exception as e:
            ten_env.log_error(
                f"on_start failed,err:{e},traceback: {traceback.format_exc()}"
            )

        asyncio.create_task(self._process_audio_data(ten_env))

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        await super().on_stop(ten_env)
        ten_env.log_info("on_stop")

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
        ten_env.log_info(f"on_request_tts: {input_text}")
        self.client.text_to_speech_stream(ten_env, input_text, end_of_segment)

    async def on_cancel_tts(self, ten_env: AsyncTenEnv) -> None:
        self.client.cancel(ten_env)
