# localstack-s3-pyspark

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

- Include "localstack-s3-pyspark" in your installation requirements (either in
  your setup.py or setup.cfg file, or in the tox **deps** argument)
- Include `localstack-s3-pyspark configure-defaults` prior to your tests
  in your list of commands for each test environment
- Include `docker-compose up -d` in **commands_pre** and `docker-compose down`
  in **commands_post**

Here is an example **tox.ini** for this repository:

```ini
[tox]
envlist = py36, py37, py38, py39

[testenv]
extras = test
deps = localstack-s3-pyspark
commands_pre =
    docker-compose -f tests/docker-compose.yml --project-directory tests up -d
commands =
    flake8
    mypy
    localstack-s3-pyspark configure-defaults
    py.test
commands_post =
    docker-compose -f tests/docker-compose.yml --project-directory tests down
```

## Patch *boto3*

If your tests interact with S3 using **boto3**, you can patch boto3 from within
your unit tests as follows:

```python3
from localstack_s3_pyspark.boto3 import use_localstack
use_localstack()
```
