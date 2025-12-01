from setuptools import setup, find_packages

setup(
    name="scanner",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "edna-common",
        "psycopg2-binary>=2.9.0",
    ],
    python_requires=">=3.11",
)

