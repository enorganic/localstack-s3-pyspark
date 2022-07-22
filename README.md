# localstack-s3-pyspark

[![test-distribute](https://github.com/enorganic/localstack-s3-pyspark/actions/workflows/test-distribute.yml/badge.svg)](https://github.com/enorganic/localstack-s3-pyspark/actions/workflows/test-distribute.yml)

This package provides a CLI for configuring pyspark to use
[localstack](https://github.com/localstack/localstack) for the S3 file system.
This is intended for testing packages locally (or in your CI/CD pipeline)
which you intend to deploy on an Amazon EMR cluster.

## Installation

Execute the following command, replacing **pip3** with the executable
appropriate for the environment where you want to configure **pyspark** to use
**localstack**:

```shell
pip3 install localstack-s3-pyspark
```

## Configure Spark's Defaults

If you've installed **localstack-s3-pyspark** in a Dockerfile or virtual
environment, just run the following command:

```shell
localstack-s3-pyspark configure-defaults
```

If you've installed **localstack-s3-pyspark** in an environment with multiple
python 3.x versions, you may instead want to run an appropriate variation of
the following command (replacing `python3` with the command used to access the
python executable for which you want to configure pyspark):

```shell
python3 -m localstack_s3_pyspark configure-defaults
```

### Tox

Please note that if you are testing your packages with **tox** (highly
recommended), you will need to:

- Include "localstack-s3-pyspark" in your tox **deps**
- Include `localstack-s3-pyspark configure-defaults` in your tox
  **commands_pre** (or by other means execute this command prior to your tests)

Here is an example **tox.ini** which starts up localstack using the localstack
CLI (you could also use `docker-compose` or just `docker run`, if you need
 greater control or fewer python dependencies, see the the localstack
documentation
["Getting Started" page](https://docs.localstack.cloud/get-started)
for details):

```ini
[tox]
envlist = pytest

[testenv:pytest]
deps =
  localstack-s3-pyspark
  localstack
commands_pre =
    localstack-s3-pyspark configure-defaults
    localstack start -d
    sleep 20
commands =
    py.test
commands_post =
    localstack stop
```

## Patch *boto3*

If your tests interact with S3 using **boto3**, you can patch boto3 from within
your unit tests as follows:

```python3
from localstack_s3_pyspark.boto3 import use_localstack
use_localstack()
```
