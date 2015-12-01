#!/usr/bin/env python

from setuptools import setup, find_packages

__version__ = "1.4"

setup(
    name="awscodedeploy",
    version=__version__,
    description="CLI for Code Deploy supporting docker-compose",
    author="Location Labs",
    author_email="info@locationlabs.com",
    url="http://locationlabs.com",
    packages=find_packages(exclude=["*.tests"]),
    setup_requires=[
        "nose>=1.3.7"
    ],
    install_requires=[
        "awscli>=1.9.5",
        "awsenv>=1.7",
        "PyYAML>=3.11",
        "termcolor>=1.1.0",
    ],
    tests_require=[
        "PyHamcrest>=1.8.5",
        "mock>=1.0.1",
        "coverage>=4.0.1",
    ],
    test_suite="awscodedeploy.tests",
    entry_points={
        "console_scripts": [
            "aws-code-deploy = awscodedeploy.main:main",
        ]
    }
)
