import csv
import os
import sys
import unittest
import boto3  # type: ignore
import functools
from datetime import datetime
from subprocess import check_call
from pyspark.sql import SparkSession  # type: ignore
from boto3.resources.base import ServiceResource  # type: ignore
from io import BytesIO, StringIO
from time import sleep
from typing import Any, Callable, Dict, Optional
from localstack_s3_pyspark.boto3 import use_localstack

TEST_ROOT: str = "test-root"
TEST1_CSV_PATH: str = f"{TEST_ROOT}/test1.csv"
TEST2_CSV_PATH: str = f"{TEST_ROOT}/test2.csv"
TESTS_DIRECTORY: str = os.path.relpath(
    os.path.dirname(os.path.abspath(__file__))
).replace("\\", "/")
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

    def setUp(self) -> None:
        env: Dict[str, str] = dict(os.environ)
        env.update(SERVICES="s3")
        check_call(
            [sys.executable, "-m", "localstack.cli.main", "start", "-d"],
            env=env,
        )
        sleep(20)
        return super().setUp()

    def tearDown(self) -> None:
        check_call(
            [sys.executable, "-m", "localstack.cli.main", "stop"],
            universal_newlines=True,
        )
        return super().tearDown()

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
