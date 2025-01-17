"""
ObsyncIt - Obsidian Settings Sync Tool
"""

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
        "setuptools>=69.0.3",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "pytest-asyncio>=0.23.5",
            "pre-commit>=3.6.0",
            "pylint>=3.0.3",
            "ruff>=0.1.14",
            "black>=24.1.0",
            "mypy>=1.8.0",
            "types-jsonschema>=4.21.0.0",
            "types-setuptools>=69.0.0.0",
        ],
    },
    entry_points={
        'console_scripts': [
            'obsyncit=obsyncit.main:main',
            'obsyncit-tui=obsyncit.obsync_tui:main',
        ],
    },
    python_requires='>=3.8',
    description="Sync Obsidian vault settings between different vaults",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Mike Earley",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities",
    ],
)