from setuptools import setup, find_packages

setup(
    name="api-gateway",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "edna-common",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "psycopg2-binary>=2.9.0",
    ],
    python_requires=">=3.11",
)

