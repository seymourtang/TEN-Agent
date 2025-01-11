#!/usr/bin/env python3

# Usage:
# pip install python-dotenv
# python3 test_tts.py

import os
import glob
import subprocess
import time
import logging
from dotenv import load_dotenv
from datetime import datetime
import json
import re


class TtsTester:
    def __init__(
        self,
        log_dir="/app/tests_tts_logs",
        txt_dir="/app/tests_tts_txt",
        property_json="/app/tests_tts_property/test_tts_%s_property.json",
    ):
        self.batch_number = datetime.now().strftime("%Y%m%d_%H%M")
        self.interval_seconds = int(os.environ.get("TOOL_DURATION", 20)) * int(
            os.environ.get("TOOL_LOOP_COUNT", 6)
        )
        self.txt_dir = txt_dir
        self.txt_files = []
        self.process = None
        self.property_json = property_json
        self.vendors = ["elevenlabs", "fish_audio", "cartesia"]

        # Create logs directory if it doesn't exist
        self.logs_dir = "%s/tests_tts_logs_%s" % (log_dir, self.batch_number)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        # Set up logging
        self.setup_logging()

        # Load environment variables from .env file
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logging.info(f"Loaded environment variables from {env_path}")
        else:
            logging.warning(f".env file not found at {env_path}")

    def clean_timestamp(self, timestamp):
        """Clean the timestamp string by removing unwanted characters."""
        """Remove special characters from the text."""
        return re.sub(r"\x1b\[[0-?9;]*[mK]", "", timestamp)

    def get_property_json(self, vendor):
        return self.property_json % vendor

    def replace_property_json(self, txt_file, property_json):
        with open(property_json, "r") as file:
            json_content = json.load(file)

        json_content["_ten"]["predefined_graphs"][0]["nodes"][0]["property"][
            "file_path"
        ] = txt_file

        with open(property_json, "w") as file:
            json.dump(json_content, file, indent=4)

    def setup_logging(self):
        """Set up logging configuration"""
        # Create log file
        log_file = os.path.join(
            self.logs_dir, f"tts_test_script_{self.batch_number}.log"
        )

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(process)d - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

        # Log initial message
        logging.info(f"TTS Test Started, log_file: {log_file}")
        logging.info("-" * 50)

    def scan_files(self):
        """Scan for TXT files in the directory"""
        self.txt_files = glob.glob(os.path.join(self.txt_dir, "*.txt"))
        if not self.txt_files:
            logging.warning(f"No TXT files found in {self.txt_dir}")
            return False

        logging.info(f"Found {len(self.txt_files)} TXT files:")
        for file in self.txt_files:
            logging.info(f"- {os.path.basename(file)}")
        return True

    def get_txt_files(self):
        """Get the list of TXT files"""
        return self.txt_files

    def get_worker_log_file(self, txt_file, vendor):
        """Get worker logs file"""
        return os.path.join(
            self.logs_dir,
            "tts_test_worker_%s_%s_%s.log"
            % (self.batch_number, os.path.basename(txt_file), vendor),
        )

    def process_txt_file(self, txt_file, vendor):
        """Process a single TXT file"""
        try:
            logging.info(f"Processing file: {txt_file} for vendor: {vendor}")

            # Start TTS service for this file
            if not self.start_tts_service(txt_file, vendor):
                return

        except Exception as e:
            logging.error(f"Error processing file {txt_file}: {e}")
        finally:
            # Stop TTS service after processing
            self.stop_tts_service()
            # Wait before processing next file
            time.sleep(1)

    def start_tts_service(self, txt_file, vendor):
        """Start the TTS service"""
        try:
            property_json = self.get_property_json(vendor)
            self.replace_property_json(txt_file, property_json)

            command = (
                f"cd /app/agents && /app/agents/bin/start --property {property_json}"
            )
            logging.info(f"Starting TTS service with command: {command}")

            worker_log_file = self.get_worker_log_file(txt_file, vendor)
            with open(worker_log_file, "w", encoding="utf-8") as output_file:
                self.process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=output_file,
                    stderr=output_file,
                    text=True,
                )
            logging.info(f"TTS service started, worker_log_file: {worker_log_file}")

            # Wait for service to initialize
            time.sleep(10)
            return True
        except Exception as e:
            logging.error(f"Failed to start TTS service: {e}")
            return False

    def stop_tts_service(self):
        """Stop the TTS service"""
        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                stdout, stderr = self.process.communicate()
                if stdout:
                    logging.info("Service output:")
                    for line in stdout.splitlines():
                        logging.info(f"  {line}")
                if stderr:
                    logging.error("Service errors:")
                    for line in stderr.splitlines():
                        logging.error(f"  {line}")

                logging.info("TTS service stopped")
            except Exception as e:
                logging.error(f"Error stopping TTS service: {e}")
            finally:
                self.process = None

    def run(self):
        """Run the TTS testing process"""
        logging.info(f"TTS Run Started")
        logging.info("-" * 50)

        if not self.scan_files():
            return

        for txt_file in self.txt_files:
            for vendor in self.vendors:
                self.process_txt_file(txt_file, vendor)

                # Wait for processing
                logging.info(
                    f"Waiting for {self.interval_seconds} seconds before processing next file"
                )
                time.sleep(self.interval_seconds)

        logging.info("All files processed")

    def stat(self):
        """Stat the TTS testing process"""
        logging.info(f"TTS Stat Started")
        logging.info("-" * 50)

        # if not self.scan_files():
        #     return

        stat_csv_file = os.path.join(
            self.logs_dir, f"tts_test_stat_{self.batch_number}.csv"
        )

        logging.info(f"stat_csv_file: {stat_csv_file}")

        with open(stat_csv_file, "w") as csv_file:
            csv_file.write("txt_file,vendor,ts_start,ts_end,time_duration(ms)\n")

            for txt_file in self.txt_files:
                for vendor in self.vendors:
                    worker_log_file = self.get_worker_log_file(txt_file, vendor)

                    logging.info(f"worker_log_file: {worker_log_file}")

                    ts_start = 0
                    ts_end = 0
                    point_send_found = False
                    point_send_found_count = 0
                    point_received_found = False
                    try:
                        with open(worker_log_file, "r") as file:
                            for line in file:
                                if "TTS_TEST_POINT_SEND" in line:
                                    point_send_found = True
                                    point_send_found_count += 1
                                    point_received_found = False

                                    parts = line.split("TTS_TEST_POINT_SEND:")
                                    if len(parts) > 1:
                                        ts_start = self.clean_timestamp(
                                            parts[1].strip()
                                        )

                                    logging.info(
                                        f"Find TTS_TEST_POINT_SEND, worker_log_file: {worker_log_file}, point_send_found: {point_send_found}, point_received_found: {point_received_found}, ts_start: {ts_start}, line: {line}"
                                    )

                                if "TTS_TEST_POINT_RECEIVED" in line:
                                    point_received_found = True

                                    parts = line.split("TTS_TEST_POINT_RECEIVED:")
                                    if len(parts) > 1:
                                        ts_end = self.clean_timestamp(parts[1].strip())

                                    logging.info(
                                        f"Find TTS_TEST_POINT_RECEIVED, worker_log_file: {worker_log_file}, point_send_found: {point_send_found}, point_received_found: {point_received_found}, ts_end: {ts_end}, line: {line}"
                                    )

                                # Ignore the first TTS_TEST_POINT_SEND
                                if (
                                    point_send_found
                                    and point_received_found
                                    and point_send_found_count > 1
                                ):
                                    time_diff = int(ts_end) - int(ts_start)
                                    logging.info(
                                        f"Time duration: {time_diff} ms, worker_log_file: {worker_log_file}, txt_file: {txt_file}, vendor: {vendor}"
                                    )

                                    csv_file.write(
                                        "%s,%s,%s,%s,%s\n"
                                        % (
                                            os.path.basename(txt_file),
                                            vendor,
                                            ts_start,
                                            ts_end,
                                            time_diff,
                                        )
                                    )

                                    # Ignore subsequent TTS_TEST_POINT_RECEIVED
                                    point_send_found = False

                    except Exception as e:
                        logging.error(f"Error reading log file {worker_log_file}: {e}")

        logging.info(f"All files stated, stat_csv_file: {stat_csv_file}")
        logging.info(f"TTS Stat Ended")


if __name__ == "__main__":
    tts_tester = TtsTester()
    tts_tester.run()
    tts_tester.stat()

