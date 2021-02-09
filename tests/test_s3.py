import functools
import unittest
import warnings
from typing import Any

from localstack_s3_pyspark.boto3 import use_localstack

lru_cache: Any = functools.lru_cache

use_localstack()


class TestS3(unittest.TestCase):
    """
    This test case verifies S3 file system functionality
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

    def test_placeholder(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
