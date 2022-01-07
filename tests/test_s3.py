import csv
import os
import unittest
from datetime import datetime
import boto3  # type: ignore
from pyspark.sql import SparkSession  # type: ignore
from boto3.resources.base import ServiceResource  # type: ignore
from io import BytesIO, StringIO
from time import sleep
from typing import Any, Optional
from localstack_s3_pyspark.boto3 import use_localstack
from daves_dev_tools.utilities import run, lru_cache

TEST_ROOT: str = "test-root"
TEST1_CSV_PATH: str = f"{TEST_ROOT}/test1.csv"
TEST2_CSV_PATH: str = f"{TEST_ROOT}/test2.csv"
TESTS_DIRECTORY: str = os.path.relpath(
    os.path.dirname(os.path.abspath(__file__))
).replace("\\", "/")
DOCKER_COMPOSE: str = f"{TESTS_DIRECTORY}/docker-compose.yml"
use_localstack()


def is_ci() -> bool:
    return "CI" in os.environ and (os.environ["CI"].lower() == "true")


class TestS3(unittest.TestCase):
    """
    This test case verifies S3 file system functionality
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._csv1_bytes: Optional[bytes] = None
        self._csv2_bytes: Optional[bytes] = None
        up_command: str = (
            "docker compose"
            f" -f {DOCKER_COMPOSE}"
            f" --project-directory {TESTS_DIRECTORY}"
            " up"
            " -d"
        )
        try:
            run(up_command)
        except OSError:
            run(up_command.replace("docker compose", "docker-compose"))
        sleep(20)
        super().__init__(*args, **kwargs)

    @property  # type: ignore
    @lru_cache()
    def spark_session(self) -> SparkSession:
        return SparkSession.builder.enableHiveSupport().getOrCreate()

    @property  # type: ignore
    @lru_cache()
    def bucket(self) -> ServiceResource:
        bucket: ServiceResource = (
            boto3.session.Session(
                aws_access_key_id="accesskey",
                aws_secret_access_key="secretkey",
            )
            .resource("s3")
            .Bucket(
                datetime.now()
                .isoformat(sep="-")
                .replace(":", "-")
                .replace(".", "-")
            )
        )
        bucket.create()
        return bucket

    @property  # type: ignore
    def csv1(self) -> BytesIO:
        if self._csv1_bytes is None:
            with StringIO() as string_io:
                dict_writer: csv.DictWriter = csv.DictWriter(
                    string_io, ("a", "b", "c")
                )
                dict_writer.writerow(dict(a=1, b=2, c=3))
                string_io.seek(0)
                self._csv1_bytes = bytes(string_io.read(), encoding="utf-8")
        return BytesIO(self._csv1_bytes)

    @property  # type: ignore
    def csv2(self) -> BytesIO:
        if self._csv2_bytes is None:
            with StringIO() as string_io:
                dict_writer: csv.DictWriter = csv.DictWriter(
                    string_io, ("a", "b", "c")
                )
                dict_writer.writerow(dict(a=4, b=5, c=6))
                string_io.seek(0)
                self._csv2_bytes = bytes(string_io.read(), encoding="utf-8")
        return BytesIO(self._csv2_bytes)

    def test_spark_read(self) -> None:
        self.bucket.put_object(Key=TEST1_CSV_PATH, Body=self.csv1)
        self.bucket.put_object(Key=TEST2_CSV_PATH, Body=self.csv2)
        sleep(10)
        self.spark_session.read.csv(
            f"s3://{self.bucket.name}/{TEST1_CSV_PATH}"
        )
        self.spark_session.read.csv(
            f"s3://{self.bucket.name}/{TEST2_CSV_PATH}"
        )
        self.bucket.objects.all().delete()

    def __del__(self) -> None:
        if not is_ci():
            down_command: str = (
                "docker compose"
                f" -f '{DOCKER_COMPOSE}'"
                f" --project-directory '{TESTS_DIRECTORY}'"
                " down"
            )
            try:
                run(down_command)
            except OSError:
                run(down_command.replace("docker compose", "docker-compose"))


if __name__ == "__main__":
    unittest.main()
