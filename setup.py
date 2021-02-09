import re
import sys
from collections import OrderedDict
from itertools import chain
from typing import (
    Any,
    Dict,
    Iterable,
    Match,
    Optional,
    Pattern,
    Sequence,
    Set,
)

import setuptools  # type: ignore

_INSTALL_REQUIRES: str = "install_requires"


_extras_pattern: Pattern = re.compile(r"^([^\[]+\[)([^\]]+)(\].*)$")


def consolidate_requirement_options(
    requirements: Iterable[str],
) -> Iterable[str]:
    requirement: str
    templates_options: Dict[str, Set[str]] = OrderedDict()
    traversed_requirements: Set[str] = set()
    template: str
    for requirement in requirements:
        print(requirement)
        match: Optional[Match] = _extras_pattern.match(requirement)
        if match:
            groups: Sequence[str] = match.groups()
            no_extras_requirement: str = f"{groups[0][:-1]}{groups[2][1:]}"
            template = f"{groups[0]}{{}}{groups[2]}"
            if template not in templates_options:
                templates_options[template] = set()
            templates_options[template] |= set(groups[1].split(","))
            if no_extras_requirement in templates_options:
                del templates_options[no_extras_requirement]
        elif requirement not in traversed_requirements:
            templates_options[requirement] = set()
    options: Set[str]
    for template, options in templates_options.items():
        if options:
            yield template.format(",".join(sorted(options)))
        else:
            yield template


def setup(**kwargs: Any) -> None:
    """
    This `setup` script intercepts arguments to be passed to
    `setuptools.setup` in order to dynamically alter setup requirements
    while retaining a function call which can be easily parsed and altered
    by `setuptools-setup-versions`.
    """
    # Require the package "dataclasses" for python 3.6, but not later
    # python versions (since it's part of the standard library after 3.6)
    if sys.version_info[:2] == (3, 6):
        if _INSTALL_REQUIRES not in kwargs:
            kwargs[_INSTALL_REQUIRES] = []
        kwargs[_INSTALL_REQUIRES].append("dataclasses")
    # Add an "all" extra which includes all extra requirements
    if "extras_require" in kwargs:
        if "all" not in kwargs["extras_require"]:
            kwargs["extras_require"]["all"] = list(
                consolidate_requirement_options(
                    chain(*kwargs["extras_require"].values())
                )
            )
        kwargs["extras_require"]["test"] = list(
            consolidate_requirement_options(
                chain(
                    *(
                        values
                        for key, values in kwargs["extras_require"].items()
                        if key not in ("dev", "all")
                    )
                )
            )
        )
        print(
            "extras_require[all]:\n"
            + "\n".join(
                f"- {requirement}"
                for requirement in kwargs["extras_require"]["all"]
            )
        )
        print(
            "extras_require[test]:\n"
            + "\n".join(
                f"- {requirement}"
                for requirement in kwargs["extras_require"]["test"]
            )
        )
    # Pass the modified keyword arguments to `setuptools.setup`
    setuptools.setup(**kwargs)


setup(
    name="localstack-s3-pyspark",
    version="0.0.0",
    description="A CLI to configure pyspark for use with s3 on localstack",
    author="David Belais",
    author_email="david@belais.me",
    python_requires="~=3.6",
    packages=["localstack_s3_pyspark"],
    package_data={"localstack_s3_pyspark": ["py.typed"]},
    install_requires=["localstack-client~=1.12", "lxml~=4.6", "pyspark"],
    extras_require={
        "boto3": ["boto3"],
        "dev": [
            "black~=19.10b0",
            "readme-md-docstrings~=0.1",
            "setuptools-setup-versions~=1.6",
        ],
        "test": [
            "daves-dev-tools~=0.3",
            "pytest~=5.4",
            "tox~=3.21",
            "flake8~=3.8",
            "mypy~=0.800",
            "pip>=21",
        ],
    },
    entry_points={
        "console_scripts": [
            "localstack-s3-pyspark = localstack_s3_pyspark.__main__:main"
        ]
    },
)
