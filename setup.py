"""Setup configuration for hogwarts-bench package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="hogwarts-bench",
    version="0.1.0",
    author="Hogwarts-bench Team",
    description="Automated testing framework for LLM long-context capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "tiktoken>=0.5.0",
        "plotly>=5.0.0",
        "python-dotenv>=1.0.0",
        "aiohttp>=3.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hogwarts-generate=src.generate:cli_main",
            "hogwarts-test=src.test:cli_main",
            "hogwarts-report=src.report:main",
        ],
    },
)
