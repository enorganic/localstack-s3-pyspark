import csv
import functools
import unittest
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from subprocess import check_call, check_output, list2cmdline
from time import sleep
from typing import Any, Callable, List, Optional

import boto3  # type: ignore
from boto3.resources.base import ServiceResource  # type: ignore
from localstack_s3_pyspark.boto3 import use_localstack
from pyspark.sql import SparkSession  # type: ignore

TESTS_PATH: Path = Path(__file__).absolute().parent
TEST_ROOT: str = "test-root"
TEST1_CSV_PATH: str = f"{TEST_ROOT}/test1.csv"
TEST2_CSV_PATH: str = f"{TEST_ROOT}/test2.csv"
spark_session_lru_cache: Callable[
    ...,
    Callable[
        [Callable[..., SparkSession]],
        Callable[..., SparkSession],
    ],
] = functools.lru_cache  # type: ignore
service_resource_lru_cache: Callable[
    ...,
    Callable[
        [Callable[..., ServiceResource]],
        Callable[..., ServiceResource],
    ],
] = functools.lru_cache  # type: ignore
use_localstack()


class TestS3(unittest.TestCase):
    """
    This test case verifies S3 file system functionality
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._csv1_bytes: Optional[bytes] = None
        self._csv2_bytes: Optional[bytes] = None
        super().__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls) -> None:
        arguments: List[str] = [
            "--file",
            str(TESTS_PATH.joinpath("docker-compose.yml")),
            "--project-directory",
            str(TESTS_PATH),
            "up",
            "-d",
        ]
        command: List[str]
        try:
            command = ["docker-compose"] + arguments
            print(" ".join(arguments))
            check_call(
                ["docker-compose"] + arguments,
                universal_newlines=True,
            )
            print(list2cmdline(command))
        except Exception:
            try:
                command = ["docker", "compose"] + arguments
                check_call(
                    command,
                    universal_newlines=True,
                )
                print(list2cmdline(command))
            except Exception:
                print(
                    check_output(
                        ["docker", "compose", "--help"], encoding="utf-8"
                    )
                )
                raise
        sleep(20)
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        arguments: List[str] = [
            "-f",
            str(TESTS_PATH.joinpath("docker-compose.yml")),
            "--project-directory",
            str(TESTS_PATH),
            "down",
        ]
        command: List[str]
        try:
            command = ["docker-compose"] + arguments
            print(" ".join(command))
            check_call(
                ["docker-compose"] + arguments,
                universal_newlines=True,
            )
            print(" ".join(command))
        except FileNotFoundError:
            command = ["docker", "compose"] + arguments
            check_call(
                command,
                universal_newlines=True,
            )
            print(" ".join(command))
        return super().tearDownClass()

    @property  # type: ignore
    @spark_session_lru_cache()
    def spark_session(self) -> SparkSession:
        return SparkSession.builder.enableHiveSupport().getOrCreate()

    @property  # type: ignore
    @service_resource_lru_cache()
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


if __name__ == "__main__":
    unittest.main()
