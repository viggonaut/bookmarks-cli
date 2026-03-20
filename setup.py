from setuptools import setup


setup(
    name="personal-os",
    version="0.1.0",
    description="Personal influence pipeline for capturing X bookmarks and other external content into agent-usable Markdown.",
    author="Vignir",
    license="MIT",
    packages=["personal_os", "personal_os.integrations"],
    entry_points={"console_scripts": ["personal-os=personal_os.cli:main"]},
    python_requires=">=3.9",
)
