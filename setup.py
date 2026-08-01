from setuptools import setup, find_packages

setup(
    name="workhorse",
    version="0.1.0",
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
            "workhorse=workhorse.cli:main",
        ],
    },
    python_requires=">=3.9",
)
