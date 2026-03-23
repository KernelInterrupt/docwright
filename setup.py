from setuptools import find_packages, setup

setup(
    name="docwright-core",
    version="0.1.0",
    description="Playwright-like runtime for guided document reading and controlled document actions",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={"docwright.capabilities.resources": ["*.md"]},
)
