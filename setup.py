import re
from pathlib import Path

from setuptools import setup, find_packages


cargo_manifest = Path(__file__).with_name("Cargo.toml").read_text()
version = re.search(r'^version = "([^"]+)"', cargo_manifest, re.MULTILINE).group(1)

setup(
    name="workhorse",
    version=version,
    packages=find_packages(),
    install_requires=[
        "groq>=0.9.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "click>=8.0",
        "rich>=13.0",
        "aiohttp>=3.8",
    ],
    entry_points={
        "console_scripts": [
            "workhorse-legacy=workhorse.cli:main",
        ],
    },
    python_requires=">=3.9",
)
