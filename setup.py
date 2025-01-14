from setuptools import setup, find_packages

setup(
    name="obsyncit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=13.7.0",
        "loguru>=0.7.2",
        "tomli>=2.0.1",
        "pydantic>=2.6.1",
        "jsonschema>=4.21.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "pytest-asyncio>=0.23.5",
        ],
    },
) 