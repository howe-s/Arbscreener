from setuptools import setup, find_packages

setup(
    name="arbscreener",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
) 