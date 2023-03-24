import argparse
import functools
import os
import re
import shutil
import sys
import lxml.etree  # type: ignore
from py4j.protocol import Py4JJavaError  # type: ignore
from collections import OrderedDict
from http.client import HTTPResponse
from inspect import Traceback
from itertools import chain
from subprocess import check_output
from typing import (
    Any,
    Callable,
    Dict,
    IO,
    Iterable,
    List,
    Set,
    Tuple,
    Union,
)
from urllib.request import urlopen
from dataclasses import astuple, dataclass
from pyspark.java_gateway import launch_gateway  # type: ignore
from pyspark.sql import SparkSession  # type: ignore

lru_cache: Callable[..., Any] = functools.lru_cache


MAVEN_ROOT: str = "https://repo1.maven.org/maven2/"


@lru_cache()
def get_spark_home() -> str:
    spark_home: str = check_output(
        [sys.executable, "-W", "ignore", "-m", "pyspark.find_spark_home"],
        encoding="utf-8",
        universal_newlines=True,
    )
    print(f"Spark Home: {spark_home}")
    return spark_home.strip()


@lru_cache()
def get_hadoop_version() -> str:
    """
    Get the HADOOP version pyspark will use
    """
    return launch_gateway().jvm.org.apache.hadoop.util.VersionInfo.getVersion()


def get_version_tuple(version: str) -> Tuple[int, ...]:
    return tuple(int(version_part) for version_part in version.split("."))


@lru_cache()
def get_latest_maven_compatible_repo_version(
    name: str, major_version: int
) -> str:
    """
    Get the HADOOP version pyspark will use
    """

    def major_version_filter_function(version: Tuple[int, ...]) -> bool:
        return version[0] == major_version

    return get_latest_maven_repo_version(
        name, filter_function=major_version_filter_function
    )


def iter_links(url: str) -> Iterable[str]:
    http_response_io: HTTPResponse
    with urlopen(url) as http_response:
        html: str = str(http_response.read(), encoding="utf-8")
        root: lxml.etree.Element = lxml.etree.HTML(html)
    element: lxml.etree.Element
    for element in root.findall(".//a"):
        if element.attrib.get("href", ""):
            yield element.attrib["href"]


def iter_maven_jar_versions(name: str) -> Iterable[str]:
    """
    Get a list of all versions available for the indicated package
    """
    path: str = parse_maven_package_identifier(name).path
    href: str
    for href in iter_links(f"{MAVEN_ROOT}{path}/"):
        if re.match(r"^[\d.]*[\d]/$", href):
            yield href.rstrip("/")


def _any_version_filter_function(version: Tuple[int, ...]) -> bool:
    return True


def get_latest_maven_repo_version(
    name: str,
    filter_function: Callable[[Tuple[int, ...]], bool] = (
        _any_version_filter_function
    ),
) -> str:
    """Find the latest version of a jar"""
    version_int: int
    version_str: str
    version_str_part: str
    return ".".join(
        str(version_int)
        for version_int in max(
            filter(
                filter_function,
                (
                    get_version_tuple(version_str)
                    for version_str in iter_maven_jar_versions(name)
                ),
            )
        )
    )


@lru_cache()
def get_spark_conf_directory() -> str:
    path: str = f"{get_spark_home()}/conf"
    os.makedirs(path, exist_ok=True)
    return f"{path}/"


def _line_is_not_empty(line: str) -> bool:
    return True if line.strip() else False


class SparkDefaults:
    __slots__ = ("_dict",)

    def __init__(self) -> None:
        self._dict: Dict[str, Set[str]] = OrderedDict()

    def __getitem__(self, key: str) -> Set[str]:
        values: Set[str] = self._dict.get(key, set())
        self._dict[key] = values
        return values

    def __delitem__(self, key: str) -> None:
        del self._dict[key]

    def __setitem__(self, key: str, values: Union[Iterable[str], str]) -> None:
        if not isinstance(values, set):
            if isinstance(values, str):
                values = {values}
            else:
                assert isinstance(values, Iterable)
                values = set(values)
        self._dict[key] = values

    def __enter__(self) -> "SparkDefaults":
        file_io: IO[str]
        try:
            with open(
                f"{get_spark_conf_directory()}spark-defaults.conf", "r"
            ) as file_io:
                line: str
                for line in filter(_line_is_not_empty, file_io.readlines()):
                    key: str
                    value: str
                    key, value = re.split(r"\s+", line.strip(), maxsplit=1)
                    self[key].add(value)
        except FileNotFoundError:
            pass
        return self

    def _iter_lines(self) -> Iterable[str]:
        key: str
        values: Set[str]
        if self._dict:
            column_width: int = max(len(key) for key in self._dict.keys()) + 1
            for key, values in self._dict.items():
                if values:
                    yield (
                        f"{key}{' ' * (column_width - len(key))}"
                        f"{','.join(sorted(values))}\n"
                    )
            yield ""

    def __exit__(
        self, type_: type, value: Exception, traceback: Traceback
    ) -> None:
        with open(
            f"{get_spark_conf_directory()}spark-defaults.conf",
            "w",
        ) as file_io:
            file_io.writelines(self._iter_lines())

    def clear(self) -> None:
        key: str
        values: Set[str]
        for key, values in self._dict.items():
            values.clear()


