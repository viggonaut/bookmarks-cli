from setuptools import setup


setup(
    name="bookmarks-cli",
    version="0.1.0",
    description="CLI for syncing X bookmarks and other saved content into portable Markdown.",
    author="Vignir",
    license="MIT",
    packages=["bookmarks_cli", "bookmarks_cli.integrations"],
    entry_points={"console_scripts": ["bookmarks-cli=bookmarks_cli.cli:main"]},
    python_requires=">=3.9",
)
