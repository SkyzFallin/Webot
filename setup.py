"""Setup configuration for Webull Trading Bot"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="webull-trading-bot",
    version="1.0.0",
    author="Trading Bot",
    description="Autonomous trading bot for Webull with stocks and options support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/webull-trading-bot",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pytz>=2024.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.9.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
        "ta-lib": [
            "ta-lib>=0.4.28",
        ]
    },
    entry_points={
        "console_scripts": [
            "webull-bot=main:main",
        ],
    },
)