@dataclass
class MavenPackage:
    identifier: str
    path: str
    qualified_name: str
    version: str


@lru_cache()
def parse_maven_package_identifier(identifier: str) -> MavenPackage:
    name_parts: List[str] = identifier.split(":")
    version: str = ""
    if len(name_parts) > 2:
        version = name_parts.pop()
    qualified_name: str = ":".join(name_parts)
    return MavenPackage(
        identifier,
        identifier.replace(".", "/").replace(":", "/"),
        qualified_name,
        version,
    )


def add_jar(identifier: str, spark_defaults: SparkDefaults) -> None:
    repository_path: str
    version: str
    identifier, repository_path, qualified_name, version = astuple(
        parse_maven_package_identifier(identifier)
    )
    if version == "latest" or not version:
        version = get_latest_maven_repo_version(qualified_name)

    def _is_version_of_package(variant_identifier: str) -> bool:
        return (
            parse_maven_package_identifier(variant_identifier).qualified_name
            == qualified_name
        )

    file_name: str
    packages_str: str
    spark_jars_packages: Set[str] = set(
        chain(
            *(
                packages_str.split(",")
                for packages_str in spark_defaults["spark.jars.packages"]
            )
        )
    )
    spark_jars_packages.difference_update(
        set(
            filter(
                _is_version_of_package,
                spark_jars_packages,
            )
        )
    )
    spark_jars_packages.add(f"{qualified_name}:{version}")
    spark_defaults["spark.jars.packages"].clear()
    spark_defaults["spark.jars.packages"].update(spark_jars_packages)


def clear_ivy_cache() -> None:
    print("Clearing the ivy cache")
    try:
        ivy_directory: str = (
            SparkSession.builder.getOrCreate()
            .sparkContext.getConf()
            .get("spark.jars.ivy", "~/.ivy2")
        )
        shutil.rmtree(os.path.expanduser(ivy_directory), ignore_errors=True)
    except Py4JJavaError:
        pass


def configure_defaults(use_localstack: bool = True) -> None:
    """
    This function alters $SPARK_HOME/conf/spark-defaults.conf so that pyspark
    will use localstack in lieu of AWS endpoints for s3 interactions.
    """
    hadoop_version: str = get_hadoop_version()
    clear_ivy_cache()
    with SparkDefaults() as spark_defaults:
        add_jar("com.amazonaws:aws-java-sdk-bundle", spark_defaults)
        add_jar(
            f"org.apache.hadoop:hadoop-aws:{hadoop_version}", spark_defaults
        )
        spark_defaults[
            "spark.hadoop.fs.s3.impl"
        ] = "org.apache.hadoop.fs.s3a.S3AFileSystem"
        spark_defaults["spark.hadoop.fs.s3a.connection.ssl.enabled"] = "false"
        spark_defaults["spark.hadoop.fs.s3a.attempts.maximum"] = "3"
        spark_defaults["spark.hadoop.fs.s3a.change.detection.mode"] = "none"
        spark_defaults["spark.hadoop.fs.s3a.path.style.access"] = "true"
        spark_defaults["spark.hadoop.fs.s3a.fast.upload"] = "true"
        spark_defaults["spark.hadoop.fs.s3a.fast.upload.buffer"] = "bytebuffer"
        if use_localstack:
            spark_defaults["spark.hadoop.fs.s3a.endpoint"] = "localhost:4566"
            spark_defaults["spark.hadoop.fs.s3a.access.key"] = "accesskey"
            spark_defaults["spark.hadoop.fs.s3a.secret.key"] = "secretkey"
        else:
            del spark_defaults["spark.hadoop.fs.s3a.endpoint"]
            del spark_defaults["spark.hadoop.fs.s3a.access.key"]
            del spark_defaults["spark.hadoop.fs.s3a.secret.key"]
    print("Success!")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="localstack-s3-pyspark configure-defaults",
        description=(
            "This command updates pyspark's hadoop configuration "
            "for use with localstack"
        ),
    )
    parser.add_argument(
        "-nl",
        "--non-local",
        const=True,
        default=False,
        action="store_const",
        help="Configure S3 only (don't connect to localstack)",
    )
    namespace: argparse.Namespace = parser.parse_args()
    assert namespace
    configure_defaults(use_localstack=(not namespace.non_local))


if __name__ == "__main__":
    main()
