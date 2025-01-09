#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import traceback
import asyncio
from ten import AsyncExtension, AsyncTenEnv, Data, Cmd

TEXT_FILE_PATH = "tts_test.txt"
DATA_OUT_TEXT_DATA_PROPERTY_TEXT = "text"
DATA_OUT_TEXT_DATA_PROPERTY_IS_FINAL = "is_final"
DATA_OUT_TEXT_DATA_PROPERTY_STREAM_ID = "stream_id"
DATA_OUT_TEXT_DATA_PROPERTY_END_OF_SEGMENT = "end_of_segment"


class TTSTestToolExtension(AsyncExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.stream_id = 123
        self.duration = 0.2

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        await super().on_init(ten_env)
        ten_env.log_info("on_init")

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        await super().on_start(ten_env)
        ten_env.log_info("on_start")
        asyncio.create_task(self.process_tts_text(ten_env=ten_env))

    async def process_tts_text(self, ten_env: AsyncTenEnv) -> None:
        try:
            for line in open(TEXT_FILE_PATH, "r", encoding="utf-8"):
                ten_env.log_info(f"origin text: {line}")
                await self.send_text_data(ten_env, line)
                await asyncio.sleep(self.duration)

        except Exception as e:
            ten_env.log_error(f"error reading text file: {e}")
            traceback.print_exc()

    async def send_text_data(self, ten_env: AsyncTenEnv, text: str) -> None:
        data = Data.create("text_data")

        data.set_property_string(DATA_OUT_TEXT_DATA_PROPERTY_TEXT, text)
        data.set_property_int(DATA_OUT_TEXT_DATA_PROPERTY_STREAM_ID, self.stream_id)
        data.set_property_bool(DATA_OUT_TEXT_DATA_PROPERTY_END_OF_SEGMENT, True)
        data.set_property_bool(DATA_OUT_TEXT_DATA_PROPERTY_IS_FINAL, True)

        await ten_env.send_data(data)

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        await super().on_stop(ten_env)
        ten_env.log_info("on_stop")

    async def on_deinit(self, ten_env: AsyncTenEnv) -> None:
        await super().on_deinit(ten_env)
        ten_env.log_debug("on_deinit")
