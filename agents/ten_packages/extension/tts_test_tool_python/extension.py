#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import traceback
import asyncio
import os
from ten import AsyncExtension, AsyncTenEnv, Data, Cmd
from .config import ToolConfig

TEXT_FILE_PATH = "tts_test.txt"
DATA_OUT_TEXT_DATA_PROPERTY_TEXT = "text"
DATA_OUT_TEXT_DATA_PROPERTY_IS_FINAL = "is_final"
DATA_OUT_TEXT_DATA_PROPERTY_STREAM_ID = "stream_id"
DATA_OUT_TEXT_DATA_PROPERTY_END_OF_SEGMENT = "end_of_segment"


class TTSTestToolExtension(AsyncExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.stream_id = 123
        self.config = None

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        await super().on_init(ten_env)
        ten_env.log_info("on_init")

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        await super().on_start(ten_env)
        ten_env.log_info("on_start")
        self.config = await ToolConfig.create_async(ten_env=ten_env)
        ten_env.log_info(f"config: {self.config}")
        asyncio.create_task(self.process_tts_text(ten_env=ten_env))

    async def process_tts_text(self, ten_env: AsyncTenEnv) -> None:
        ten_env.log_info("process_tts_text is ready")
        await asyncio.sleep(5)
        ten_env.log_info("process_tts_text is running")

        if not os.path.exists(self.config.file_path):
            ten_env.log_error(f"file not found: {self.config.file_path}")
            return
        content = ""
        try:

            with open(self.config.file_path, "r", encoding="utf-8") as file:
                content = file.read()
        except Exception as e:
            ten_env.log_error(f"error reading text file: {e}")
            traceback.print_exc()

        # 循环5次发送tts请求，内容就是content
        for i in range(int(self.config.loop_count)):
            await self.send_text_data(ten_env, content)
            ten_env.log_info(f"send text data,i={i}")
            await asyncio.sleep(int(self.config.duration))

        ten_env.log_info("process_tts_text is done")
        await self.close_app(ten_env)

    async def close_app(self, ten_env: AsyncTenEnv) -> None:
        close_app_cmd = Cmd.create("ten:close_app")
        close_app_cmd.set_dest("localhost", None, None, None)
        await ten_env.send_cmd(close_app_cmd)

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
        ten_env.log_info("on_deinit")
